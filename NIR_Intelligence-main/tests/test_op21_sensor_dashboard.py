# OP21: sensor quality SPC dashboard and optimization recommendations.
#
# The old NIR platform showed the sensor quality as a nicely presented
# panel with optimization recommendations. The new agent computes drift,
# offset, noise and a quality score from the real replicas, but nothing
# was plotted and no recommendations were shown. OP21 renders a 4-panel
# SPC-style dashboard (Shewhart control chart, spectral overlay,
# per-channel noise box plot, quality gauge with sub-scores) from the
# real measurement replicas and derives concrete German optimization
# recommendations from the agent results. Everything degrades
# gracefully: no replicas or no sensor results -> no charts, report
# intact.
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
# T1: dashboard builder on the real triad replicas (18 channels)
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
replicas = dataset.get("measurement_samples") or []
wavelengths = dataset.get("preview", {}).get("wavelengths", [])
check("T1c measurement replicas extracted (>=3 rows)", len(replicas) >= 3,
      str(len(replicas)))
check("T1d 18-channel wavelength axis", len(wavelengths) == 18, str(len(wavelengths)))

from agents.sensor_quality_agent import SensorQualityAgent
from services.sensor_charts import (
    MATPLOTLIB_AVAILABLE, _as_matrix, sensor_dashboard_data_urls,
    sensor_recommendations)

check("T1e matplotlib available in the environment", MATPLOTLIB_AVAILABLE)

agent = SensorQualityAgent()
sensor_results = agent.execute({"spectra": replicas, "sample_id": "triad"}).data
check("T1f sensor agent completes on the replicas",
      sensor_results.get("status") in ("ok", "degraded"), str(sensor_results)[:80])
check("T1g sensor results carry the quality score",
      isinstance(sensor_results.get("overall_quality_score"), float),
      str(sensor_results.get("overall_quality_score")))

charts = sensor_dashboard_data_urls(replicas, sensor_results, wavelengths)
check("T1h dashboard rendered as base64 PNG",
      charts.get("sensor_dashboard", "").startswith("data:image/png;base64,"),
      str(charts.get("sensor_dashboard", ""))[:40])
check("T1i only the dashboard key (no metadata keys)", set(charts) <= {"sensor_dashboard"},
      str(set(charts)))
check("T1j charts strictly JSON serializable",
      json.loads(json.dumps(charts)) is not None)

# graceful degradation
empty = sensor_dashboard_data_urls([], sensor_results, wavelengths)
check("T1k no replicas -> empty charts dict (no crash)", empty == {}, str(empty))
single = sensor_dashboard_data_urls(replicas[:1], sensor_results, wavelengths)
check("T1l single replica -> empty charts dict (control chart needs >=2)", single == {},
      str(single))
no_results = sensor_dashboard_data_urls(replicas, {}, wavelengths)
check("T1m no sensor results -> empty charts dict (no crash)", no_results == {},
      str(no_results))
mismatch = sensor_dashboard_data_urls(replicas, sensor_results, [700.0, 800.0])
check("T1n wavelength count mismatch tolerated", isinstance(mismatch, dict))
check("T1o matrix guard rejects ragged/short input",
      _as_matrix([[1.0, 2.0]]) is None)

# ---------------------------------------------------------------------------
# T2: optimization recommendations derived from the real results
# ---------------------------------------------------------------------------
recommendations = sensor_recommendations(sensor_results)
check("T2a recommendations present (>=1)", len(recommendations) >= 1,
      str(recommendations))
check("T2b recommendations are actionable German sentences",
      all(len(r) > 20 and r.endswith(".") for r in recommendations), str(recommendations))
drift_rec = sensor_recommendations({"drift_detected": True})
check("T2c drift finding yields a drift recommendation",
      any("Drift" in r for r in drift_rec), str(drift_rec))
noise_rec = sensor_recommendations({"noise_detected": True})
check("T2d noise finding yields a noise recommendation",
      any("Rauschen" in r for r in noise_rec), str(noise_rec))
offset_rec = sensor_recommendations({"offset_detected": True})
check("T2e offset finding yields an offset recommendation",
      any("Offset" in r or "Baseline" in r for r in offset_rec), str(offset_rec))
good_rec = sensor_recommendations({"overall_quality_score": 0.95,
                                   "drift_detected": False,
                                   "offset_detected": False,
                                   "noise_detected": False,
                                   "reference_valid": True})
check("T2f good sensor keeps a positive maintenance note",
      any("keine Ma\u00dfnahmen" in r for r in good_rec), str(good_rec))

