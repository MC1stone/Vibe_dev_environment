# OP24: embedded report chatbot for questions about the analysis.
#
# The final report is a self-contained, offline HTML file - a live
# CrewAI chat would break that concept (server dependency, no offline
# use). The hybrid design: a release-time ChatbotAgent (CrewAI agent)
# turns the REAL crew results into a structured Q&A knowledge base
# (categories, questions, answers with the real numbers, keyword
# matching sets, figure references), and an embedded vanilla-JS widget
# matches student questions client-side. Consistent with OP14: the agent
# only answers what the results contain - nothing is invented. The
# widget works fully offline, degrades to '' without a knowledge base.
import json
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
ref = dataset.get("reference_values") or []

# ---------------------------------------------------------------------------
# T1: ChatbotAgent builds a truthful knowledge base from real results
# ---------------------------------------------------------------------------
from agents.chatbot_agent import ChatbotAgent

b64 = "data:image/png;base64," + "A" * 50
per_agent = [
    {"agent": "spectral_analysis", "status": "completed",
     "data": {"quality_score": 88.0, "quality_grade": "good"},
     "charts": {"spectrum": b64}},
    {"agent": "sensor_quality", "status": "completed",
     "data": {"drift_detected": True, "drift_level": 0.013,
              "noise_detected": True, "noise_level": 0.07,
              "overall_quality_score": 0.68,
              "optimization_recommendations":
                  ["Rauschen \u00fcber der Schwelle: Messzeit erh\u00f6hen."]},
     "charts": {"sensor_dashboard": b64}},
    {"agent": "neural_network", "status": "completed",
     "data": {"model_results": {"CNN": {"r2_score": 0.595, "rmse": 0.627}}},
     "charts": {"prediction_vs_actual": b64}},
    {"agent": "calibration", "status": "completed",
     "data": {"best_r2_score": 0.82, "best_method": "PLS",
              "recommendations": ["Mehr Proben aufnehmen."]},
     "charts": {"ref_vs_pred": b64, "reg_coefficients": b64,
                "rmsecv_vs_n": b64}},
    {"agent": "faiss_similarity", "status": "completed",
     "data": {"matches": [{"reference_id": "db_a.txt", "similarity": 0.98}],
              "database_references": 3},
     "charts": {"similarity_top3": b64}},
]
crew_results = {"overall_quality_score": 79.0, "recommendations": [],
                "warnings": ["Testwarnung"]}
datasets = [{"file_name": "triad.txt",
             "preview": {"wavelengths": wavelengths,
                         "intensities": intensities},
             "reference_values": ref}]

agent = ChatbotAgent()
output = agent.execute({
    "per_agent_reports": per_agent,
    "crew_results": crew_results,
    "datasets": datasets,
    "overview_keys": ["spectrum", "quality_bar"],
})
kb = output.data.get("knowledge_base") or []
check("T1b agent completes with a knowledge base",
      output.status.name == "COMPLETED" and len(kb) >= 10, str(len(kb)))
check("T1c entries carry id/category/question/answer/keywords",
      all(set(("id", "category", "question", "answer", "keywords"))
          <= set(e) for e in kb))
check("T1d knowledge base strictly JSON serializable",
      json.loads(json.dumps(kb)) is not None)

joined = " ".join(e["answer"] for e in kb)
check("T1e real numbers flow into the answers (R2, score)",
      "0.820" in joined and "79" in joined, joined[:100])
check("T1f real sensor findings flow in (drift level)",
      "0.013" in joined and "Drift" in joined)
check("T1g real wavelength range flows in",
      any("410" in e["answer"] and "940" in e["answer"] for e in kb))
check("T1h no invented findings: answers only cite present results",
      "8.10" not in joined or "8.1" in str(ref))

figure_entries = [e for e in kb if e.get("figure")]
check("T1i entries reference figures by report number",
      len(figure_entries) >= 4
      and all(isinstance(e["figure"], int) for e in figure_entries),
      str([e["figure"] for e in figure_entries]))
numbers = sorted(e["figure"] for e in figure_entries)
check("T1j figure numbers are within the rendered figures (1..9)",
      all(1 <= n <= 9 for n in numbers), str(numbers))
