# OP23: student-friendly report sections (Diskussion, Fazit, Literatur).
#
# The final report listed per-agent results but was not written for
# students. OP23 renders three sections from the REAL analysis results
# (no invented findings):
#   Diskussion - spectrum interpretation (band assignment from the
#     measured range), model quality (R2, RMSE from the agent results,
#     honest RMSEP note), error sources (agent findings + NIR effects)
#     and a detailed explanation of every figure (Abbildung 1..N in
#     report order)
#   Fazit - key findings summary + every optimization option collected
#     from the agents, each with a short explanation
#   Literaturhinweise - real, accessible standard works in APA style
# Fachbegriffe are explained in plain language at first use.
import re
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

# ---------------------------------------------------------------------------
# T1: spectrum interpretation from the real 18-channel axis
# ---------------------------------------------------------------------------
from services.student_report import interpret_spectra

sentences = interpret_spectra(wavelengths, intensities, analyte="Brix")
check("T1c interpretation mentions the real range 410-940",
      any("410" in s and "940" in s for s in sentences), str(sentences)[:120])
check("T1d VIS+NIR classification for a 410-940 range",
      any("sichtbaren" in s and "nahen infrarot" in s for s in sentences))
check("T1e band assignment names concrete wavelengths",
      any(re.search(r"um \d{3} nm", s) for s in sentences))
check("T1f O-H/C-H explanation present (why NIR works)",
      any("O-H" in s and "C-H" in s for s in sentences))
check("T1g analyte explanation for Brix present",
      any("Brix" in s for s in sentences))
empty_interp = interpret_spectra([], [])
check("T1h no wavelengths -> no invented interpretation", empty_interp == [])

# ---------------------------------------------------------------------------
# T2: model quality from real agent result shapes
# ---------------------------------------------------------------------------
from services.student_report import model_quality_paragraphs

per_agent = [
    {"agent": "calibration", "status": "completed",
     "data": {"best_r2_score": 0.82,
              "method_results": {"PLS": {"mean_r2": 0.82}}}},
    {"agent": "neural_network", "status": "completed",
     "data": {"model_results": {"CNN": {"r2_score": 0.595, "rmse": 0.627}}}},
]
quality = model_quality_paragraphs(per_agent)
joined = " ".join(quality)
check("T2a best model R2 reported", "R\u00b2 = 0.820" in joined, joined[:120])
check("T2b R2 explained in plain language", "Bestimmtheitsmass" in joined)
check("T2c CNN R2 reported for comparison", "0.595" in joined)
check("T2d RMSE reported with unit", "0.627" in joined and "\u00b0Brix" in joined)
check("T2e honest RMSEP note (no invented validation set)",
      "RMSEP" in joined and "liegt nicht vor" in joined)
check("T2f quality graded in words", any(g in joined for g in
      ("sehr gut", "gut", "brauchbar", "eingeschr\u00e4nkt", "unzureichend")))
no_quality = model_quality_paragraphs([])
check("T2g no results -> honest 'no assessment possible' sentence",
      any("nicht m\u00f6glich" in p for p in no_quality), str(no_quality)[:120])

# ---------------------------------------------------------------------------
# T3: error sources and figure explanations
# ---------------------------------------------------------------------------
from services.student_report import (
    build_student_sections, error_source_items, figure_explanations)

errors = error_source_items([
    {"agent": "spectral_analysis", "status": "completed",
     "data": {"issues_detected": ["saturated channels"]}},
    {"agent": "sensor_quality", "status": "completed",
     "data": {"drift_detected": True, "noise_detected": True,
              "noise_level": 0.07}},
])
joined_errors = " ".join(errors)
check("T3a spectral issues become error sources",
      any("saturated channels" in e for e in errors))
check("T3b sensor findings become error sources", "Drift" in joined_errors)
check("T3c general NIR error sources explained",
      "Streulicht" in joined_errors and "Probenverteilung" in joined_errors
      and "Temperatur" in joined_errors)

b64 = "data:image/png;base64," + "A" * 50
sections_with_charts = [
    {"agent": "spectral_analysis", "status": "completed", "data": {},
     "charts": {"spectrum": b64}},
    {"agent": "statistical_analysis", "status": "completed", "data": {},
     "charts": {"score_plot": b64, "scree_plot": b64}},
    {"agent": "calibration", "status": "completed",
     "data": {"best_r2_score": 0.82}, "charts": {"reg_coefficients": b64}},
]
figures = figure_explanations(sections_with_charts, overview_keys=["spectrum", "quality_bar"])
numbers = [n for n, _ in figures]
check("T3d figures numbered 1..N without gaps",
      numbers == list(range(1, len(numbers) + 1)), str(numbers))
