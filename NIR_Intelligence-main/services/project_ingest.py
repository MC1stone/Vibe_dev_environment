# NIR Intelligence Platform - Project ingest service (OP10)
# Phase 1 of the project workflow: turns the files of an AnalysisProject into
# usable datasets (measurement series + metadata) using the S3 format-agnostic
# loader (EnhancedDataPreparationAgent) and assesses metadata quality and
# data usability with improvement recommendations for the user. File-type
# and spectrometer agnostic per the init prompt ground rules.
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

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


def ingest_file(file_record) -> Dict[str, Any]:
    """Ingest one GenericFile into a dataset entry for the preparation report.

    Returns a dict with dataset info (wavelengths/intensities preview,
    quality metrics, metadata) or a usable=False marker with the reason.
    Never raises: unusable files are reported, not fatal, so the user can
    adapt and re-upload.
    """
    from agents.data_preparation_agent import EnhancedDataPreparationAgent

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

    # OP14: multi-channel wide-format exports (one row per measurement, one
    # column per wavelength channel, e.g. A_410..L_940) must not go through
    # the two-column loader - it garbles channels and counters into a fake
    # wavelength axis. Detect first, fall back to the S3 loader.
    wide = _detect_wide_format(file_path)
    if wide:
        entry.update(_ingest_wide_format(file_record, file_path, wide))
        logger.info('Wide-format ingest for %s: %s channels, %s measurements',
                    file_record.name, len(wide['channel_columns']),
                    wide['measurement_count'])
        return entry

    loader = EnhancedDataPreparationAgent(
        input_directory=str(Path(file_path).parent),
        output_directory=str(Path(file_path).parent / "processed"),
    )
    spectral = loader._load_spectral_data(file_path)
    if not spectral or spectral.get("data") is None or len(spectral.get("data", [])) == 0:
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
        "metadata": spectral.get("metadata") or {},
        "numeric_references": _extract_numeric_reference(spectral.get("metadata") or {}),
    })
    return entry


def _assess_metadata(datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Assess metadata completeness across the usable datasets (MO 2-4)."""
    usable = [d for d in datasets if d.get("usable")]
    assessed = {"datasets_usable": len(usable), "datasets_total": len(datasets)}
    fields_found: Dict[str, int] = {}
    for dataset in usable:
        for key in dataset.get("metadata", {}):
            fields_found[key] = fields_found.get(key, 0) + 1
    assessed["metadata_fields"] = sorted(fields_found)
    recommended = RECOMMENDED_METADATA_FIELDS
    missing = [f for f in recommended if f not in fields_found]
    assessed["missing_recommended_fields"] = missing
    assessed["overall_quality_score"] = round(
        100.0 * (len(recommended) - len(missing)) / len(recommended), 1
    ) if usable else 0.0
    return assessed


def _recommendations(datasets: List[Dict[str, Any]], metadata_assessment: Dict[str, Any]) -> List[str]:
    """Concrete improvement recommendations for the user (phase 1 report)."""
    recommendations: List[str] = []
    for dataset in datasets:
        if not dataset.get("usable"):
            recommendations.append(
                f"„{dataset.get('file_name')}“ ist nicht als Spektrum auswertbar "
                f"({dataset.get('reason')}). Bitte Datei prüfen und ggf. angepasst neu hochladen."
            )
    for field in metadata_assessment.get("missing_recommended_fields", []):
        recommendations.append(
            f"Metadatenfeld „{field}“ fehlt: ergänzen, um die Metadatenbewertung zu verbessern."
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
        entry = ingest_file(f)
        apply_metadata_overrides(entry, overrides.get(str(f.id), {}))
        datasets.append(entry)
    metadata_assessment = _assess_metadata(datasets)
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