# ---------------------------------------------------------------------------
# T3: crew section wiring (sensor section carries charts + recommendations)
# ---------------------------------------------------------------------------
crew_src = (PROJECT / "services" / "project_crew.py").read_text(encoding="utf-8")
check("T3a crew renders the sensor dashboard for replicas",
      "sensor_dashboard_data_urls" in crew_src
      and "measurement_samples" in crew_src.split("sensor_dashboard_data_urls")[0])
check("T3b charts stored outside section.data (pprint stays small)",
      "sensor_section['charts']" in crew_src and "charts_note" in crew_src)
check("T3c recommendations injected into the sensor section data",
      "optimization_recommendations" in crew_src
      and "sensor_recommendations" in crew_src)

# live: build the sensor section with a stub result the way the crew does
import logging

logging.basicConfig(level=logging.CRITICAL)

import types

from services import project_crew


class _StubResult:
    spectral_analysis = None
    metadata_quality = None
    statistical_analysis_results = None
    neural_network_results = None
    calibration_results = None
    sensor_quality_results = dict(sensor_results)


class _StubDataset(dict):
    def __init__(self):
        super().__init__({
            "file_name": "triad.txt",
            "preview": {"wavelengths": wavelengths,
                        "intensities": [float(i) for i in range(18)]},
            "measurement_samples": replicas,
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
    sensor = [s for s in built if s.get("agent") == "sensor_quality"]
    section = sensor[0] if sensor else None
if section is not None:
    check("T3d sensor section carries the dashboard chart",
          (section.get("charts") or {}).get("sensor_dashboard"),
          str(sorted((section.get("charts") or {}).keys())))
    check("T3e recommendations stored inside section.data",
          isinstance((section.get("data") or {}).get("optimization_recommendations"),
                     list)
          and len(section["data"]["optimization_recommendations"]) >= 1,
          str((section.get("data") or {}).get("optimization_recommendations"))[:80])
    check("T3f section stays JSON serializable",
          json.loads(json.dumps(section)) is not None)
else:
    check("T3d sensor section built", False, "section not built")

# ---------------------------------------------------------------------------
# T4: template and final report wiring (generic charts loop)
# ---------------------------------------------------------------------------
report_tpl = (PROJECT / "django_project" / "templates" / "project_report.html").read_text(encoding="utf-8")
check("T4a project report template renders section.charts",
      "section.charts" in report_tpl and "<img" in report_tpl)
report_src = (PROJECT / "services" / "project_report.py").read_text(encoding="utf-8")
check("T4b final report builder renders section charts",
      "charts" in report_src.split("def _agent_section_html")[1])

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")
import django

django.setup()
from django.template.loader import get_template

get_template("project_report.html")
check("T4c project report template compiles", True)

# final report with a charts section renders the image
from services.project_report import generate_final_html_report

html_path = ""
try:
    html_path = generate_final_html_report(
        types.SimpleNamespace(id="00000000-0000-0000-0000-000000000000",
                              name="OP21 Sensor", user_id=None,
                              preparation_report={"datasets": [{
                                  "usable": True, "file_name": "triad.txt"}]}),
        {
            "request_id": "op21",
            "overall_quality_score": 80.0,
            "recommendations": [],
            "warnings": [],
            "errors": [],
            "processing_time": 0.1,
            "datasets_analyzed": 1,
            "per_agent_reports": [{
                "agent": "sensor_quality",
                "title": "Sensorqualität (Drift, Rauschen)",
                "status": "completed",
                "data": {"overall_quality_score": 0.7,
                         "optimization_recommendations": recommendations},
                "charts": dict(charts),
                "charts_note": "SPC-Dashboard",
            }],
        },
        full_series=[{"file_name": "triad.txt",
                      "wavelengths": wavelengths,
                      "intensities": [float(i) for i in range(18)]}],
    )
except Exception as exc:  # pragma: no cover
    check("T4d final report generated", False, str(exc))
if html_path:
    content = Path(html_path).read_text(encoding="utf-8")
    check("T4d final report generated", html_path.endswith(".html"))
    check("T4e final report embeds the dashboard",
          content.count("data:image/png;base64,") >= 1,
          str(content.count("data:image/png;base64,")))
    check("T4f recommendations rendered in the report",
          "Rauschen" in content or "Drift" in content
          or "keine Ma\u00dfnahmen" in content)
    check("T4g report has no raw markdown leftovers", "{%" not in content)

print(f"OP21 sensor dashboard matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
