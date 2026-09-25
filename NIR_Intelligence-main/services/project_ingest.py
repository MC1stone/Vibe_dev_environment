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
    return {
        'channel_columns': channels,
        'header_row': header_row,
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

    series = []
    for col, wavelength_nm in channels:
        values = _wide_column_numeric(df[col])
        if values.empty:
            continue
        series.append((wavelength_nm, float(values.median()), int(len(values))))
    if len(series) < 8:
        return {'usable': False,
                'reason': 'Wide-Format erkannt, aber zu wenige auswertbare Kanäle'}
    wavelengths = [s[0] for s in series]
    intensities = [s[1] for s in series]

    reference_columns = []
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
            saturated = numeric[(numeric >= 2 ** 31).any(axis=1)]
            saturated_measurements = int(len(saturated))
            numeric = numeric[~(numeric >= 2 ** 31).any(axis=1)]
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
    if channel_names:
        numeric_all = df[channel_names].apply(pd.to_numeric, errors='coerce') \
            .dropna(how='any')
        numeric_all = numeric_all[~(numeric_all >= 2 ** 31).any(axis=1)]
        target_keys = ('brix', 'zucker', 'sugar', 'refe', 'target',
                       'kalibration', 'calibration', 'y')
        ordered_refs = sorted(
            reference_columns,
            key=lambda r: 0 if any(k in str(r['name']).lower()
                                    for k in target_keys) else 1)
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
            break

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
        'metadata': {
            'channel_count': len(series),
            'measurement_count': wide['measurement_count'],
            'channel_names': [c for c, _ in channels],
            'saturated_measurements': saturated_measurements,
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
        if zipfile.is_zipfile(file_path):
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
    try:
        is_archive = zipfile.is_zipfile(file_path) or (
            archive_ext in (".tar", ".tar.gz", ".tgz", ".gz", ".bz2", ".xz")
            and tarfile.is_tarfile(file_path))
    except Exception:
        return None
    if not is_archive:
        return None
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
        entry.update({"usable": False, "reason": "Not parseable as spectral data (S3 loader)"})
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
    _ki_metadata_pass(entry, file_path, loader)
    return entry


def _metadata_only_entry(file_record, file_path, loader) -> Dict[str, Any] | None:
    """A text file without measurement values can still be the experiment's
    documentation (prose description, sample background): its metadata is
    extracted and the file is listed as a metadata source instead of being
    discarded as 'not parseable'. Returns None for binary/unreadable files
    or when no metadata was found - those keep the honest usable=False
    marker. Never raises."""
    try:
        metadata = loader._extract_text_metadata(file_path)
    except Exception:
        return None
    if not metadata or all(key == "description" for key in metadata):
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
    _ki_metadata_pass(entry, file_path, loader)
    return entry


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
    }
    project.preparation_report = report
    if usable_count:
        project.save(update_fields=["preparation_report", "updated_at"])
    else:
        project.save(update_fields=["preparation_report", "updated_at"])
    logger.info(
        "Preparation report for project %s: %s/%s usable datasets",
        project.id, usable_count, len(datasets),
    )
    return report
