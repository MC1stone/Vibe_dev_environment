# NIR Intelligence Platform - Project ingest service (OP10)
# Phase 1 of the project workflow: turns the files of an AnalysisProject into
# usable datasets (measurement series + metadata) using the S3 format-agnostic
# loader (EnhancedDataPreparationAgent) and assesses metadata quality and
# data usability with improvement recommendations for the user. File-type
# and spectrometer agnostic per the init prompt ground rules.
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.ProjectIngest")

# Channel columns of multi-channel (wide-format) spectrometer exports:
# '<prefix>_<wavelength>' like A_410, B_435, L_940 (Dpark fun NIR Triad) or
# ch_410nm, 680nm etc. Generic per the init prompt ground rules - no device
# or format hard-coding.
_WAVELENGTH_COLUMN_RE = re.compile(r"^(?:[A-Za-z]{1,3}_)?(\d{2,5})\s*n?m?$", re.IGNORECASE)


def _detect_wide_format(file_path: str) -> Dict[str, Any] | None:
    """Detect a multi-channel (wide-format) spectral export: one row per
    sample/measurement, one column per wavelength channel (A_410, B_435,
    ... L_940). Returns {'channel_columns': [(column, wavelength_nm), ...],
    'header_row': index} or None when the file is not a wide-format export.
    Handles preamble/metadata lines above the header (DIY exports) and
    semicolon/tab/comma delimiters.
    """
    import pandas as pd

    path = Path(file_path)
    if not path.exists():
        return None
    from agents.data_preparation_agent import sniff_text_encoding
    text = path.read_text(encoding=sniff_text_encoding(str(path)),
                          errors='replace')
    lines = text.splitlines()

    header_row, header_fields, delimiter = None, None, None
    for index, line in enumerate(lines[:50]):
        if not line.strip():
            continue
        for delim in (';', '\t', ','):
            fields = line.split(delim)
            channel_cols = []
            for col in fields:
                match = _WAVELENGTH_COLUMN_RE.match(col.strip())
                if match:
                    channel_cols.append((col.strip(), float(match.group(1))))
            if len(channel_cols) >= 8 and len(fields) > len(channel_cols):
                header_row, header_fields, delimiter = index, fields, delim
                break
        if header_row is not None:
            break
    if header_row is None:
        return None

    try:
        from agents.data_preparation_agent import sniff_text_encoding
        df = pd.read_csv(path, sep=delimiter, header=header_row, dtype=str,
                         engine='python', on_bad_lines='skip',
                         skip_blank_lines=False,
                         encoding=sniff_text_encoding(str(path)))
        df = df.dropna(how='all')
    except Exception:
        return None

    channels = []
    for col in (header_fields or []):
        match = _WAVELENGTH_COLUMN_RE.match(col.strip())
        if match and col in df.columns:
            channels.append((col, float(match.group(1))))
    if len(channels) < 8 or len(df) < 2:
        return None
    # Deterministic preamble metadata (2026-10-09, Kaffee-Vorfall): the
    # lines ABOVE the header carry the measurement context ('Bediener: ...',
    # 'Instrument: ...') - the Data Preparation Agent extracts them so the
    # many meta infos in DIY exports are not silently dropped when no
    # LLM is available.
    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    preamble_metadata = EnhancedDataPreparationAgent._extract_metadata_from_lines(
        lines[:header_row])
    return {
        'channel_columns': channels,
        'header_row': header_row,
        'preamble_metadata': preamble_metadata,
        'dataframe': df,
        'measurement_count': len(df),
    }


