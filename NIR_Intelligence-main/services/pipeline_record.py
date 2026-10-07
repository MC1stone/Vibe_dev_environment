"""PipelineRecord: reproducible processing chains per spectrum (M4 of the
interoperability plan).

Captures every processing step (loader, preprocessing operations with
parameters, derived columns) as a machine-readable record attached to the
loaded dataset, renders it as a Quarto methods section and exports the
processed spectrum as JCAMP-DX (ASTM E5795 style) for interchange with
commercial NIR software. Concept inspired by provenance logs in scientific
frameworks; implemented independently (license compliance, see
THIRD_PARTY_LICENSES.md - Mantid is GPL, concept-only).
"""

from typing import Any, Dict, List, Optional


def new_pipeline_record(source_file: str = "", fmt: str = "",
                        loader: str = "") -> Dict[str, Any]:
    return {
        "source_file": source_file,
        "format": fmt,
        "loader": loader,
        "operations": [],
        "unit": None,
    }


def add_operation(record: Dict[str, Any], name: str,
                  parameters: Optional[Dict[str, Any]] = None,
                  output_column: str = "") -> Dict[str, Any]:
    record["operations"].append({
        "operation": name,
        "parameters": parameters or {},
        "output_column": output_column,
    })
    return record


def pipeline_from_load_result(loaded: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Start a pipeline record from a unified loader result."""
    if not loaded:
        return new_pipeline_record()
    metadata = loaded.get("metadata") or {}
    record = new_pipeline_record(
        source_file=loaded.get("source_file", ""),
        fmt=loaded.get("format", ""),
        loader=loaded.get("loader", "unknown"),
    )
    record["unit"] = metadata.get("x_unit") or metadata.get("x_units")
    return record


def record_preprocessing(record: Dict[str, Any],
                          preprocessing_results: Dict[str, Any],
                          intensity_columns: Dict[str, Any],
                          smoothing_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Append applied preprocessing operations with their parameters."""
    if "SNV" in preprocessing_results:
        add_operation(record, "SNV", {}, intensity_columns.get("snv") or "")
    if "MSC" in preprocessing_results:
        add_operation(record, "MSC", {}, intensity_columns.get("msc") or "")
    if "Savitzky-Golay" in preprocessing_results:
        params = dict(smoothing_params or {})
        add_operation(record, "Savitzky-Golay", params,
                     intensity_columns.get("savitzky_golay") or "")
    if "BaselineCorrection" in preprocessing_results:
        add_operation(record, "BaselineCorrection", {},
                     intensity_columns.get("baseline_corrected") or "")
    if "Detrending" in preprocessing_results:
        add_operation(record, "Detrending", {},
                     intensity_columns.get("detrended") or "")
    return record


def methods_markdown(record: Dict[str, Any]) -> str:
    """Render the pipeline as a Quarto methods section."""
    lines = ["## Methoden / Methods", ""]
    src = record.get("source_file") or "unknown source"
    fmt = record.get("format") or "unknown format"
    loader = record.get("loader") or "unknown loader"
    lines.append(f"Datenquelle: `{src}` (Format `{fmt}`, Loader `{loader}`).")
    unit = record.get("unit")
    if unit:
        lines.append(f"Achseneinheit: `{unit}`.")
    ops: List[Dict[str, Any]] = record.get("operations") or []
    if not ops:
        lines.append("")
        lines.append("Keine Verarbeitungsschritte aufgezeichnet.")
        return "\n".join(lines)
    lines.append("")
    lines.append("Verarbeitungskette (in Reihenfolge):")
    lines.append("")
    for i, op in enumerate(ops, start=1):
        params = op.get("parameters") or {}
        param_str = ""
        if params:
            rendered = ", ".join(f"{k}={v}" for k, v in sorted(params.items()))
            param_str = f" ({rendered})"
        out = op.get("output_column")
        out_str = f" -> `{out}`" if out else ""
        lines.append(f"{i}. **{op['operation']}**{param_str}{out_str}")
    return "\n".join(lines)


def export_jcamp_dx(wavelengths: List[float], intensities: List[float],
                    title: str = "NIR-IP export",
                    x_unit: str = "1/CM", y_unit: str = "ARBITRARY UNITS",
                    pipeline: Optional[Dict[str, Any]] = None) -> str:
    """Serialize one spectrum as JCAMP-DX text, including the pipeline
    record in ##COMMENT= lines for round-trip provenance."""
    if len(wavelengths) != len(intensities):
        raise ValueError("wavelength and intensity axes differ in length")
    if not wavelengths:
        raise ValueError("empty spectrum")
    unit_aliases = {"nm": "NANOMETERS", "cm^-1": "1/CM", "um": "MICROMETERS"}
    x_unit_label = unit_aliases.get(str(x_unit).strip().lower() or "",
                                    "1/CM" if not str(x_unit).strip() else str(x_unit).upper())
    lines = [
        "##TITLE= " + title,
        "##JCAMP-DX= 4.24",
        "##DATA TYPE= INFRARED SPECTRUM",
        f"##ORIGIN= NIR Intelligence Platform",
        f"##XUNITS= {x_unit_label}",
        f"##YUNITS= {str(y_unit).upper()}",
        f"##XFACTOR= 1.0",
        "##YFACTOR= 1.0",
        f"##NPOINTS= {len(wavelengths)}",
        "##FIRSTX= " + f"{wavelengths[0]:.6G}",
        "##LASTX= " + f"{wavelengths[-1]:.6G}",
        "##XYDATA= (X++(Y..Y))",
    ]
    for x, y in zip(wavelengths, intensities):
        lines.append(f"{x:.6G} {y:.6G}")
    if pipeline:
        ops = pipeline.get("operations") or []
        comments = [f"pipeline_op_{i + 1}={op.get('operation')}"
                    f"({op.get('parameters') or {}})"
                    for i, op in enumerate(ops)]
        comments.insert(0, "pipeline_source="
                       + str(pipeline.get("source_file") or ""))
        lines.append("##COMMENT= " + " | ".join(comments))
    lines.append("##END=")
    return "\n".join(lines) + "\n"
