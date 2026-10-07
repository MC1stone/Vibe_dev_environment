"""M4 verification: PipelineRecord reproducibility (M4).

Covers record construction from loader results, preprocessing capture with
parameters, Quarto methods rendering and JCAMP-DX export round-tripped
through the M2 parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from services.pipeline_record import (
    add_operation,
    export_jcamp_dx,
    methods_markdown,
    new_pipeline_record,
    pipeline_from_load_result,
    record_preprocessing,
)
from services.jcamp_parser import parse_jcamp_dx


def test_new_record_and_add_operation():
    rec = new_pipeline_record("a.spc", ".spc", "spc_loader")
    add_operation(rec, "SNV", {}, "intensity_snv")
    add_operation(rec, "Savitzky-Golay", {"window_size": 5, "polyorder": 2},
                  "intensity_sg")
    ops = rec["operations"]
    assert ops[0]["operation"] == "SNV"
    assert ops[1]["parameters"] == {"window_size": 5, "polyorder": 2}
    assert ops[1]["output_column"] == "intensity_sg"


def test_pipeline_from_load_result():
    loaded = {
        "source_file": "x.jdx",
        "format": ".jdx",
        "metadata": {"x_units": "1/CM"},
    }
    rec = pipeline_from_load_result(loaded)
    assert rec["source_file"] == "x.jdx"
    assert rec["unit"] == "1/CM"
    assert rec["operations"] == []


def test_record_preprocessing_captures_all():
    rec = new_pipeline_record()
    record_preprocessing(
        rec,
        {"SNV": True, "MSC": True, "Savitzky-Golay": True,
         "BaselineCorrection": True, "Detrending": True},
        {"snv": "i_snv", "msc": "i_msc", "savitzky_golay": "i_sg",
         "baseline_corrected": "i_bc", "detrended": "i_dt"},
        smoothing_params={"window_size": 7, "polyorder": 3},
    )
    names = [op["operation"] for op in rec["operations"]]
    assert names == ["SNV", "MSC", "Savitzky-Golay",
                     "BaselineCorrection", "Detrending"]
    sg = next(op for op in rec["operations"]
              if op["operation"] == "Savitzky-Golay")
    assert sg["parameters"] == {"window_size": 7, "polyorder": 3}


def test_methods_markdown_contains_steps():
    rec = new_pipeline_record("a.csv", ".csv", "csv_loader")
    add_operation(rec, "SNV", {}, "i_snv")
    add_operation(rec, "Savitzky-Golay", {"window_size": 5}, "i_sg")
    md = methods_markdown(rec)
    assert "## Methoden" in md
    assert "1. **SNV**" in md
    assert "2. **Savitzky-Golay** (window_size=5)" in md
    assert "`a.csv`" in md


def test_methods_markdown_empty_record():
    md = methods_markdown(new_pipeline_record())
    assert "Keine Verarbeitungsschritte" in md


def test_jcamp_export_roundtrip():
    xs = [4000.0, 3900.0, 3800.0]
    ys = [0.95, 0.90, 0.85]
    rec = new_pipeline_record("src.csv", ".csv", "csv_loader")
    add_operation(rec, "SNV", {}, "i_snv")
    text = export_jcamp_dx(xs, ys, title="roundtrip", x_unit="cm^-1",
                           pipeline=rec)
    assert "##TITLE= roundtrip" in text
    assert "##XUNITS= 1/CM" in text
    assert "##COMMENT=" in text and "pipeline_op_1=SNV" in text
    parsed = parse_jcamp_dx(text)
    df = parsed["data"]
    assert len(df) == 3
    assert abs(df["wavelength"].iloc[0] - 4000.0) < 1e-6
    assert abs(df["intensity"].iloc[2] - 0.85) < 1e-6


def test_jcamp_export_validation():
    for args in (([1.0], []), ([], [])):
        try:
            export_jcamp_dx(*args)
            raised = False
        except ValueError:
            raised = True
        assert raised


def test_agent_preprocess_writes_pipeline_record():
    import logging
    logging.disable(logging.WARNING)
    import tempfile
    import numpy as np
    import pandas as pd
    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    agent = EnhancedDataPreparationAgent(
        input_directory=tempfile.gettempdir(),
        output_directory=tempfile.gettempdir(),
        temp_directory=tempfile.gettempdir(),
        preprocessing_methods=["SNV", "Savitzky-Golay"],
    )
    data = {
        "data": pd.DataFrame({
            "wavelength": np.linspace(1000, 2000, 50),
            "intensity": np.random.RandomState(0).rand(50),
        }),
        "wavelength_column": "wavelength",
        "intensity_column": "intensity",
        "metadata": {"x_units": "nm"},
        "source_file": "t.csv",
        "format": ".csv",
    }
    result = agent._preprocess_data(data)
    assert result is not None
    pipeline = result.get("pipeline_record")
    assert pipeline is not None
    names = [op["operation"] for op in pipeline["operations"]]
    assert names == ["SNV", "Savitzky-Golay"]
    assert pipeline["unit"] == "nm"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print(f"All {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