def _wide_column_numeric(series):
    """Convert one wide-format column to numeric values. Uses the plain
    number format first and falls back to a German decimal comma; avoids
    the thousands-separator heuristic (it misreads three-decimal exports
    like '20729.770' as thousands groups) and stays format-agnostic."""
    import pandas as pd

    values = pd.to_numeric(series, errors='coerce')
    if values.notna().sum() >= max(1, len(series) // 2):
        return values.dropna()
    values = pd.to_numeric(
        series.astype(str).str.replace(',', '.', regex=False),
        errors='coerce')
    return values.dropna()


def _ingest_wide_format(file_record, file_path: str, wide: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest a wide-format export into a dataset entry: channel columns
    become the wavelength axis, each row is one measurement. The median
    spectrum over all measurements is the project measurement series
    (median is robust against sensor overflow values); the reference
    columns (e.g. Brix) are kept with their statistics for the agents."""
    import pandas as pd

    df = wide['dataframe']
    channels = wide['channel_columns']

    # Datenbereinigung (Data Preparation Agent, MO): Sensor-Overflow-
    # Sentinels (32-Bit-ADC-Marker wie 2**32 + 4 = 4294967300.0) sind
    # ungueltige Messwerte - zentrale Erkennung durch den Agenten, damit
    # sie weder den Median (Darstellung) noch Statistiken verzerren.
    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    # Kanal-Diagnose (Kaffee-Vorfall 2026-10-09): ein Kanal mit
    # durchgaengigem Overflow-Sentinel (C_460: 99%, F_535: 84%) ist ein
    # DEFEKTER KANAL des Spektrometers - ihn ausschliessen und die
    # Messungen behalten. Der bisherige Zeilen-Filter warf bei diesem
    # Datensatz 447 von 451 Messungen weg.
    channel_diag = EnhancedDataPreparationAgent.detect_defective_channels(
        df, [c for c, _ in channels])
    defective_channels = channel_diag['defective_channels']
    channels = [(c, wl) for c, wl in channels
                if c not in defective_channels]
    if defective_channels:
        logger.info(
            'Defekte Kanaele ausgeschlossen (%s): %s - Messungen '
            'bleiben erhalten', file_path, ', '.join(defective_channels))
    overflow = EnhancedDataPreparationAgent.detect_sensor_overflow(
        df, [c for c, _ in channels])
    saturated_values_total = overflow['saturated_values']
    series = []
    for col, wavelength_nm in channels:
        values = _wide_column_numeric(df[col])
        values = values[values < EnhancedDataPreparationAgent.SENSOR_OVERFLOW_THRESHOLD]
        if values.empty:
            continue
        series.append((wavelength_nm, float(values.median()), int(len(values))))
    if len(series) < 8:
        return {'usable': False,
                'reason': 'Wide-Format erkannt, aber zu wenige auswertbare Kanäle'}
    wavelengths = [s[0] for s in series]
    intensities = [s[1] for s in series]

    reference_columns = []
    text_reference_columns = []
    for col in df.columns:
        if col in (c for c, _ in channels):
            continue
        values = _wide_column_numeric(df[col])
        if len(values) >= max(2, len(df) // 2):
            reference_columns.append({
                'name': col,
                'count': int(len(values)),
                'mean': float(values.mean()),
                'min': float(values.min()),
                'max': float(values.max()),
            })
        else:
            # Nicht-numerische Spalte (z.B. 'Messobjekt' = Kaffeesorte,
            # Proben-Name): Klassen-Label-Kandidat fuer die
            # Klassifikations-Erkennung - numerische Spalten sind fuer
            # Kategorien unbrauchbar, deshalb getrennt erfasst.
            as_text = df[col].astype(str)
            if 2 <= as_text.nunique() <= 30 and as_text.str.len().mean() <= 40:
                text_reference_columns.append({
                    'name': col,
                    'count': int(len(as_text)),
                    'unique_values': int(as_text.nunique()),
                })

    # Measurement replicas for the sensor quality agent: replicate-based
    # noise/drift/offset checks are meaningful, channel-shape-based ones are
    # not (a wide-band multisensor has genuine channel-to-channel structure).
    # Replicas = longest run of consecutive rows sharing one non-channel
    # identifier value (e.g. the measured object), capped at 25% of the rows
    # so a whole-day constant column cannot pose as a replicate group.
    # Saturated channel values (32-bit ADC overflow markers like 2**32) are
    # excluded from the replicas and reported as their own defect instead of
    # skewing the noise/drift estimates.
    channel_names = [c for c, _ in channels if c in df.columns]
    measurement_samples = []
    saturated_measurements = 0
    if len(df) > 1 and channel_names:
        best_len, best_start = 0, 0
        cap = max(3, len(df) // 4)
        for col in df.columns:
            if col in channel_names or col in (r['name'] for r in reference_columns):
                continue
            values = df[col].astype(str)
            if values.str.len().mean() > 60 or values.nunique() > 50:
                continue
            run_len, run_start = 0, 0
            cur_start, cur_len = 0, 1
            vals = values.tolist()
            for i in range(1, len(vals) + 1):
                if i < len(vals) and vals[i] == vals[i - 1]:
                    cur_len += 1
                else:
                    if cur_len > run_len:
                        run_len, run_start = cur_len, cur_start
                    if i < len(vals):
                        cur_start, cur_len = i, 1
            if 3 <= run_len <= cap and run_len > best_len:
                best_len, best_start = run_len, run_start
        if best_len >= 3:
            block = df[channel_names].iloc[best_start:best_start + best_len]
            numeric = block.apply(pd.to_numeric, errors='coerce').dropna(how='any')
            block_overflow = EnhancedDataPreparationAgent.detect_sensor_overflow(
                numeric)
            saturated_measurements = len(block_overflow['saturated_rows'])
            numeric = block_overflow['clean']
            if len(numeric) >= 3:
                measurement_samples = [
                    [float(v) for v in row]
                    for row in numeric.to_numpy().tolist()[:25]
                ]

    # Calibration samples for supervised models (MLP/CNN calibration, PLS/PCR
    # targets): rows sampled across the WHOLE file, not only the replica
    # block - one measured object carries one reference value (a constant
    # target cannot train a calibrator). Saturated rows are excluded; the
    # target column is chosen by name priority (brix/sugar/reference first),
    # index/counter-like and row-unique columns are skipped.
    calibration_samples = []
    reference_values = None
    classification_samples = None
    classification_labels = None
    if channel_names:
        numeric_all = df[channel_names].apply(pd.to_numeric, errors='coerce') \
            .dropna(how='any')
        numeric_all = EnhancedDataPreparationAgent.detect_sensor_overflow(
            numeric_all)['clean']
        target_keys = ('brix', 'zucker', 'sugar', 'refe', 'target',
                       'kalibration', 'calibration', 'y')
        ordered_refs = sorted(
            reference_columns,
            key=lambda r: 0 if any(k in str(r['name']).lower()
                                    for k in target_keys) else 1)
        target_name = None
        for ref in ordered_refs:
            target = pd.to_numeric(df[ref['name']], errors='coerce')
            if target.is_monotonic_increasing or target.is_monotonic_decreasing:
                continue
            if target.nunique() >= len(target):
                continue
            paired = numeric_all.join(target.rename('__target'), how='inner') \
                .dropna(subset=['__target'])
            if len(paired) < 12:
                continue
            max_samples = min(2000, len(paired))
            step = max(1, len(paired) // max_samples)
            rows = paired.iloc[::step].head(max_samples)
            calibration_samples = [
                [float(v) for v in row]
                for row in rows[channel_names].to_numpy().tolist()
            ]
            reference_values = [float(v) for v in rows['__target'].tolist()]
            target_name = str(ref['name'])
            break

    # Klassifikations-Erkennung (2026-10-08, Kaffee-Datensatz): eine
    # nicht-numerische Referenzspalte mit wenigen wiederholten Werten
    # (z.B. 'Messobjekt' = Kaffeesorte) ist ein KLASSEN-LABEL, kein
    # numerischer Zielwert. analysis_mode='classification' steuert die
    # Folgeauswertung (Sorten unterscheiden statt Kalibration); die
    # Klassen-Labels werden fuer Klassifikations-Samples mitgefuehrt.
    class_label_column = None
    class_labels = None
    analysis_mode = 'regression' if target_name else 'unsupervised'
    if text_reference_columns:
        # Text-Label-Spalte (Sorte/Probe) hat Vorrang: Kategorien sind der
        # fachliche Zweck des Versuchs (z.B. Kaffeesorten unterscheiden).
        best_text = max(text_reference_columns, key=lambda r: r['unique_values'])
        class_label_column = best_text['name']
        class_labels = df[class_label_column].astype(str).unique().tolist()
        analysis_mode = 'classification'
    elif reference_columns:
        for ref in reference_columns:
            values = df[ref['name']].astype(str)
            num_unique = values.nunique()
            if 2 <= num_unique <= 30 and values.str.len().mean() <= 40:
                class_label_column = str(ref['name'])
                class_labels = values.unique().tolist()
                analysis_mode = 'classification'
                break
    # Klassifikations-Samples (2026-10-08, Kaffee): ALLE Zeilen mit
    # Klassen-Label (nicht nur der Replica-Block) - bei
    # Messobjekt-wechselnden Datensaetzen ist der Replica-Block winzig
    # und die Klassifikation bekam zu wenige/gar keine Zeilen -> keine
    # Konfusionsmatrix. Gecappt wie die Kalibration (2000 Zeilen).
    if class_label_column and channel_names:
        label_series = df[class_label_column].astype(str)
        numeric_rows = df[channel_names].apply(
            pd.to_numeric, errors='coerce').dropna(how='any')
        numeric_rows = EnhancedDataPreparationAgent.detect_sensor_overflow(
            numeric_rows)['clean']
        paired = numeric_rows.join(label_series.rename('__label'),
                                   how='inner').dropna(subset=['__label'])
        if len(paired) >= 10:
            max_cls = min(2000, len(paired))
            step_cls = max(1, len(paired) // max_cls)
            cls_rows = paired.iloc[::step_cls].head(max_cls)
            classification_samples = [
                [float(v) for v in row]
                for row in cls_rows[channel_names].to_numpy().tolist()]
            classification_labels = cls_rows['__label'].astype(str).tolist()

    return {
        'usable': True,
        'dataset_type': 'measurement',
        'format': 'wide',
        'wavelength_column': 'channels',
        'intensity_column': 'channels',
        'num_points': len(series),
        'wavelength_min': min(wavelengths),
        'wavelength_max': max(wavelengths),
        'num_measurements': wide['measurement_count'],
        'preview': {
            'wavelengths': wavelengths,
            'intensities': intensities,
        },
        **({'classification_samples': classification_samples,
            'classification_labels': classification_labels}
           if classification_samples else {}),
        'metadata': {
            **wide.get('preamble_metadata', {}),
            'channel_count': len(series),
            'measurement_count': wide['measurement_count'],
            'channel_names': [c for c, _ in channels],
            'saturated_measurements': saturated_measurements,
            'saturated_values': saturated_values_total,
            'overflow_rows_total': len(overflow['saturated_rows']),
            'defective_channels': defective_channels,
            'target_name': target_name,
            'analysis_mode': analysis_mode,
            **({'class_label_column': class_label_column,
                'class_labels': class_labels}
               if class_label_column else {}),
            **({'reference_values': reference_values}
               if reference_values is not None else {}),
        },
        'numeric_references': reference_columns,
        'measurement_samples': measurement_samples,
        'calibration_samples': calibration_samples,
        **({'reference_values': reference_values}
           if reference_values is not None else {}),
    }



def _finite_pairs(df, wavelength_column, intensity_column):
    """Extract (wavelength, intensity) pairs where both values are finite
    numbers. Tolerates header/metadata rows inside numeric columns (same
    conversion contract as the OP7 crew bridge in file_views.py)."""
    from agents.data_preparation_agent import EnhancedDataPreparationAgent

    pairs = []
    for wl_raw, it_raw in zip(df[wavelength_column].tolist(), df[intensity_column].tolist()):
        try:
            wl = float(EnhancedDataPreparationAgent._normalise_decimal_string(wl_raw))
            it = float(EnhancedDataPreparationAgent._normalise_decimal_string(it_raw))
        except (TypeError, ValueError):
            continue
        if wl == wl and it == it:  # filter NaN
            pairs.append((wl, it))
    return pairs


def _extract_numeric_reference(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect numeric reference/target columns (e.g. brix, temperature) from
    parsed file metadata so supervised analyses can use them later."""
    references = []
    if not isinstance(metadata, dict):
        return references
    for key in ("brix", "reference_values", "reference", "y", "target"):
        value = metadata.get(key)
        if isinstance(value, (int, float)):
            references.append({"name": key, "value": value})
        elif isinstance(value, (list, tuple)) and value:
            references.append({"name": key, "count": len(value)})
    return references


def ingest_file(file_record) -> Dict[str, Any] | List[Dict[str, Any]]:
    """Ingest one GenericFile into a dataset entry (or several entries when
    the file is an archive, OP30) for the preparation report.

    Returns a dict with dataset info (wavelengths/intensities preview,
    quality metrics, metadata) or a usable=False marker with the reason;
    an archive returns one entry per inner file. Never raises: unusable
    files are reported, not fatal, so the user can adapt and re-upload.
    """
    entry: Dict[str, Any] = {
        "file_id": str(file_record.id),
        "file_name": file_record.name,
        "file_extension": file_record.file_extension,
        "file_category": file_record.file_category,
    }
    file_path = file_record.get_file_path()
    if not file_path or not Path(file_path).exists():
        entry.update({"usable": False, "reason": "File not found on server"})
        return entry

    # OP30: an archive is a container, not a spectrum file - every inner
    # file is ingested with the same rules as a directly uploaded file.
    archive = _archive_entries(file_record, file_path)
    if archive is not None:
        return archive

    return _ingest_single_file(file_record, file_path)


class _InnerFileRecord:
    """Minimal GenericFile stand-in for one file extracted from an archive
    (OP30): carries the inner file's identity so the shared ingest path
    (_metadata_only_entry, wide-format ingest) works unchanged."""

    def __init__(self, file_id: str, name: str):
        self.id = file_id
        self.name = name
        self.file_extension = Path(name).suffix.lower() or ".txt"
        self.file_category = "archive_inner"


def _extract_archive_members(file_path: str, loader) -> List[str]:
    """Extract archive members into a FRESH unique directory (OP30): the
    loader's own scan reuses one directory per archive basename, so two
    project uploads with the same archive name would see each other's
    inner files. Each project ingest therefore extracts into its own
    temporary directory. Size guard and candidate cap follow the loader
    contract. Never raises."""
    import os
    import tarfile
    import tempfile
    import zipfile

    try:
        extract_dir = tempfile.mkdtemp(prefix="nir_project_archive_")
        if os.path.splitext(file_path)[1].lower() == ".7z":
            import py7zr
            with py7zr.SevenZipFile(file_path, mode="r") as z:
                z.extractall(extract_dir)
        elif zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                total_size = sum(info.file_size for info in zip_ref.infolist())
                if total_size > loader.max_file_size:
                    return []
                zip_ref.extractall(extract_dir)
        else:
            with tarfile.open(file_path, "r:*") as tar_ref:
                safe_members = []
                total_size = 0
                for member in tar_ref.getmembers():
                    if not member.isfile():
                        continue
                    total_size += member.size
                    if total_size > loader.max_file_size:
                        return []
                    safe_members.append(member)
                try:
                    tar_ref.extractall(extract_dir, members=safe_members,
                                       filter="data")
                except TypeError:
                    tar_ref.extractall(extract_dir, members=safe_members)
        members = []
        for root, _dirs, files in os.walk(extract_dir):
            for name in files:
                members.append(os.path.join(root, name))
    except Exception:
        return []
    return members[:loader._MAX_ARCHIVE_CANDIDATES]


def _archive_entries(file_record, file_path: str) -> List[Dict[str, Any]] | None:
    """An archive (ZIP/tar) is a container of files, not one spectrum file
    (OP30): a project ZIP bundles a description and several measurement
    files (train/test). Treating the archive as a single spectrum file
    picks ONE inner file and garbles its columns into a fake wavelength
    axis ('No finite wavelength/intensity rows'). Instead every inner file
    is extracted and ingested with the same rules as a directly uploaded
    file (wide format -> two-column -> metadata source), each under its own
    name and id ('<archive-file-id>:<inner-name>') so the editor shows one
    row per inner file. Returns None when the file is not an archive or
    extraction failed - the caller then runs the single-file path.
    Never raises."""
    import os
    import tarfile
    import zipfile

    archive_ext = os.path.splitext(file_path)[1].lower()
    # Strukturierte Dokumente (docx/xlsx, Kaffee-Vorfall 2026-10-09) sind
    # KEINE Archive, obwohl sie ZIP-Container sind: als 'Archiv'
    # zerfiel das Versuchsprotokoll in 13 XML-Innendateien und der
    # Metadaten-Inhalt (Experimentator, Geraet, Datum) ging verloren.
    # Erkennung inhaltlich, nicht nach Endung: nur echte Archive
    # (docProps/word/xl ausschliessen) werden als Container behandelt.
    # 7z-Archive (Kaffee-Vorfall 2026-10-09): ohne diese Erkennung fiel
    # Kaffee.7z in den Single-File-Pfad, der Agenten-Loader extrahierte
    # intern und lief EINEN Eintrag ohne Sentinel-/Kanal-Behandlung und
    # ohne die Protokoll-Metadaten (OP30 'jede Innendatei einzeln' lief
    # fuer 7z nie). py7zr ist optional (MIT) - ohne es bleibt der ehrliche
    # Single-File-Fallback.
    is_7z = archive_ext == ".7z"
    try:
        is_archive = is_7z or zipfile.is_zipfile(file_path) or (
            archive_ext in (".tar", ".tar.gz", ".tgz", ".gz", ".bz2", ".xz")
            and tarfile.is_tarfile(file_path))
    except Exception:
        return None
    if not is_archive:
        return None
    if is_7z:
        try:
            import py7zr  # noqa: F401
        except ImportError:
            return None
    if zipfile.is_zipfile(file_path):
        try:
            with zipfile.ZipFile(file_path) as zf:
                names = set(zf.namelist())
            doc_markers = ({"word/document.xml", "xl/workbook.xml",
                            "ppt/presentation.xml"})
            if names & doc_markers:
                return None
        except Exception:
            pass
    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    loader = EnhancedDataPreparationAgent(
        input_directory=str(Path(file_path).parent),
        output_directory=str(Path(file_path).parent / "processed"),
    )
    candidates = _extract_archive_members(file_path, loader)
    if not candidates:
        return None
    entries: List[Dict[str, Any]] = []
    for candidate in candidates:
        name = Path(candidate).name
        inner = _InnerFileRecord(f"{file_record.id}:{name}", name)
        entry = _ingest_single_file(inner, candidate)
        entry["archive_file"] = file_record.name
        entries.append(entry)
    return entries


def _file_text_for_llm(file_path: str, loader) -> str:
    """The text a file contributes to the LLM metadata extraction: the
    raw text lines when readable, plus the metadata key/value pairs the
    deterministic layer already collected (so the KI sees header facts
    of binary/structured formats too). Never raises."""
    parts = []
    try:
        from agents.data_preparation_agent import read_text_lines
        lines = read_text_lines(file_path)
        text = "".join(ln for ln in lines[:400] if ln.strip())
        if text.strip():
            parts.append(text[:6000])
    except Exception:
        pass
    if not parts:
        # Strukturierte Dokumente (docx, Kaffee-Vorfall 2026-10-09): das
        # Versuchsprotokoll traegt den Kontext (Experimentator, Geraet,
        # Datum, Ort) - ohne diese Quelle sieht die KI den Operator nie.
        try:
            from agents.data_preparation_agent import read_document_text
            doc_text = read_document_text(file_path)
            if doc_text.strip():
                parts.append(doc_text[:6000])
        except Exception:
            pass
    return "\n".join(parts)


def _make_loader(file_path: str):
    """One loader instance for a file's directory (shared by the spectral
    load and the KI metadata pass)."""
    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    return EnhancedDataPreparationAgent(
        input_directory=str(Path(file_path).parent),
        output_directory=str(Path(file_path).parent / "processed"),
    )


def _ki_metadata_pass(entry: Dict[str, Any], file_path: str, loader) -> None:
    """KI-first metadata extraction (OP31): Mistral via Ollama reads the
    file text and extracts the canonical metadata fields BEFORE the
    deterministic result is final. Strict anti-hallucination: values the
    LLM reports without verbatim evidence are rejected in code
    (services/metadata_llm.py). Hard facts win: when the deterministic
    layer already holds a value for a field and the LLM disagrees, the
    conflict is recorded and escalated to the user (open_questions) -
    never silently resolved. Never raises; without Ollama the entry
    keeps its deterministic metadata (resilience)."""
    try:
        from services.metadata_llm import MetadataLLMService
        text = _file_text_for_llm(file_path, loader)
        if not text.strip():
            return
        service = MetadataLLMService()
        if not service.client.is_available():
            entry["metadata_sources"] = entry.get("metadata_sources") or {}
            from services.ollama_health import ollama_reachable
            if ollama_reachable(service.client.base_url):
                entry["metadata_sources"]["llm"] = (
                    f"Ollama erreichbar, Modell {service.client.model} fehlt - "
                    "bitte laden: docker compose exec ollama ollama pull "
                    f"{service.client.model} (deterministisch bis dahin)")
            else:
                entry["metadata_sources"]["llm"] = "nicht erreichbar (deterministisch)"
            return
        result = service.extract(text, file_name=str(entry.get("file_name")))
        if result is None:
            return
        metadata = entry.setdefault("metadata", {})
        sources = entry.setdefault("metadata_sources", {})
        questions = entry.setdefault("open_questions", [])
        for field, payload in result.get("fields", {}).items():
            value = str(payload.get("value") or "").strip()
            existing = metadata.get(field)
            if existing in (None, ""):
                # KI-first: the LLM found what the deterministic layer missed
                metadata[field] = value
                sources[field] = "ki"
            elif _norm_value(existing) != _norm_value(value):
                # Conflict: the deterministic hard fact wins, the LLM
                # disagreement is escalated to the user (never hidden).
                questions.append(
                    f"Metadatenkonflikt für '{field}': Deterministische "
                    f"Extraktion lief '{existing}', die KI las '{value}'. "
                    f"Welcher Wert ist korrekt?")
                sources[field] = f"konflikt (deterministisch: '{existing}', ki: '{value}')"
            else:
                sources[field] = "ki bestätigt"
        for q in result.get("questions", []):
            questions.append(f"KI-Frage zu '{entry.get('file_name')}': {q}")
        if result.get("rejected"):
            entry["llm_rejected_values"] = result["rejected"]
    except Exception:
        logger.exception("LLM metadata pass failed (non-fatal): %s", file_path)


def _norm_value(value: Any) -> str:
    return str(value if value is not None else "").strip().lower()


def _ingest_single_file(record, file_path: str) -> Dict[str, Any]:
    """Ingest one concrete file path (a directly uploaded file or a file
    extracted from an archive, OP30) into a dataset entry with the shared
    rules: wide-format detection first, then the S3 two-column loader,
    then the metadata-only source. Never raises."""
    entry: Dict[str, Any] = {
        "file_id": str(record.id),
        "file_name": record.name,
        "file_extension": record.file_extension,
        "file_category": record.file_category,
    }

    # OP14: multi-channel wide-format exports (one row per measurement, one
    # column per wavelength channel, e.g. A_410..L_940) must not go through
    # the two-column loader - it garbles channels and counters into a fake
    # wavelength axis. Detect first, fall back to the S3 loader.
    wide = _detect_wide_format(file_path)
    if wide:
        entry.update(_ingest_wide_format(record, file_path, wide))
        logger.info('Wide-format ingest for %s: %s channels, %s measurements',
                    file_path, len(wide['channel_columns']),
                    wide['measurement_count'])
        _derived_metadata_pass(entry)
        _ki_metadata_pass(entry, file_path, _make_loader(file_path))
        return entry

    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    loader = EnhancedDataPreparationAgent(
        input_directory=str(Path(file_path).parent),
        output_directory=str(Path(file_path).parent / "processed"),
    )
    spectral = loader._load_spectral_data(file_path)
    if not spectral or spectral.get("data") is None or len(spectral.get("data", [])) == 0:
        text_metadata = _metadata_only_entry(record, file_path, loader)
        if text_metadata is not None:
            logger.info('Metadata-only ingest for %s (description file with '
                        'no measurement values)', file_path)
            return text_metadata
        # OP59-Nachtrag: KI-Rettungsstufe - auch fuer Dateien, die weder als
        # Spektrum noch als beschreibender Text erkannt wurden, ist die
        # Metadaten-Untersuchung Pflicht. Der KI-Pass sieht den Dateitext
        # (soweit lesbar) und kann kanonische Felder mit Beleg oder
        # Klaerungsfragen liefern; nur wenn auch die KI nichts findet,
        # bleibt der ehrliche usable=False-Marker mit Grund.
        ki_entry = _ki_rescue_entry(entry, file_path, loader)
        if ki_entry is not None:
            logger.info('KI-Rescue ingest for %s (metadata from LLM pass)',
                        file_path)
            return ki_entry
        # Struktur-Klaerungsdialog (Stufe B): statt stillem usable=False
        # erhaelt der Eintrag die KI-Struktur-Analyse (Vorschlag +
        # Klaerungsfragen). Der Nutzer klart im Dialog, die Antworten
        # fuehren uber den Struktur-Endpunkt zu einem erneuten Load - und
        # die bestaetigte Struktur wird als StructureProfile gelernt,
        # damit das naechste File dieses Formats automatisch laeuft.
        try:
            from services.structure_dialog import ki_structure_proposal
            proposal = ki_structure_proposal(file_path)
        except Exception:
            proposal = None
        entry.update({
            "usable": False,
            "reason": "Not parseable as spectral data (S3 loader)",
            "structure_dialog": {
                "available": proposal is not None,
                "signature": (proposal or {}).get("signature"),
                "proposal": (proposal or {}).get("proposal"),
                "questions": (proposal or {}).get("questions") or [
                    {"field": "layout",
                     "question": "Wie sind die Daten aufgebaut: zwei Spalten "
                                 "(Wellenlaenge/Intensitaet) oder Kanaele als "
                                 "Spalten (eine Messung je Zeile)?"},
                ],
            },
        })
        return entry

    df = spectral.get("data")
    wavelength_column = spectral.get("wavelength_column")
    intensity_column = spectral.get("intensity_column")
    if wavelength_column not in getattr(df, "columns", []) or intensity_column not in getattr(df, "columns", []):
        entry.update({"usable": False, "reason": "Wavelength/intensity columns missing"})
        return entry

    pairs = _finite_pairs(df, wavelength_column, intensity_column)
    if not pairs:
        entry.update({"usable": False, "reason": "No finite wavelength/intensity rows"})
        return entry

    wavelengths = [p[0] for p in pairs]
    intensities = [p[1] for p in pairs]
    metadata = spectral.get("metadata") or {}
    _sync_recommended_aliases(metadata)
    entry.update({
        "usable": True,
        "dataset_type": "measurement",
        "wavelength_column": str(wavelength_column),
        "intensity_column": str(intensity_column),
        "num_points": len(pairs),
        "wavelength_min": min(wavelengths),
        "wavelength_max": max(wavelengths),
        "preview": {
            "wavelengths": wavelengths[:64],
            "intensities": intensities[:64],
        },
        "metadata": metadata,
        "numeric_references": _extract_numeric_reference(metadata),
    })
    _derived_metadata_pass(entry)
    _ki_metadata_pass(entry, file_path, loader)
    return entry


def _metadata_only_entry(file_record, file_path, loader) -> Dict[str, Any] | None:
    """A text file without measurement values can still be the experiment's
    documentation (prose description, sample background): its metadata is
    extracted and the file is listed as a metadata source instead of being
    discarded as 'not parseable'. Returns None for binary/unreadable files
    or when no metadata was found - those keep the honest usable=False
    marker. Never raises."""
    metadata = {}
    # Strukturierte Dokumente (docx, Kaffee-Vorfall 2026-10-09): der
    # echte Dokumenttext ist die PRIMAERE Quelle - read_text_lines
    # dekodiert docx als Binaermuell, dessen 'description' zu Recht
    # verworfen wird und den DOCX-Pfad blockierte. Nie hartkodiert:
    # nur wenn echten Dokumenttext gibt.
    try:
        from agents.data_preparation_agent import (
            read_document_text, EnhancedDataPreparationAgent)
        doc_lines = read_document_text(file_path).splitlines()
        if doc_lines:
            metadata = (EnhancedDataPreparationAgent
                        ._extract_metadata_from_lines(doc_lines))
    except Exception:
        metadata = {}
    if not metadata:
        try:
            metadata = loader._extract_text_metadata(file_path)
        except Exception:
            metadata = {}
    if not metadata:
        return None
    # 2026-10-08 (Kaffee-Datensatz): experiment_name/purpose sind jetzt
    # kanonische Felder - eine Beschreibungsdatei mit Versuchsname/Zweck
    # ist ein WERTVOLLER Kontext-Datensatz, auch wenn sie sonst nur eine
    # description traegt. Verworfen wird weiterhin ehrlich:
    # (a) gar keine Extraktion, (b) NUR eine description, die aus
    # Binaermuell stammt (hoher Anteil undruckbarer Zeichen) - Binaer-
    # Rauschen ist keine Metadatenquelle (OP28 T5m).
    if not metadata:
        return None
    only_description = set(metadata.keys()) == {"description"}
    if only_description:
        text = str(metadata.get("description") or "")
        # Binaermuell-Erkennung: Anteil einfacher Textzeichen (ASCII-
        # Buchstaben/Ziffern/Satz + Leerzeichen/Umbruch). Zufallsbytes
        # erzeugen viele Steuer- und Exotic-Unicode-Zeichen; echter
        # Prosa-Text liegt fast immer bei >0.9 (OP28 T5m).
        text_chars = sum(1 for ch in text
                         if ch.isalnum() or ch in " \n\r\t.,;:!?-_()/'\"")
        if not text or text_chars / len(text) < 0.75:
            return None
    _sync_recommended_aliases(metadata)
    entry = {
        "file_id": str(file_record.id),
        "file_name": file_record.name,
        "file_extension": file_record.file_extension,
        "file_category": file_record.file_category,
        "usable": True,
        "dataset_type": "metadata",
        "metadata": metadata,
    }
    _derived_metadata_pass(entry)
    _ki_metadata_pass(entry, file_path, loader)
    return entry


def _ki_rescue_entry(entry: Dict[str, Any], file_path: str, loader) -> Dict[str, Any] | None:
    """KI-Rettungsstufe (OP59-Nachtrag): Dateityp-agnostische
    Metadaten-Untersuchung ist Pflicht - auch fuer Dateien, die weder als
    Spektrum noch als beschreibender Text erkannt wurden. Der KI-Pass
    (Mistral via Ollama, mit Anti-Halluzinations-Belegpruefung wie immer)
    sieht den lesbaren Dateitext und kann kanonische Felder liefern oder
    Klaerungsfragen aufwerfen. Findet die KI nichts, bleibt der ehrliche
    usable=False-Marker beim Aufrufer. Gibt eine ergaenzte Entry-Kopie
    zurueck (dataset_type 'metadata', metadata_sources 'ki'), oder None,
    wenn die KI nichts beitragen kann. Never raises."""
    try:
        from services.metadata_llm import MetadataLLMService
        text = _file_text_for_llm(file_path, loader)
        if not text.strip():
            return None
        service = MetadataLLMService()
        if not service.client.is_available():
            return None
        result = service.extract(text, file_name=str(entry.get("file_name")))
        if result is None:
            return None
        fields = {field: str(payload.get("value") or "").strip()
                  for field, payload in result.get("fields", {}).items()
                  if str(payload.get("value") or "").strip()}
        questions = [q for q in result.get("questions", []) if str(q).strip()]
        if not fields and not questions:
            return None
        rescue = dict(entry)
        rescue.update({
            "usable": True,
            "dataset_type": "metadata",
            "metadata": fields,
            "metadata_sources": {field: "ki" for field in fields},
            "open_questions": [f"KI-Frage zu '{entry.get('file_name')}': {q}"
                               for q in questions],
        })
        if result.get("rejected"):
            rescue["llm_rejected_values"] = result["rejected"]
        return rescue
    except Exception:
        logger.exception("KI rescue pass failed (non-fatal): %s", file_path)
        return None

def _propagate_project_metadata(datasets: List[Dict[str, Any]]) -> None:
    """Fill measurement datasets with the metadata of the project's
    description documents (OP34): a ZIP with Oel_Meta.txt + measurement
    matrices carries operator/instrument/environment ONLY in the prose
    file - the measurement entries themselves showed almost no metadata
    in the report. The description metadata is project context: it fills
    MISSING fields of the measurement entries (never overwrites), the
    source is transparently recorded so the report shows where the value
    came from. Never raises."""
    try:
        context_fields: Dict[str, str] = {}
        for dataset in datasets:
            if dataset.get("dataset_type") == "metadata" and dataset.get("usable"):
                for key, value in (dataset.get("metadata") or {}).items():
                    if value not in (None, "") and key not in context_fields:
                        context_fields[key] = str(value)
        if not context_fields:
            return
        for dataset in datasets:
            if dataset.get("dataset_type") == "metadata":
                continue
            metadata = dataset.get("metadata") or {}
            sources = dataset.setdefault("metadata_sources", {})
            filled = False
            for key, value in context_fields.items():
                if metadata.get(key) in (None, ""):
                    metadata[key] = value
                    sources[key] = "projekt-kontext"
                    filled = True
            if filled:
                dataset["metadata"] = metadata
    except Exception:
        logger.exception("Project metadata propagation failed (non-fatal)")


def _ki_forward_questions(entry: Dict[str, Any],
                        standards: Dict[str, List[str]]) -> None:
    """KI asks the user explicitly for standard-relevant fields that the
    data cannot provide itself (OP33/OP34): instead of one isolated
    question per field the KI CONSOLIDATES the missing fields thematically
    (sensor: type/model/serial number, measurement parameters: integration
    time) into one question per topic - the user answers a coherent
    request, not a form letter series. The KI does NOT guess values
    (anti-hallucination); it asks, naming the standards the fields unlock.
    Never raises; without Ollama the deterministic template question is
    used so the user is still asked."""
    try:
        metadata = entry.get("metadata") or {}
        questions = entry.setdefault("open_questions", [])
        asked_topics = {q.split("thema '")[1].split("'")[0]
                        for q in questions if "thema '" in q}
        # Grundregel (User 2026-10-09): keine hartkodierten Feld-Mappings.
        # Begriffe ohne kanonische Zuordnung (z. B. 'Bediener' ?=
        # operator_name) entscheidet die KI im LLM-Pass; entscheidet auch
        # sie nicht eindeutig, wird der Nutzer gefragt - die Rohwerte
        # fallen nie still weg.
        for mapping_q in (metadata.pop("field_mapping_questions", None)
                          or []):
            questions.append(
                f"KI-Frage zu '{entry.get('file_name')}': {mapping_q}")
        # Zielwert-Thema: nur fragen, wenn weder Metadaten noch die
        # Messwertlisten einen Rueckschluss zulassen (target_name fehlt und
        # keine geeignete Referenzspalte existiert). Bei
        # analysis_mode='classification' (Kategorien-Versuch, z.B.
        # Kaffeesorten unterscheiden) ist die Kalibrationsziel-Frage
        # fachlich falsch - die Klassen-Labels sind das Analyseziel.
        if metadata.get("analysis_mode") == "classification":
            asked_topics.add("zielwert")  # Thema gilt als geklaert
        if not (metadata.get("target_name") or entry.get("reference_values")):
            if "zielwert" not in asked_topics:
                std = sorted({name for name, req in (standards or {}).items()
                              if "reference_values" in req})
                std_part = (f" (relevant fuer {', '.join(std)})" if std
                            else "")
                questions.append(
                    "KI-Frage zum Thema 'zielwert'" + std_part + ": "
                    "Es konnte kein eindeutiger Zielwert (Kalibrationsziel) "
                    "aus den Messdaten oder Metadaten abgeleitet werden. "
                    "Fehlende Felder: target_name. "
                    "Bitte im Metadaten-Editor ergaenzen.")

        topics = [
            ("sensor",
             ("instrument_type", "instrument_model", "serial_number"),
             "Der Sensor ist nur unvollst\u00e4ndig dokumentiert "
             "(Name/Typ, Modell, Seriennummer). Bitte geben Sie im "
             "Metadaten-Editor die Sensorangaben zusammen an: "
             "Sensor-Name/Typ, Modell und Seriennummer."),
            ("messparameter",
             ("integration_time",),
             "Die Integrationszeit ist nicht aus den Messdaten ableitbar. "
             "Mit welcher Integrationszeit (ms) wurden die Spektren "
             "aufgenommen?"),
        ]

        for topic, fields, template in topics:
            if topic in asked_topics:
                continue
            missing = [f for f in fields if not metadata.get(f)]
            if not missing:
                continue
            std = sorted({name for name, req in (standards or {}).items()
                          for f in missing if f in req})
            std_part = f" (relevant f\u00fcr {', '.join(std)})" if std else ""
            present = [f for f in fields if metadata.get(f)]
            present_part = (f" Bekannt ist bereits: "
                            f"{', '.join(f'{f}={metadata[f]}' for f in present)}."
                            if present else "")
            question = None
            try:
                from services.metadata_llm import OllamaMetadataClient
                client = OllamaMetadataClient()
                if client.is_available():
                    fields_block = ", ".join(missing)
                    llm = client.chat(
                        f"Formuliere EINE kurze, zusammenfassende deutsche "
                        f"Frage an einen NIR-Spektroskopie-Nutzer nach den "
                        f"fehlenden Sensor-/Mess-Metadaten: {fields_block}."
                        f"{present_part} Nenne die Felder in einer Frage."
                        f"{std_part} Antworte NUR mit dem Fragetext.")
                    if isinstance(llm, str) and llm.strip() and len(llm) <= 400:
                        question = llm.strip()
                        # Der Client erzwingt format=json - die Antwort
                        # kann als JSON-Objekt kommen. Ehrlich entpacken
                        # statt das rohe JSON in die Frage zu kleben
                        # (User-Befund 2026-10-09: '{"Question (German):
                        # ...": "..."}' im Fragetext).
                        try:
                            import json as _json
                            parsed = _json.loads(question)
                            if isinstance(parsed, dict):
                                for _key in ('question', 'frage', 'text',
                                             'frage_text'):
                                    if isinstance(parsed.get(_key), str):
                                        parsed = parsed[_key]
                                        break
                                else:
                                    vals = [v for v in parsed.values()
                                            if isinstance(v, str)]
                                    parsed = vals[0] if vals else None
                            if isinstance(parsed, str) and parsed.strip():
                                question = parsed.strip()
                            else:
                                question = None
                        except (ValueError, TypeError):
                            pass
            except Exception:
                question = None
            if not question:
                question = template
            fields_part = ", ".join(missing)
            known_part = (f" Bekannt ist bereits: "
                         f"{', '.join(f'{f}={metadata[f]}' for f in present)}."
                         if present else "")
            questions.append(
                f"KI-Frage zum Thema '{topic}'{std_part}: {question} "
                f"Fehlende Felder: {fields_part}.{known_part} "
                "Bitte im Metadaten-Editor erg\u00e4nzen.")
    except Exception:
        logger.exception("KI forward question pass failed (non-fatal)")


def _ki_relevance_pass(metadata_assessment: Dict[str, Any],
                        datasets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """KI-first NIR relevance assessment (OP32): Mistral judges which of
    the collected metadata fields matter for NIR spectroscopy and which
    standards they satisfy, so the recommendations become concrete and
    prioritised instead of a generic percentage. Guarded in code: only
    field names from the actual present/missing lists and only known
    standards survive. Never raises; None offline (the report then keeps
    the deterministic standards verdicts)."""
    try:
        from services.metadata_llm import MetadataRelevanceService
        service = MetadataRelevanceService()
        if not service.client.is_available():
            metadata_assessment["ki_relevance_status"] = (
                "nicht erreichbar (deterministische Standards-Bewertung)")
            return None
        present = list(metadata_assessment.get("metadata_fields") or [])
        missing = list(metadata_assessment.get("missing_recommended_fields") or [])
        context = " ".join(
            str(d.get("file_name")) for d in datasets[:10])
        relevance = service.assess(
            present, missing, _metadata_standards(), context)
        if relevance is None:
            metadata_assessment["ki_relevance_status"] = (
                "keine verwertbare Antwort (deterministische Bewertung)")
        return relevance
    except Exception:
        logger.exception("KI relevance pass failed (non-fatal)")
        return None


def _derived_metadata_pass(entry: Dict[str, Any]) -> None:
    """Derive standard-relevant metadata from the loaded measurement data
    (OP33): wavelength_range and resolution are hard facts computed from
    the dataset's own wavelength axis - the KI exposes them to the user as
    suggestions instead of listing them as 'missing' when the data already
    carries the answer. scan_count mirrors the measurement count of wide
    exports. Fields the data cannot provide (integration_time,
    instrument_model) stay honestly missing - the KI forward-question pass
    asks the user for them. Never raises, never overwrites."""
    try:
        if not entry.get("usable"):
            return
        metadata = entry.setdefault("metadata", {})
        sources = entry.setdefault("metadata_sources", {})
        wmin = entry.get("wavelength_min")
        wmax = entry.get("wavelength_max")
        num = entry.get("num_points")
        if wmin is None or wmax is None or num in (None, 0):
            return
        wmin = float(wmin)
        wmax = float(wmax)
        if not metadata.get("wavelength_range"):
            span = wmax - wmin
            metadata["wavelength_range"] = f"{wmin:.1f}-{wmax:.1f} nm ({span:.1f} nm Spanne, {num} Punkte)"
            sources["wavelength_range"] = "ki (aus Daten berechnet)"
        if not metadata.get("resolution") and num > 1 and wmax > wmin:
            step = (wmax - wmin) / (num - 1)
            metadata["resolution"] = f"{step:.2f} nm ({num} Punkte)"
            sources["resolution"] = "ki (aus Daten berechnet)"
        if not metadata.get("scan_count") and entry.get("num_measurements"):
            metadata["scan_count"] = str(entry["num_measurements"])
            sources["scan_count"] = "ki (aus Daten berechnet)"
    except Exception:
        logger.exception("Derived metadata pass failed (non-fatal)")


def _metadata_standards() -> Dict[str, List[str]]:
    """The NIR-relevant metadata standards (single source of truth). The
    field lists mirror the loader's METADATA_STANDARDS so the assessment
    and the KI relevance pass judge against the same requirements."""
    try:
        from agents.data_preparation_agent import EnhancedDataPreparationAgent
        return dict(EnhancedDataPreparationAgent.METADATA_STANDARDS or {})
    except Exception:
        return {}


def _standards_compliance(fields_found: Dict[str, int],
                          standards: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """Per-standard present/missing verdict for the report: the user sees
    which standard is satisfied by which fields and what is still missing
    - instead of a single high-level percentage."""
    result = []
    for name, required in (standards or {}).items():
        present = [f for f in required if f in fields_found]
        missing = [f for f in required if f not in fields_found]
        result.append({
            "standard": name,
            "present": present,
            "missing": missing,
            "satisfied": not missing,
        })
    return result


def _assess_metadata(datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Assess metadata completeness across the usable datasets (MO 2-4).
    OP31: the assessment is field-level - every dataset carries its fields
    with the source (ki / header / editor / deterministic) and a per-field
    rating, so the user sees WHERE each value came from and how good it is."""
    usable = [d for d in datasets if d.get("usable")]
    assessed = {"datasets_usable": len(usable), "datasets_total": len(datasets)}
    fields_found: Dict[str, int] = {}
    standards = _metadata_standards()
    for dataset in usable:
        sources = dataset.get("metadata_sources") or {}
        rating = {}
        for key, value in (dataset.get("metadata") or {}).items():
            fields_found[key] = fields_found.get(key, 0) + 1
            # OP32: alias mirrors (operator/instrument/acquisition_time) hold
            # the SAME value as their canonical twin - show the information
            # once in the report, under the canonical name.
            if key in RECOMMENDED_FIELD_ALIASES:
                continue
            source = sources.get(key) or "deterministisch"
            rating[key] = {
                "value": value,
                "source": source,
                "rating": "konflikt" if "konflikt" in str(source) else "ok",
            }
        if rating:
            dataset["metadata_rating"] = rating
        conflicts = [q for q in (dataset.get("open_questions") or [])
                     if "Konflikt" in q or "konflikt" in q]
        if conflicts:
            dataset.setdefault("metadata_rating", {})["konflikte"] = conflicts
    assessed["metadata_fields"] = sorted(fields_found)
    recommended = RECOMMENDED_METADATA_FIELDS
    missing = [f for f in recommended if f not in fields_found]
    assessed["missing_recommended_fields"] = missing
    assessed["overall_quality_score"] = round(
        100.0 * (len(recommended) - len(missing)) / len(recommended), 1
    ) if usable else 0.0
    # OP32: standards compliance - which of the NIR-relevant standards
    # (ASTM E1655, ISO 12099, ...) the collected fields satisfy, presented
    # not as a percentage but as a per-standard present/missing verdict so
    # the user knows WHAT to complete for WHICH standard.
    assessed["standards_compliance"] = _standards_compliance(
        fields_found, standards)
    # OP31: how much of the metadata the KI contributed (transparency about
    # the primary extractor) and the open questions that need an answer.
    ki_fields = sum(
        1 for d in usable
        for s in (d.get("metadata_sources") or {}).values()
        if str(s).startswith("ki"))
    assessed["ki_extracted_fields"] = ki_fields
    assessed["open_questions"] = [
        q for d in datasets for q in (d.get("open_questions") or [])]
    return assessed


def _recommendations(datasets: List[Dict[str, Any]], metadata_assessment: Dict[str, Any]) -> List[str]:
    """Concrete improvement recommendations for the user (phase 1 report).
    OP32: the KI relevance pass prioritises the missing fields by their
    importance for NIR spectroscopy and the standards they unlock, so the
    recommendations tell the user WHAT to complete for WHICH standard -
    not a bare percentage."""
    recommendations: List[str] = []
    for dataset in datasets:
        if not dataset.get("usable"):
            recommendations.append(
                f"„{dataset.get('file_name')}“ ist nicht als Spektrum auswertbar "
                f"({dataset.get('reason')}). Bitte Datei prüfen und ggf. angepasst neu hochladen."
            )
    relevance = metadata_assessment.get("ki_relevance") or {}
    prioritised = {str(p.get("field")): p
                   for p in relevance.get("priority_missing", [])}
    for field in metadata_assessment.get("missing_recommended_fields", []):
        entry = prioritised.get(field)
        if entry:
            std = ", ".join(entry.get("standards") or [])
            std_part = f" (relevant für {std})" if std else ""
            recommendations.append(
                f"Metadatenfeld „{field}“ fehlt{std_part}: {entry.get('reason')} "
                "Bitte im Metadaten-Editor ergänzen."
            )
        else:
            recommendations.append(
                f"Metadatenfeld „{field}“ fehlt: ergänzen, um die Metadatenbewertung zu verbessern."
            )
    # OP31: the KI escalates conflicts and open questions to the user -
    # they are recommendations that need an explicit answer, never silent.
    for dataset in datasets:
        for question in (dataset.get("open_questions") or []):
            recommendations.append(
                f"Offene KI-Frage zu „{dataset.get('file_name')}“: {question} "
                "Bitte im Metadaten-Editor klären."
            )
    if not recommendations:
        recommendations.append(
            "Alle Dateien sind als Messdaten verwertbar und die Metadaten sind vollständig - "
            "das Projekt kann zur Analyse freigegeben werden."
        )
    return recommendations


RECOMMENDED_METADATA_FIELDS = [
    "operator", "humidity", "temperature", "instrument", "acquisition_time"
]

# The loaders emit canonical names (operator_name, instrument_type,
# timestamp); the recommended fields use their short aliases. Both
# describe the SAME information - without a mapping the editor showed
# 'operator' and 'operator_name' as two fields with the same value.
RECOMMENDED_FIELD_ALIASES = {
    "operator": "operator_name",
    "instrument": "instrument_type",
    "acquisition_time": "timestamp",
}


def _sync_recommended_aliases(metadata: Dict[str, Any]) -> None:
    """Give every canonical loader field its recommended alias so the same
    information is not shown twice in the editor: the recommended field
    ('operator') mirrors the canonical loader field ('operator_name').
    Never raises, never overwrites existing values."""
    try:
        for alias, canonical in RECOMMENDED_FIELD_ALIASES.items():
            value = metadata.get(canonical)
            if value not in (None, "") and metadata.get(alias) in (None, ""):
                metadata[alias] = value
    except Exception:
        return


def apply_metadata_overrides(entry: Dict[str, Any], overrides: Dict[str, Any]) -> None:
    """Merge user-entered metadata overrides (OP13) into a dataset entry.

    Empty values are ignored so a user can clear a typo by keeping other
    fields intact; the merged fields are tracked for the report UI.
    """
    if not overrides:
        return
    merged = dict(entry.get("metadata") or {})
    applied = []
    for key, value in (overrides or {}).items():
        if value in (None, ""):
            continue
        merged[key] = value
        applied.append(key)
    entry["metadata"] = merged
    entry["metadata_user_entered"] = applied


def _ki_llm_status() -> Dict[str, Any]:
    """KI-first transparency (User-Befund 2026-10-09): das LLM ist der
    ganze Antrieb der Metadaten-Extraktion - die Aufbereitung muss
    sichtbar machen, OB es beteiligt war. Ohne LLM: ehrlicher Status
    mit konkreter Start-Anleitung (docker compose + ollama pull),
    damit der Nutzer das Problem selbst loesen kann. Never raises."""
    try:
        from services.metadata_llm import MetadataLLMService
        service = MetadataLLMService()
        if service.client.is_available():
            return {
                "available": True,
                "used": True,
                "model": service.client.model,
                "base_url": service.client.base_url,
                "message": (
                    f"KI beteiligt: lokale LLM ({service.client.model}) "
                    "liest jede Datei und extrahiert Metadaten."),
            }
        from services.ollama_health import ollama_reachable
        reachable = ollama_reachable(service.client.base_url)
        if reachable:
            return {
                "available": False,
                "used": False,
                "model": service.client.model,
                "base_url": service.client.base_url,
                "reason": "server_up_model_missing",
                "message": (
                    f"Ollama laeuft, aber das Modell '{service.client.model}' "
                    "fehlt - die Aufbereitung lief deterministisch ohne KI."),
                "solution": (
                    "Modell laden: docker compose exec ollama ollama pull "
                    f"{service.client.model} - danach 'Aufbereitung erneut "
                    "ausfuehren' klicken."),
            }
        return {
            "available": False,
            "used": False,
            "model": service.client.model,
            "base_url": service.client.base_url,
            "reason": "server_down",
            "message": (
                "Das lokale LLM (Ollama) ist nicht erreichbar - die "
                "Aufbereitung lief deterministisch ohne KI."),
            "solution": (
                "Ollama starten: docker compose up -d ollama (ggf. vorher "
                "'docker compose pull ollama'), dann Modell laden: "
                "docker compose exec ollama ollama pull "
                f"{service.client.model} - danach 'Aufbereitung erneut "
                "ausfuehren' klicken."),
        }
    except Exception as exc:
        return {"available": False, "used": False,
                "reason": f"status check failed: {exc}",
                "message": "KI-Status konnte nicht geprueft werden.",
                "solution": ""}


def build_preparation_report(project) -> Dict[str, Any]:
    """Build the full phase-1 preparation report for an AnalysisProject.

    The report contains: usable datasets (measurement series + metadata),
    metadata quality assessment and improvement recommendations. It is
    stored on project.preparation_report and rendered to the user.
    User-entered metadata overrides (project.metadata_overrides, OP13) are
    applied per file before the assessment.
    """
    overrides = getattr(project, "metadata_overrides", None) or {}
    datasets = []
    for f in project.files.all():
        entries = ingest_file(f)
        if isinstance(entries, dict):
            entries = [entries]
        for entry in entries:
            # Metadata overrides are keyed by file id; inner archive files
            # carry the '<archive-id>:<name>' key of their inner entry (OP30)
            # while direct files keep the plain file id.
            entry_overrides = overrides.get(str(entry.get("file_id")), None)
            if entry_overrides is None:
                entry_overrides = overrides.get(str(f.id), {}) \
                    if entry.get("file_id") == str(f.id) else {}
            apply_metadata_overrides(entry, entry_overrides)
            datasets.append(entry)
    _propagate_project_metadata(datasets)
    metadata_assessment = _assess_metadata(datasets)
    for dataset in datasets:
        if dataset.get("usable"):
            _ki_forward_questions(dataset, _metadata_standards())
    metadata_assessment = _assess_metadata(datasets)
    relevance = _ki_relevance_pass(metadata_assessment, datasets)
    if relevance:
        metadata_assessment["ki_relevance"] = relevance
    recommendations = _recommendations(datasets, metadata_assessment)
    usable_count = sum(1 for d in datasets if d.get("usable"))
    report = {
        "datasets": datasets,
        "metadata_quality": metadata_assessment,
        "recommendations": recommendations,
        "usable_dataset_count": usable_count,
        "total_dataset_count": len(datasets),
        "ki_status": _ki_llm_status(),
    }
    # OP53: sensor database reference check - does the sensor used in
    # this new project have a reference entry (documents) in the sensor
    # database? Honest result with links, appended to the report.
    try:
        from services.sensor_documents import (check_sensor_reference,
                                                instrument_types_from_report)
        instrument_types = []
        for dataset in datasets:
            metadata = dataset.get("metadata") or {}
            value = metadata.get("instrument_type") or metadata.get("instrument")
            if value:
                instrument_types.append(str(value))
        if not instrument_types:
            instrument_types = instrument_types_from_report(project)
        user = getattr(project, "user", None)
        report["sensor_reference"] = check_sensor_reference(
            instrument_types, user)
    except Exception as exc:
        logger.warning("Sensor reference check failed (degraded): %s", exc)
        report["sensor_reference"] = {"checked": [], "unknown": [],
                                      "error": str(exc)}
    project.preparation_report = report
    if usable_count:
        project.save(update_fields=["preparation_report", "updated_at"])
    else:
        project.save(update_fields=["preparation_report", "updated_at"])
    logger.info(
        "Preparation report for project %s: %s/%s usable datasets",
        project.id, usable_count, len(datasets),
    )
    # WORKFLOW_DESIGN.md stations 3/4: translate agent findings (sensor
    # standard values, comparable spectra) into user decisions. Never raises.
    try:
        from services.workflow_integration import integrate_preparation_report
        integrate_preparation_report(project, report)
    except Exception as exc:
        logger.warning("Workflow integration failed (non-fatal): %s", exc)
    return report