check("T3e every figure has a substantial explanation",
      all(len(text) > 60 for _, text in figures))
check("T3f explanations reference the chart content",
      any("Wellenl\u00e4nge" in t for _, t in figures)
      and any("Hauptkomponenten" in t for _, t in figures))
check("T3g quality_bar overview explained",
      any("Balkendiagramm" in t for _, t in figures))

# ---------------------------------------------------------------------------
# T4: full section build + final report integration
# ---------------------------------------------------------------------------
crew_results = {"overall_quality_score": 79.0, "recommendations":
                ["Referenzmessung wiederholen."]}
student = build_student_sections(
    sections_with_charts, crew_results,
    [{"preview": {"wavelengths": wavelengths, "intensities": intensities}}],
    overview_keys=["spectrum", "quality_bar"])
check("T4a three sections rendered",
      all(student.get(k) for k in ("discussion", "conclusion", "literature")))
check("T4b discussion carries the four required parts",
      all(h in student["discussion"] for h in
          ("Interpretation der Spektren", "Bewertung der Modellg\u00fcte",
           "M\u00f6gliche Fehlerquellen", "Erkl\u00e4rung der Grafiken")))
check("T4c conclusion summarizes and lists options",
      "Zusammenfassung der wichtigsten Erkenntnisse" in student["conclusion"]
      and "Optimierungsoptionen" in student["conclusion"])
check("T4d options include agent recommendations",
      "Referenzmessung wiederholen." in student["conclusion"])
check("T4e literature is APA-styled with real sources",
      "Pasquini" in student["literature"]
      and "https://doi.org" in student["literature"]
      and re.search(r"\(\d{4}\)", student["literature"]))
check("T4f literature carries short annotations",
      student["literature"].count("muted") >= 7)

minimal = build_student_sections([], {"recommendations": []}, [])
check("T4g minimal input still renders all sections",
      all(minimal.get(k) for k in ("discussion", "conclusion", "literature")))
check("T4h minimal discussion states missing data honestly",
      "Keine Spektraldaten" in minimal["discussion"])

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")
import django

django.setup()

import types

from services.project_report import generate_final_html_report

html_path = ""
try:
    html_path = generate_final_html_report(
        types.SimpleNamespace(id="00000000-0000-0000-0000-000000000000",
                              name="OP23 Student", user_id=None,
                              preparation_report={"datasets": [{
                                  "usable": True, "file_name": "triad.txt",
                                  "preview": {"wavelengths": wavelengths,
                                              "intensities": intensities}}]}),
        {"request_id": "op23", "overall_quality_score": 79.0,
         "recommendations": [], "warnings": [], "errors": [],
         "processing_time": 0.2, "datasets_analyzed": 1,
         "per_agent_reports": sections_with_charts},
        full_series=[{"file_name": "triad.txt", "wavelengths": wavelengths,
                      "intensities": intensities}])
except Exception as exc:  # pragma: no cover
    check("T4i final report generated", False, str(exc))
if html_path:
    content = Path(html_path).read_text(encoding="utf-8")
    check("T4i final report generated", html_path.endswith(".html"))
    check("T4j report contains Diskussion, Fazit, Literaturhinweise",
          all(f"<h2>{h}</h2>" in content for h in
              ("Diskussion", "Fazit", "Literaturhinweise")))
    figs = sorted(set(int(n) for n in re.findall(r"Abbildung (\d+):", content)))
    imgs = content.count("<img")
    check("T4k every figure in the report is explained",
          imgs == len(figs) and figs == list(range(1, imgs + 1)),
          f"imgs={imgs} figs={figs}")
    check("T4l report has no raw markdown leftovers", "{%" not in content)

# regression guard: the project report template must stay untouched
report_src = (PROJECT / "services" / "project_report.py").read_text(encoding="utf-8")
check("T4m report builder wires the student sections",
      "build_student_sections" in report_src
      and "Diskussion" in report_src and "Literaturhinweise" in report_src)

print(f"OP23 student report matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
