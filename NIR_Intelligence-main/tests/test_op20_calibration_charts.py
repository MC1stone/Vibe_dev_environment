# OP20: standard calibration plots for the calibration section.
#
# A chemometric calibration is judged by three standard plots: reference
# vs. cross-validated prediction (how good?), regression coefficients per
# wavelength (why does it work? the sought-after plot) and RMSECV over
# the number of PLS components (how complex?). The calibration agent
# computed cross-validated scores but nothing was plotted. OP20 renders
# these plots from the real calibration samples with scikit-learn PLS
# (no TensorFlow needed, CI-safe). Charts degrade gracefully: no
# calibration rows or a constant target -> empty dict, report intact.
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "django_project"))

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name} {detail}")


TRIAD = PROJECT / "data" / "raw" / "T4-T5_ALLE_mit_Brix_2.txt"
check("T1a triad sample present", TRIAD.exists(), str(TRIAD))

# ---------------------------------------------------------------------------
# T1: chart builder on the real triad calibration data (18 channels)
# ---------------------------------------------------------------------------
from services.project_ingest import _detect_wide_format, _ingest_wide_format

wide = _detect_wide_format(str(TRIAD))
check("T1b wide format detected", wide is not None)


class _FR:
    def __init__(self, path):
        import uuid
        self.id = uuid.uuid4()
        self.name = Path(path).name
        self.file_extension = Path(path).suffix
        self.file = None

    def read_bytes(self):
        with open(TRIAD, "rb") as fh:
            return fh.read()

    @property
    def path(self):
        return str(TRIAD)


dataset = _ingest_wide_format(_FR(TRIAD), str(TRIAD), wide)
cal = dataset.get("calibration_samples") or []
ref = dataset.get("reference_values") or []
wavelengths = dataset.get("preview", {}).get("wavelengths", [])
check("T1c calibration samples extracted (>=50 rows)", len(cal) >= 50, str(len(cal)))
check("T1d one reference per calibration row", len(ref) == len(cal) and len(ref) >= 50,
      f"{len(cal)}/{len(ref)}")
check("T1e 18-channel wavelength axis", len(wavelengths) == 18, str(len(wavelengths)))

from services.calibration_charts import (
    calibration_chart_data_urls, MATPLOTLIB_AVAILABLE, _as_matrix)

check("T1f matplotlib available in the environment", MATPLOTLIB_AVAILABLE)

expected_keys = ("ref_vs_pred", "reg_coefficients", "rmsecv_vs_n")

charts = calibration_chart_data_urls(cal, ref, wavelengths)
for key in expected_keys:
    check(f"T1g '{key}' rendered as base64 PNG",
          charts.get(key, "").startswith("data:image/png;base64,"),
          str(charts.get(key, ""))[:40])
check("T1h no extra non-chart keys", set(charts) <= set(expected_keys), str(set(charts)))
check("T1i charts strictly JSON serializable",
      json.loads(json.dumps(charts)) is not None)

# graceful degradation
empty = calibration_chart_data_urls([], [], wavelengths)
check("T1j no calibration rows -> empty charts dict (no crash)", empty == {}, str(empty))
short = calibration_chart_data_urls([[1.0, 2.0]] * 4, [1.0, 2.0, 3.0, 4.0], [700.0, 800.0])
check("T1k too few rows -> empty charts dict (no crash)", short == {}, str(short))
mismatch = calibration_chart_data_urls([[1.0, 2.0]] * 4, [1.0, 2.0], [700.0, 800.0])
check("T1l reference count mismatch tolerated (empty, no crash)", mismatch == {},
      str(mismatch))
constant = calibration_chart_data_urls(cal, [5.0] * len(cal), wavelengths)
check("T1m constant target cannot calibrate -> empty charts dict", constant == {},
      str(constant))
check("T1n matrix guard rejects ragged/short input",
      _as_matrix([[1.0, 2.0]] * 4) is None)

# real cross-validation: the ref_vs_pred plot is backed by KFold CV, not
# an in-sample fit - verify via the underlying helper
import numpy as np

from services.calibration_charts import _pls_ref_vs_pred

matrix = np.asarray(cal, dtype=float)
y = np.asarray(ref, dtype=float)
y_pred, n_components, folds = _pls_ref_vs_pred(matrix, y)
ss_res = float(np.sum((y - y_pred) ** 2))
rmsecv = float(np.sqrt(ss_res / y.size))
check("T1o cross-validated predictions are out-of-sample (RMSECV > 0)",
      y_pred.shape == y.shape and rmsecv > 0.0, f"rmsecv={rmsecv:.3f}")
check("T1p PLS component count within the sensible range",
      1 <= n_components <= 10, str(n_components))

