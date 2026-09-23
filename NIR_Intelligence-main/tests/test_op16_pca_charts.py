# OP16: standard PCA visualisations for the statistical analysis section.
#
# A PCA in spectroscopy is judged by six standard plots (score, loading,
# biplot, scree, R2 per wavelength, SPE). The statistical agent computed
# the numbers, but nothing was plotted. OP16 renders these plots from the
# measurement replicas of a dataset (matplotlib Agg, base64 PNG) and shows
# them in the project report and the final OP11 report. Charts degrade
# gracefully: no replicas or no matplotlib -> no charts, report intact.
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

# ---------------------------------------------------------------------------
# T1: chart builder on real triad replicas (18 channels, 410-940 nm)
# ---------------------------------------------------------------------------
from services.project_ingest import _detect_wide_format, _ingest_wide_format

check("T1a triad sample present", TRIAD.exists(), str(TRIAD))
wide = _detect_wide_format(str(TRIAD))
check("T1b wide format detected", wide is not None)
if not wide:
    raise SystemExit(1)


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
samples = dataset.get("measurement_samples") or []
wavelengths = dataset.get("preview", {}).get("wavelengths", [])
check("T1c replicas extracted (>=3 rows)", len(samples) >= 3, str(len(samples)))
check("T1d 18-channel wavelength axis", len(wavelengths) == 18, str(len(wavelengths)))

from services.pca_charts import pca_chart_data_urls, MATPLOTLIB_AVAILABLE

check("T1e matplotlib available in the environment", MATPLOTLIB_AVAILABLE)
charts = pca_chart_data_urls(samples, wavelengths)
expected_keys = ("score_plot", "loading_plot", "biplot",
                 "scree_plot", "r2_per_wavelength", "spe_plot")
for key in expected_keys:
    check(f"T1f '{key}' rendered as base64 PNG",
          charts.get(key, "").startswith("data:image/png;base64,"),
          str(charts.get(key, ""))[:40])
check("T1g no extra non-chart keys", set(charts) <= set(expected_keys), str(set(charts)))

empty = pca_chart_data_urls([], wavelengths)
check("T1h no replicas -> empty charts dict (no crash)", empty == {}, str(empty))
short = pca_chart_data_urls([[1.0, 2.0], [3.0, 4.0]], [100.0, 200.0])
check("T1i too few samples -> empty charts dict (no crash)", short == {}, str(short))
mismatch = pca_chart_data_urls([[1.0, 2.0, 3.0]] * 4, [700.0])
check("T1j wavelength count mismatch tolerated", isinstance(mismatch, dict))

# charts dict is JSON serialisable (crew_results contract)
check("T1k charts strictly JSON serializable",
      json.loads(json.dumps(charts)) is not None)

# ---------------------------------------------------------------------------
# T2: crew section wiring (statistical section carries the charts)
# ---------------------------------------------------------------------------
crew_src = (PROJECT / "services" / "project_crew.py").read_text(encoding="utf-8")
check("T2a crew renders PCA charts for replicas",
      "pca_chart_data_urls" in crew_src
      and "measurement_samples" in crew_src.split("pca_chart_data_urls")[0].split("statistical_analysis_results")[-1]
      if "statistical_analysis_results" in crew_src else False)
check("T2b charts stored outside section.data (pprint stays small)",
      "section['charts']" in crew_src and "charts_note" in crew_src)

# live: build the statistical section with a stub result the way the crew does
import logging

logging.basicConfig(level=logging.CRITICAL)


class _StubResult:
    spectral_analysis = None
    metadata_quality = None
    sensor_quality_results = None
    neural_network_results = None
    calibration_results = None
    statistical_analysis_results = {"methods_applied": ["PCA"], "method_results": {"PCA": {"n_components": 3}}}


class _StubDataset(dict):
    def __init__(self):
        super().__init__({
            "file_name": "triad.txt",
            "preview": {"wavelengths": wavelengths, "intensities": [float(i) for i in range(18)]},
            "measurement_samples": samples,
        })


import types

from services import project_crew

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
    # _per_agent_reports may need a fuller result object; fall back to
    # constructing the statistical section body directly
    built = None
if built:
    stats = [s for s in built if s.get("agent") == "statistical_analysis"]
    section = stats[0] if stats else None
if section is not None:
    check("T2c statistical section carries six charts",
          all(section.get("charts", {}).get(k) for k in expected_keys),
          str(sorted((section.get("charts") or {}).keys())))
    check("T2d section stays JSON serializable",
          json.loads(json.dumps(section)) is not None)
else:
    check("T2c statistical section carries six charts", False, "section not built")

# ---------------------------------------------------------------------------
# T3: template and report wiring
# ---------------------------------------------------------------------------
report_tpl = (PROJECT / "django_project" / "templates" / "project_report.html").read_text(encoding="utf-8")
check("T3a project report template renders section.charts",
      "section.charts" in report_tpl and "<img" in report_tpl)
report_src = (PROJECT / "services" / "project_report.py").read_text(encoding="utf-8")
check("T3b final report builder renders section charts",
      "charts" in report_src.split("def _agent_section_html")[1])

# template compiles
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")
import django

django.setup()
from django.template.loader import get_template

get_template("project_report.html")
check("T3c project report template compiles", True)

# final report with a charts section renders the images
from services.project_report import generate_final_html_report  # noqa: E402

html_path = ""
try:
    html_path = generate_final_html_report(
        types.SimpleNamespace(id="00000000-0000-0000-0000-000000000000",
                              name="OP16 Charts", user_id=None,
                              preparation_report={"datasets": [{
                                  "usable": True, "file_name": "triad.txt"}]}),
        {
            "request_id": "op16",
            "overall_quality_score": 80.0,
            "recommendations": [],
            "warnings": [],
            "errors": [],
            "processing_time": 0.1,
            "datasets_analyzed": 1,
            "per_agent_reports": [{
                "agent": "statistical_analysis",
                "title": "Statistische Analyse (PCA, PLS, Cluster)",
                "status": "completed",
                "data": {"methods_applied": ["PCA"]},
                "charts": {k: charts[k] for k in expected_keys if charts.get(k)},
                "charts_note": "6 PCA-Diagramme aus Messreplikaten",
            }],
        },
        full_series=[{"file_name": "triad.txt",
                      "wavelengths": wavelengths,
                      "intensities": [float(i) for i in range(18)]}],
    )
except Exception as exc:  # pragma: no cover
    check("T3d final report generated", False, str(exc))
if html_path:
    content = Path(html_path).read_text(encoding="utf-8")
    check("T3d final report generated", html_path.endswith(".html"))
    check("T3e final report embeds the PCA charts",
          content.count("data:image/png;base64,") >= 6,
          str(content.count("data:image/png;base64,")))
    check("T3f charts note rendered", "PCA-Diagramme" in content)
    check("T3g report has no raw markdown leftovers", "{%" not in content)

print(f"OP16 PCA charts matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
