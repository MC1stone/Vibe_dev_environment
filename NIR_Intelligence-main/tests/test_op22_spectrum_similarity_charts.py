# OP22: spectrum chart in the spectral analysis section and a top-3
# similarity comparison chart in the database comparison section.
#
# The uploaded spectral data was only ever shown as numbers - the
# spectral analysis section had no plot of the measured spectrum, and
# the FAISS similarity search reported scores without visualising the
# matches. OP22 renders:
#   - the uploaded spectrum as a single line (same style as the database
#     detail page) in the spectral analysis section
#   - the measurement overlaid with the three most similar spectra
#     (from the spectral database and sibling project files) in the
#     comparison section
# Everything degrades gracefully: no preview data or no matches ->
# missing chart, report intact.
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
# T1: chart builders on the real triad preview (18 channels)
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
wavelengths = dataset.get("preview", {}).get("wavelengths", [])
intensities = dataset.get("preview", {}).get("intensities", [])
check("T1c preview extracted (18 channels)", len(wavelengths) == 18,
      str(len(wavelengths)))

from services.similarity_charts import (
    MATPLOTLIB_AVAILABLE, similarity_charts_data_urls,
    similarity_top3_chart_data_url, spectrum_chart_data_url)

check("T1d matplotlib available in the environment", MATPLOTLIB_AVAILABLE)

spectrum_url = spectrum_chart_data_url(wavelengths, intensities,
                                       title="Hochgeladenes Spektrum")
check("T1e spectrum chart rendered as base64 PNG",
      spectrum_url.startswith("data:image/png;base64,"), spectrum_url[:40])

import numpy as np

rng = np.random.default_rng(1)
reference_curves = {}
for name, scale in (("db_a.txt", 1.0), ("db_b.txt", 0.9),
                    ("db_c.txt", 1.1), ("db_d.txt", 2.0)):
    reference_curves[name] = (
        wavelengths, [v * scale + rng.normal(0, 2) for v in intensities])
matches = [
    {"reference_id": "db_a.txt", "similarity": 0.98},
    {"reference_id": "db_b.txt", "similarity": 0.95},
    {"reference_id": "db_c.txt", "similarity": 0.90},
    {"reference_id": "db_d.txt", "similarity": 0.40},
]
top3_url = similarity_top3_chart_data_url(wavelengths, intensities,
                                          matches, reference_curves)
check("T1f top-3 similarity chart rendered as base64 PNG",
      top3_url.startswith("data:image/png;base64,"), top3_url[:40])

charts = similarity_charts_data_urls(wavelengths, intensities, matches,
                                      reference_curves)
check("T1g wrapper carries both chart keys",
      set(charts) == {"spectrum", "similarity_top3"}, str(set(charts)))
check("T1h charts strictly JSON serializable",
      json.loads(json.dumps(charts)) is not None)

# graceful degradation
check("T1i no matplotlib guard: empty intensities -> '' spectrum chart",
      spectrum_chart_data_url(wavelengths, [], title="x") == "")
check("T1j length mismatch -> '' spectrum chart",
      spectrum_chart_data_url(wavelengths, intensities[:-1]) == "")
no_match = similarity_top3_chart_data_url(wavelengths, intensities, [], {})
check("T1k no matches -> '' similarity chart (never a fake overlay)",
      no_match == "")
unknown = similarity_top3_chart_data_url(
    wavelengths, intensities,
    [{"reference_id": "missing.txt", "similarity": 0.9}], reference_curves)
check("T1l matches without a reference curve are ignored",
      unknown == "")
bad_curve = dict(reference_curves)
bad_curve["db_a.txt"] = (wavelengths, intensities[:-1])
partial = similarity_top3_chart_data_url(
    wavelengths, intensities, matches[:1], bad_curve)
check("T1m ragged reference curve skipped, chart still renders",
      partial.startswith("data:image/png;base64,"), partial[:40])

# ---------------------------------------------------------------------------
# T2: crew section wiring
# ---------------------------------------------------------------------------
crew_src = (PROJECT / "services" / "project_crew.py").read_text(encoding="utf-8")
check("T2a spectral section renders the uploaded spectrum chart",
      "spectrum_chart_data_url" in crew_src
      and "Hochgeladenes Spektrum" in crew_src)
check("T2b similarity section renders the top-3 comparison chart",
      "similarity_top3_chart_data_url" in crew_src
      and "similarity_top3" in crew_src)
check("T2c charts stored outside section.data (pprint stays small)",
      "'charts'" in crew_src and "charts_note" in crew_src)

# live: build the spectral section with a stub result the way the crew does
import logging

logging.basicConfig(level=logging.CRITICAL)

import types

from services import project_crew


class _SpectralResult:
    quality_score = 88.0

    class _Grade:
        value = "good"

    quality_grade = _Grade()
    wavelength_range = (410.0, 940.0)
    data_points = 18
    issues_detected = []
    recommendations = ["Messung wiederholen"]


class _StubResult:
    spectral_analysis = _SpectralResult()
    metadata_quality = None
    sensor_quality_results = None
    statistical_analysis_results = None
    neural_network_results = None
    calibration_results = None