# ---------------------------------------------------------------------------
# T2: crew section wiring (calibration section carries the charts)
# ---------------------------------------------------------------------------
crew_src = (PROJECT / "services" / "project_crew.py").read_text(encoding="utf-8")
check("T2a crew renders calibration charts for calibration samples",
      "calibration_chart_data_urls" in crew_src
      and "calibration_samples" in crew_src.split("calibration_chart_data_urls")[0])
check("T2b charts stored outside section.data (pprint stays small)",
      "cal_section['charts']" in crew_src and "charts_note" in crew_src)
check("T2c charts note mentions the calibration measurements",
      "Kalibrationsmessungen" in crew_src)

# live: build the calibration section with a stub result the way the crew does
import logging

logging.basicConfig(level=logging.CRITICAL)

import types

from services import project_crew


class _StubResult:
    spectral_analysis = None
    metadata_quality = None
    sensor_quality_results = None
    statistical_analysis_results = None
    neural_network_results = None
    calibration_results = {"best_method": "PLS", "status": "ok"}


class _StubDataset(dict):
    def __init__(self):
        super().__init__({
            "file_name": "triad.txt",
            "preview": {"wavelengths": wavelengths,
                        "intensities": [float(i) for i in range(18)]},
            "calibration_samples": cal,
            "reference_values": ref,
        })


section = None
try:
    built = project_crew._per_agent_reports(
        types.SimpleNamespace(),
        _StubResult(),
        types.SimpleNamespace(id="00000000-0000-0000-0000-000000000000",
                               user_id=None,
                               preparation_report={"datasets": []}),
        _StubDataset(),
    )
except Exception:
    built = None
if built:
    cal_sections = [s for s in built if s.get("agent") == "calibration"]
    section = cal_sections[0] if cal_sections else None
if section is not None:
    check("T2d calibration section carries three charts",
          all(section.get("charts", {}).get(k) for k in expected_keys),
          str(sorted((section.get("charts") or {}).keys())))
    check("T2e section charts stay JSON serializable",
          json.loads(json.dumps(section)) is not None)
else:
    check("T2d calibration section built", False, "section not built")

# ---------------------------------------------------------------------------
# T3: template and final report wiring (generic charts loop)
# ---------------------------------------------------------------------------
report_tpl = (PROJECT / "django_project" / "templates" / "project_report.html").read_text(encoding="utf-8")
check("T3a project report template renders section.charts",
      "section.charts" in report_tpl and "<img" in report_tpl)
report_src = (PROJECT / "services" / "project_report.py").read_text(encoding="utf-8")
check("T3b final report builder renders section charts",
      "charts" in report_src.split("def _agent_section_html")[1])

cal_src = (PROJECT / "services" / "calibration_charts.py").read_text(encoding="utf-8")
check("T3c predictions come from KFold cross-validation (not in-sample)",
      "cross_val_predict" in cal_src and "KFold" in cal_src)
check("T3d coefficients come from a real PLS fit",
      "PLSRegression" in cal_src.split("def _reg_coefficients")[0]
      and "pls.coef_" in cal_src)
check("T3e no placeholder/fake chart payloads",
      "placeholder" not in cal_src.lower() and "np.random.rand" not in cal_src
      and "np.linspace" not in cal_src)

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")
import django

django.setup()
from django.template.loader import get_template

get_template("project_report.html")
check("T3f project report template compiles", True)

# final report with a charts section renders the images
from services.project_report import generate_final_html_report

html_path = ""
try:
    html_path = generate_final_html_report(
        types.SimpleNamespace(id="00000000-0000-0000-0000-000000000000",
                              name="OP20 Calibration", user_id=None,
                              preparation_report={"datasets": [{
                                  "usable": True, "file_name": "triad.txt"}]}),
        {
            "request_id": "op20",
            "overall_quality_score": 80.0,
            "recommendations": [],
            "warnings": [],
            "errors": [],
            "processing_time": 0.1,
            "datasets_analyzed": 1,
            "per_agent_reports": [{
                "agent": "calibration",
                "title": "Kalibration (PLS, PCR)",
                "status": "completed",
                "data": {"best_method": "PLS"},
                "charts": dict(charts),
                "charts_note": "3 Kalibrierungs-Diagramme",
            }],
        },
        full_series=[{"file_name": "triad.txt",
                      "wavelengths": wavelengths,
                      "intensities": [float(i) for i in range(18)]}],
    )
except Exception as exc:  # pragma: no cover
    check("T3g final report generated", False, str(exc))
if html_path:
    content = Path(html_path).read_text(encoding="utf-8")
    check("T3g final report generated", html_path.endswith(".html"))
    check("T3h final report embeds the calibration charts",
          content.count("data:image/png;base64,") >= 3,
          str(content.count("data:image/png;base64,")))
    check("T3i charts note rendered", "Kalibrierungs-Diagramme" in content)
    check("T3j report has no raw markdown leftovers", "{%" not in content)

print(f"OP20 calibration charts matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
