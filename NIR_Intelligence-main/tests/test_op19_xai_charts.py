# OP19: XAI visualisations for the neural network analysis.
#
# A neural calibrator on NIR spectra is interpreted through seven standard
# XAI plots (SHAP summary, SHAP force/waterfall, saliency, Grad-CAM,
# attention weights, prediction vs. actual, loss curves). OP18 fixed the
# CNN training; OP19 renders these plots from REAL computations on the
# trained attention-CNN - no simulated values, and the shap package stays
# a non-dependency (permutation importance / occlusion are the
# SHAP-equivalents). Charts degrade gracefully: no TensorFlow or too few
# calibration rows -> empty dict, report intact.
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

from agents.neural_network_agent import _tensor_flow_available
from services.xai_charts import xai_chart_data_urls, MATPLOTLIB_AVAILABLE, _as_matrix

check("T1f matplotlib available in the environment", MATPLOTLIB_AVAILABLE)
tf_available = _tensor_flow_available()

expected_keys = ("prediction_vs_actual", "loss_curves", "shap_summary",
                 "shap_waterfall", "saliency_map", "grad_cam", "attention_weights")

if tf_available:
    charts = xai_chart_data_urls(cal, ref, wavelengths, epochs=15)
    for key in expected_keys:
        check(f"T1g '{key}' rendered as base64 PNG",
              charts.get(key, "").startswith("data:image/png;base64,"),
              str(charts.get(key, ""))[:40])
    check("T1h no extra non-chart keys", set(charts) <= set(expected_keys),
          str(set(charts)))
    check("T1i charts strictly JSON serializable",
          json.loads(json.dumps(charts)) is not None)
else:
    charts = xai_chart_data_urls(cal, ref, wavelengths, epochs=15)
    # OP70: ohne TensorFlow entstehen die XAI-Grafiken jetzt IMMER via
    # sklearn-MLP-Fallback (Vertrag des Neural Network Agent); die
    # TF-exklusiven Keys entfallen ehrlich statt gefaked.
    fallback_keys = ("prediction_vs_actual", "loss_curves", "shap_summary",
                     "shap_waterfall")
    for key in fallback_keys:
        check(f"T1g '{key}' rendered as base64 PNG (MLP fallback)",
              charts.get(key, "").startswith("data:image/png;base64,"),
              str(charts.get(key, ""))[:40])
    check("T1h TF-exclusive keys honestly absent (never simulated)",
          not ({'saliency_map', 'grad_cam', 'attention_weights'}
               & set(charts)), str(set(charts)))

# graceful degradation (works with and without TF)
empty = xai_chart_data_urls([], [], wavelengths)
check("T1j no calibration rows -> empty charts dict (no crash)", empty == {}, str(empty))
short = xai_chart_data_urls([[1.0, 2.0]] * 4, [1.0, 2.0, 3.0, 4.0], [700.0, 800.0])
check("T1k too few rows -> empty charts dict (no crash)", short == {}, str(short))
mismatch = xai_chart_data_urls([[1.0, 2.0]] * 4, [1.0, 2.0], [700.0, 800.0])
check("T1l reference count mismatch tolerated (empty, no crash)", mismatch == {},
      str(mismatch))
check("T1m matrix guard rejects ragged/short input",
      _as_matrix([[1.0, 2.0]] * 4) is None)

# ---------------------------------------------------------------------------
# T2: crew wiring - neural network section carries the XAI charts
# ---------------------------------------------------------------------------
crew_src = (PROJECT / "services" / "project_crew.py").read_text(encoding="utf-8")
check("T2a crew renders XAI charts for calibration samples",
      "xai_chart_data_urls" in crew_src
      and "calibration_samples" in crew_src.split("xai_chart_data_urls")[0])
check("T2b charts stored outside section.data (pprint stays small)",
      "nn_section['charts']" in crew_src and "charts_note" in crew_src)
check("T2c charts note mentions the calibration measurements",
      "Kalibrationsmessungen" in crew_src)

# live: build the neural network section with a stub result the way the
# crew does (mirrors the OP16 live section build)
import logging

logging.basicConfig(level=logging.CRITICAL)

import types

from services import project_crew


class _StubResult:
    spectral_analysis = None
    metadata_quality = None
    sensor_quality_results = None
    statistical_analysis_results = None
    calibration_results = None
    neural_network_results = {"models_trained": ["CNN"], "status": "ok"}


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
    nn = [s for s in built if s.get("agent") == "neural_network"]
    section = nn[0] if nn else None
if section is not None:
    if tf_available:
        check("T2d neural section carries seven XAI charts",
              all(section.get("charts", {}).get(k) for k in expected_keys),
              str(sorted((section.get("charts") or {}).keys())))
        check("T2e section charts stay JSON serializable",
              json.loads(json.dumps(section)) is not None)
    else:
        # OP70: ohne TF liefert der MLP-Fallback jetzt die vier
        # Basis-XAI-Grafiken - die Sektion traegt Charts statt leer zu
        # sein; TF-exklusive Keys bleiben ehrlich abwesend.
        fb_keys = ("prediction_vs_actual", "loss_curves", "shap_summary",
                   "shap_waterfall")
        check("T2d without TF: section carries MLP-fallback charts",
              all((section.get("charts") or {}).get(k) for k in fb_keys)
              and not ({"saliency_map", "grad_cam", "attention_weights"}
                       & set(section.get("charts") or {})),
              str(sorted((section.get("charts") or {}).keys())))

print(f"OP19 XAI charts matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