check("T1k methods glossary present (PLS, PCA, R2, RMSE)",
      any("Partial Least Squares" in e["answer"] for e in kb)
      and any("Principal Component Analysis" in e["answer"] for e in kb))
check("T1l optimization recommendations become answers",
      any("Messzeit erh\u00f6hen" in e["answer"] for e in kb))
check("T1m warnings become answers", any("Testwarnung" in e["answer"] for e in kb))

minimal = ChatbotAgent().execute({"per_agent_reports": [], "crew_results": {},
                                  "datasets": []})
check("T1n empty results still yield a helpful fallback entry",
      len(minimal.data.get("knowledge_base") or []) >= 1)

# ---------------------------------------------------------------------------
# T2: widget rendering (offline, self-contained)
# ---------------------------------------------------------------------------
from services.report_chatbot import build_chatbot_widget, chatbot_html

widget = build_chatbot_widget(kb)
check("T2a widget rendered", len(widget) > 1000, str(len(widget)))
check("T2b knowledge base embedded as JSON",
      'var KB = [' in widget)
match = re.search(r'var KB = (\[.*?\]);', widget, re.S)
embedded = json.loads(match.group(1)) if match else []
check("T2c embedded base equals the agent output",
      embedded == kb, f"{len(embedded)} vs {len(kb)}")
check("T2d widget: KI-first local endpoint only, no external URLs",
      "http://" not in widget and "https://" not in widget
      and "XMLHttpRequest" not in widget
      and "fetch('/api/chatbot/message/'" in widget)
check("T2e script closing tag escaped in the JSON payload",
      "</script" not in re.search(r'var KB = (\[.*?\]);', widget, re.S).group(1))
check("T2f empty knowledge base -> no widget", build_chatbot_widget([]) == "")

html_result = chatbot_html(per_agent, crew_results, datasets,
                           overview_keys=["spectrum", "quality_bar"])
check("T2g chatbot_html never raises and returns the widget",
      html_result.get("widget", "").lstrip().startswith("<section"),
      str(html_result)[:60])
broken = chatbot_html([{"bad": object()}], {}, [], overview_keys=None)
check("T2h broken input never raises and returns a dict",
      isinstance(broken, dict) and "widget" in broken, str(broken)[:60])

# ---------------------------------------------------------------------------
# T3: final report integration
# ---------------------------------------------------------------------------
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")
import django

django.setup()

import types

from services.project_report import generate_final_html_report

report_src = (PROJECT / "services" / "project_report.py").read_text(encoding="utf-8")
widget_src = (PROJECT / "services" / "report_chatbot.py").read_text(encoding="utf-8")
check("T3a report builder wires the chatbot widget",
      "chatbot_html" in report_src
      and "Fragen zur Analyse" in widget_src)

html_path = ""
try:
    html_path = generate_final_html_report(
        types.SimpleNamespace(
            id="00000000-0000-0000-0000-000000000000",
            name="OP24 Chatbot", user_id=None,
            preparation_report={"datasets": [{
                "usable": True, "file_name": "triad.txt",
                "preview": {"wavelengths": wavelengths,
                            "intensities": intensities}}]}),
        {"request_id": "op24", "overall_quality_score": 79.0,
         "recommendations": [], "warnings": [], "errors": [],
         "processing_time": 0.2, "datasets_analyzed": 1,
         "per_agent_reports": per_agent},
        full_series=[{"file_name": "triad.txt", "wavelengths": wavelengths,
                      "intensities": intensities}])
except Exception as exc:  # pragma: no cover
    check("T3b final report generated", False, str(exc))
if html_path:
    content = Path(html_path).read_text(encoding="utf-8")
    check("T3b final report generated", html_path.endswith(".html"))
    check("T3c report contains the chatbot section",
          "Fragen zur Analyse (Chatbot)" in content
          and "chatbot-form" in content)
    check("T3d embedded base present in the report",
          "var KB = [" in content)
    check("T3e single chatbot instance in the report",
          content.count("chatbot-section") == 2)  # section id + css/js ref
    check("T3f report has no raw markdown leftovers", "{%" not in content)

print(f"OP24 report chatbot matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