class _StubDataset(dict):
    def __init__(self):
        super().__init__({
            "file_name": "triad.txt",
            "file_id": "f1",
            "preview": {"wavelengths": wavelengths,
                        "intensities": intensities},
        })


spectral_section = None
try:
    built = project_crew._per_agent_reports(
        types.SimpleNamespace(),
        _StubResult(),
        types.SimpleNamespace(id="00000000-0000-0000-0000-000000000000",
                               user_id=None,
                               preparation_report={"datasets": []}),
        _StubDataset(),
    )
    spectral_section = next(
        (s for s in built if s.get("agent") == "spectral_analysis"), None)
except Exception:
    spectral_section = None
if spectral_section is not None:
    check("T2d spectral section carries the spectrum chart",
          (spectral_section.get("charts") or {}).get("spectrum"),
          str(sorted((spectral_section.get("charts") or {}).keys())))
    check("T2e spectral section stays JSON serializable",
          json.loads(json.dumps(spectral_section)) is not None)
else:
    check("T2d spectral section built", False, "section not built")

# live: the similarity section compares sibling datasets and renders top 3
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")
import django

django.setup()


class _StubProject:
    id = "00000000-0000-0000-0000-000000000001"
    user_id = None

    def __init__(self):
        self.preparation_report = {
            "datasets": [
                {"usable": True, "file_id": "f1", "file_name": "triad.txt",
                 "preview": {"wavelengths": wavelengths,
                              "intensities": intensities}},
                {"usable": True, "file_id": "f2", "file_name": "probe_b.txt",
                 "preview": {"wavelengths": wavelengths,
                              "intensities": [v * 1.02 for v in intensities]}},
                {"usable": True, "file_id": "f3", "file_name": "probe_c.txt",
                 "preview": {"wavelengths": wavelengths,
                              "intensities": [v * 0.5 + 300 for v in intensities]}},
            ]
        }


sim_section = None
try:
    sim_section = project_crew._similarity_section(_StubProject(), _StubDataset())
except Exception as exc:
    check("T2f similarity section built", False, str(exc))
if sim_section is not None:
    data = sim_section.get("data") or {}
    found_matches = data.get("matches") or []
    check("T2f similarity section built with FAISS matches",
          len(found_matches) >= 1, str(data)[:100])
    check("T2g similarity section carries the top-3 chart",
          (sim_section.get("charts") or {}).get("similarity_top3"),
          str(sorted((sim_section.get("charts") or {}).keys())))
    check("T2h similarity section stays JSON serializable",
          json.loads(json.dumps(sim_section)) is not None)

# ---------------------------------------------------------------------------
# T3: template and final report wiring (generic charts loop)
# ---------------------------------------------------------------------------
report_tpl = (PROJECT / "django_project" / "templates" / "project_report.html").read_text(encoding="utf-8")
check("T3a project report template renders section.charts",
      "section.charts" in report_tpl and "<img" in report_tpl)
report_src = (PROJECT / "services" / "project_report.py").read_text(encoding="utf-8")
check("T3b final report builder renders section charts",
      "charts" in report_src.split("def _agent_section_html")[1])

from django.template.loader import get_template

get_template("project_report.html")
check("T3c project report template compiles", True)

from services.project_report import generate_final_html_report

html_path = ""
try:
    html_path = generate_final_html_report(
        types.SimpleNamespace(id="00000000-0000-0000-0000-000000000000",
                              name="OP22 Similarity", user_id=None,
                              preparation_report={"datasets": [{
                                  "usable": True, "file_name": "triad.txt"}]}),
        {
            "request_id": "op22",
            "overall_quality_score": 80.0,
            "recommendations": [],
            "warnings": [],
            "errors": [],
            "processing_time": 0.1,
            "datasets_analyzed": 1,
            "per_agent_reports": [
                {"agent": "spectral_analysis",
                 "title": "Spektralanalyse (Qualität)",
                 "status": "completed",
                 "data": {"quality_score": 88.0},
                 "charts": {"spectrum": spectrum_url},
                 "charts_note": "Spektrum der hochgeladenen Messdaten"},
                {"agent": "faiss_similarity",
                 "title": "Spektren-Datenbankvergleich (FAISS)",
                 "status": "completed",
                 "data": {"matches": matches},
                 "charts": {"similarity_top3": top3_url},
                 "charts_note": "Top-3-Vergleich"},
            ],
        },
        full_series=[{"file_name": "triad.txt",
                      "wavelengths": wavelengths,
                      "intensities": intensities}],
    )
except Exception as exc:  # pragma: no cover
    check("T3d final report generated", False, str(exc))
if html_path:
    content = Path(html_path).read_text(encoding="utf-8")
    check("T3d final report generated", html_path.endswith(".html"))
    check("T3e final report embeds both charts",
          content.count("data:image/png;base64,") >= 2,
          str(content.count("data:image/png;base64,")))
    check("T3f report has no raw markdown leftovers", "{%" not in content)

print(f"OP22 spectrum + similarity charts matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
