# NIR Intelligence Platform - Chatbot Agent (OP24)
# Release-time agent that turns the REAL crew results into a structured
# Q&A knowledge base for the embedded report chatbot. Consistent with the
# OP14 truthfulness rule: the agent only answers what the results actually
# contain - every answer is built from the real per-agent data (scores,
# R2, RMSE, drift levels, wavelengths, recommendations) and carries the
# reference to the figure or section it comes from. Nothing is invented.
#
# The knowledge base is a list of entries:
#   {'id', 'category', 'question', 'answer', 'keywords', 'figure'}
# The embedded widget (services/report_chatbot.py) matches student
# questions against keywords + question text and shows the best entry -
# fully offline, no server needed.

import logging
import re
from typing import Any, Dict, List, Optional

from .base_agent import AgentOutput, AgentStatus, BaseAgent

logger = logging.getLogger("Agent.ChatbotAgent")


def _fmt(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


class ChatbotAgent(BaseAgent):
    """Agent for building the report Q&A knowledge base.

    context keys:
    - per_agent_reports: the per-agent sections of the crew result
    - crew_results: the overall crew result dict (scores, warnings)
    - datasets: usable datasets (wavelength range, references)
    - overview_figures: number of overview charts before the sections
    """

    def __init__(self, **kwargs):
        super().__init__(name="ChatbotAgent", version="1.0.0", **kwargs)
        self.dependencies = []

    # ------------------------------------------------------------------
    # figure numbering: identical logic to student_report.figure_explanations
    # ------------------------------------------------------------------
    @staticmethod
    def _figure_keys(per_agent: List[Dict[str, Any]],
                     overview_keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        figures = []
        for key in (overview_keys or []):
            figures.append({"key": key, "section": None})
        for section in per_agent:
            for key, url in (section.get("charts") or {}).items():
                if url:
                    figures.append({"key": key, "section": section.get("agent")})
        for index, figure in enumerate(figures, start=1):
            figure["number"] = index
        return figures

    def _find(self, per_agent: List[Dict[str, Any]],
              agent: str) -> Optional[Dict[str, Any]]:
        return next((s for s in per_agent if s.get("agent") == agent), None)

    def _fig(self, figures: List[Dict[str, Any]], key: str,
             section: Optional[str] = None) -> Optional[int]:
        for figure in figures:
            if figure["key"] == key and (section is None
                                         or figure["section"] == section):
                return figure["number"]
        return None

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Build the Q&A knowledge base from the real results."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting chatbot knowledge base generation")

            context = context or {}
            per_agent = list(context.get("per_agent_reports") or [])
            crew_results = context.get("crew_results") or {}
            datasets = list(context.get("datasets") or [])
            overview_keys = list(context.get("overview_keys") or [])
            figures = self._figure_keys(per_agent, overview_keys)

            entries: List[Dict[str, Any]] = []

            def add(category: str, question: str, answer: str,
                    keywords: List[str], figure: Optional[int] = None):
                entries.append({
                    "id": f"qa{len(entries) + 1}",
                    "category": category,
                    "question": question,
                    "answer": answer,
                    "keywords": [k.lower() for k in keywords],
                    "figure": figure,
                })

            # --- project overview ------------------------------------------
            score = crew_results.get("overall_quality_score")
            if score is not None:
                add("Projekt", "Wie gut ist die Analyse insgesamt?",
                    f"Die Gesamtqualit\u00e4t der Analyse betr\u00e4gt "
                    f"{_fmt(score, 1)} von 100 Punkten. Der Wert fasst die "
                    "Bewertungen der einzelnen Bereiche (Spektralanalyse, "
                    "Metadaten, Sensor, Statistik, Kalibration) zusammen.",
                    ["gesamt", "qualit\u00e4t", "score", "bewertung", "insgesamt",
                     "ergebnis", "punktzahl"])
            num_datasets = len(datasets)
            if num_datasets:
                names = ", ".join(str(d.get("file_name", "?")) for d in datasets[:3])
                add("Projekt", "Welche Dateien wurden analysiert?",
                    f"Analysiert wurden {num_datasets} nutzbare Datei(en): "
                    f"{names}"
                    + (" (und weitere)" if num_datasets > 3 else "") + ".",
                    ["datei", "dateien", "welche", "datensatz", "upload", "proben"])

            # --- spectral analysis -------------------------------------------
            wavelengths: List[Any] = []
            if datasets:
                preview = datasets[0].get("preview") or {}
                wavelengths = (datasets[0].get("wavelengths")
                               or preview.get("wavelengths") or [])
            if wavelengths:
                wl = sorted(float(w) for w in wavelengths if w is not None)
                fig_spectrum = self._fig(figures, "spectrum")
                add("Spektrum",
                    "Welchen Wellenl\u00e4ngenbereich deckt die Messung ab?",
                    f"Die Messung umfasst {len(wl)} Kan\u00e4le von {wl[0]:.0f} bis "
                    f"{wl[-1]:.0f} nm. "
                    + (f"Abbildung {fig_spectrum} zeigt das aufgenommene "
                       "Spektrum \u00fcber diesen Bereich."
                       if fig_spectrum else ""),
                    ["wellenl\u00e4nge", "bereich", "kanal", "kan\u00e4le", "nm",
                     "spektrum", "messen", "messbereich"], fig_spectrum)
                add("Spektrum",
                    "Welche Peaks sind f\u00fcr welche Inhaltsstoffe "
                    "verantwortlich?",
                    "Im NIR absorbieren vor allem Oberschwingungen von O-H- "
                    "(Wasser, Zucker) und C-H-Bindungen (Fett, Zucker, "
                    "Zellwand): z. B. liegt eine Wasserbande (O-H) um 970 und "
                    "eine starke um 1450/1940 nm, Zucker- und Fett-C-H-Banden "
                    "um 910/1190/1720 nm. Im sichtbaren Teil kommen "
                    "Pigmente hinzu: Chlorophyll absorbiert um 430 und 660 nm, "
                    "Carotinoide um 520 nm. Die Details stehen in der "
                    "Diskussion des Berichts.",
                    ["peak", "peaks", "inhaltsstoff", "inhaltstoffe", "bande",
                     "absorption", "wasser", "zucker", "fett", "chlorophyll",
                     "bandenzuordnung"])
            spectral = self._find(per_agent, "spectral_analysis")
            if spectral:
                data = spectral.get("data") or {}
                grade = data.get("quality_grade")
                qscore = data.get("quality_score")
                if grade or qscore is not None:
                    add("Spektrum", "Wie ist die Qualit\u00e4t der Spektraldaten?",
                        "Die Spektralanalyse bewertet die Daten mit "
                        + (f"Note '{grade}'" if grade else "keiner Note")
                        + (f" ({_fmt(qscore, 1)}/100)" if qscore is not None else "")
                        + ". "
                        + ("Auff\u00e4lligkeiten: "
                           + "; ".join(str(i) for i in
                                       (data.get("issues_detected") or []))
                           if data.get("issues_detected") else "Keine "
                           "Auff\u00e4lligkeiten erkannt."),
                        ["spektral", "spektrum", "datenqualit\u00e4t",
                         "auff\u00e4llig", "problem"])

            # --- sensor quality ---------------------------------------------
            sensor = self._find(per_agent, "sensor_quality")
            if sensor:
                data = sensor.get("data") or {}
                parts = []
                if data.get("drift_detected") is True:
                    parts.append(f"eine Drift erkannt (Level "
                                 f"{_fmt(data.get('drift_level'))})")
                elif data.get("drift_detected") is False:
                    parts.append("keine Drift")
                if data.get("offset_detected") is True:
                    parts.append("einen Baseline-Offset")
                if data.get("noise_detected") is True:
                    parts.append(f"erh\u00f6htes Rauschen (Level "
                                 f"{_fmt(data.get('noise_level'))})")
                elif data.get("noise_detected") is False:
                    parts.append("das Rauschen im Rahmen")
                score_sensor = data.get("overall_quality_score")
                fig_dashboard = self._fig(figures, "sensor_dashboard")
                add("Sensor", "Wie ist der Zustand des Sensors?",
                    "Die Sensorpr\u00fcfung meldet "
                    + (" und ".join(parts) if parts else "keine Befunde")
                    + (f"; Gesamt-Score {_fmt(score_sensor, 2)} von 1.00."
                       if score_sensor is not None else ".")
                    + (f" Abbildung {fig_dashboard} zeigt Kontrollkarte, "
                       "Kurven-Overlay, Kanal-Rauschen und Gauge im \u00dcberblick."
                       if fig_dashboard else ""),
                    ["sensor", "drift", "rauschen", "noise", "offset",
                     "zustand", "instrument", "ger\u00e4t", "kontrollkarte"],
                    fig_dashboard)
                for rec in (data.get("optimization_recommendations") or []):
                    add("Sensor", "Wie kann ich die Messqualit\u00e4t verbessern?",
                        str(rec), ["verbessern", "optimieren", "empfehlung",
                                   "ma\u00dfnahme", "tip", "rauschen", "drift"])

            # --- statistics / PCA ---------------------------------------------
            stats = self._find(per_agent, "statistical_analysis")
            if stats:
                fig_score = self._fig(figures, "score_plot")
                add("Statistik",
                    "Was sagt der Score-Plot der PCA aus?",
                    "Die Hauptkomponentenanalyse (PCA, Principal Component "
                    "Analysis) fasst die vielen Wellenl\u00e4ngen zu wenigen "
                    "Hauptkomponenten zusammen. "
                    + (f"Abbildung {fig_score} zeigt die Messungen als Punkte "
                       "in der Ebene der ersten beiden Komponenten: nah "
                       "beieinander = \u00e4hnliche Proben, einzelne Randpunkte "
                       "sind m\u00f6gliche Ausreisser."
                       if fig_score else "")
                    + " Die Ladungen (Loadings) zeigen, welche Wellenl\u00e4ngen "
                    "jede Komponente pr\u00e4gen.",
                    ["pca", "score", "hauptkomponente", "cluster", "ausreisser",
                     "statistik", "biplot", "loadings"], fig_score)

            # --- neural network ----------------------------------------------
            neural = self._find(per_agent, "neural_network")
            if neural:
                data = neural.get("data") or {}
                models = (data.get("model_results") or {})
                for name, result in models.items():
                    if not isinstance(result, dict):
                        continue
                    r2 = result.get("r2_score")
                    rmse = result.get("rmse")
                    fig_pred = self._fig(figures, "prediction_vs_actual")
                    add("Neuronales Netz",
                        f"Wie gut ist das {name}-Modell?",
                        f"Das {name}-Modell erreicht "
                        + (f"R\u00b2 = {_fmt(r2)}" if r2 is not None else "keinen R\u00b2-Wert")
                        + (f" und RMSE = {_fmt(rmse)} \u00b0Brix"
                           if rmse is not None else "")
                        + ". R\u00b2 (Bestimmtheitsmass) sagt aus, wie viel der "
                        "Streuung das Modell erkl\u00e4rt (1 = perfekt). Der RMSE "
                        "ist der mittlere Vorhersagefehler in \u00b0Brix. "
                        + (f"Abbildung {fig_pred} zeigt Vorhersage gegen "
                           "Referenzwert." if fig_pred else ""),
                        ["cnn", "neuronales", "netz", "modell", "r2", "rmse",
                         "vorhersage", "maschine", "ki", "k\u00fcnstlich",
                         "neural", name.lower()], fig_pred)
                deferred = data.get("models_deferred") or []
                if deferred:
                    names = ", ".join(str(d.get("model")) for d in deferred
                                      if isinstance(d, dict))
                    add("Neuronales Netz",
                        "Warum wurde ein Modell nicht trainiert?",
                        f"Nicht trainierte Modelle: {names}. Der Grund steht "
                        "im Berichtsteil der Netzwerkanalyse - h\u00e4ufig fehlt "
                        "eine optionale Abh\u00e4ngigkeit (z. B. TensorFlow) oder "
                        "es gibt zu wenig Kalibrationsproben.",
                        ["warum", "nicht", "deferred", "fehlend", "tensorflow",
                         "trainiert"])

            # --- calibration ---------------------------------------------------
            calibration = self._find(per_agent, "calibration")
            if calibration:
                data = calibration.get("data") or {}
                best = data.get("best_r2_score")
                method = data.get("best_method")
                fig_ref = self._fig(figures, "ref_vs_pred")
                add("Kalibration",
                    "Wie gut ist die Kalibration?",
                    f"Die beste Kalibrationsmethode ist {method or 'PLS'} "
                    + (f"mit einem kreuzvalidierten R\u00b2 = {_fmt(best)}."
                       if best is not None else "")
                    + " Die Kreuzvalidierung l\u00e4sst jedes Sample einmal "
                    "aussen vor und testet daran - der Wert ist also "
                    "out-of-sample. "
                    + (f"Abbildung {fig_ref} zeigt Referenz gegen Vorhersage."
                       if fig_ref else ""),
                    ["kalibration", "kalibrier", "pls", "regression", "g\u00fcte",
                     "validierung", "rmsecv", "vorhersageg\u00fcte"], fig_ref)
                fig_coef = self._fig(figures, "reg_coefficients")
                if fig_coef:
                    add("Kalibration",
                        "Warum funktioniert die Kalibration? Welche "
                        "Wellenl\u00e4ngen treiben sie?",
                        f"Abbildung {fig_coef} zeigt die "
                        "Regressionskoeffizienten pro Wellenl\u00e4nge: Positive "
                        "S\u00e4ulen erh\u00f6hen die Vorhersage mit steigender "
                        "Intensit\u00e4t, negative senken sie. Grosse Betr\u00e4ge "
                        "markieren die Wellenl\u00e4ngen, \u00fcber die das Modell "
                        "den Gehalt 'sieht' - physikalisch sind das "
                        "typischerweise die O-H- und C-H-Banden des Analyten.",
                        ["koeffizient", "warum", "funktioniert", "erkl\u00e4rung",
                         "wichtigkeit", "wellenl\u00e4nge"], fig_coef)
                fig_rmse = self._fig(figures, "rmsecv_vs_n")
                if fig_rmse:
                    add("Kalibration",
                        "Wie viele PLS-Komponenten sind optimal?",
                        f"Abbildung {fig_rmse} zeigt den "
                        "Kreuzvalidierungsfehler RMSECV \u00fcber die Anzahl der "
                        "PLS-Komponenten (die Modellkomplexit\u00e4t). Das Minimum "
                        "(rote Linie) ist die optimale Componentenzahl: mehr "
                        "f\u00fchrt zu Overfitting, weniger nutzt die Information "
                        "nicht aus. PLS (Partial Least Squares) ist ein "
                        "Regressionsverfahren, das korrelierte Wellenl\u00e4ngen "
                        "zu wenigen Komponenten b\u00fcndelt.",
                        ["komponenten", "rmsecv", "komplexit\u00e4t", "optimal",
                         "wie viele", "overfitting"], fig_rmse)

            # --- similarity -------------------------------------------------------
            similarity = self._find(per_agent, "faiss_similarity")
            if similarity:
                data = similarity.get("data") or {}
                matches = data.get("matches") or []
                fig_top3 = self._fig(figures, "similarity_top3")
                if matches:
                    best_match = matches[0]
                    add("Datenbank",
                        "Gibt es \u00e4hnliche Spektren in der Datenbank?",
                        f"Die \u00c4hnlichkeitssuche (FAISS) fand {len(matches)} "
                        "Treffer; der beste ist "
                        f"{best_match.get('reference_id', '?')} "
                        f"(\u00c4hnlichkeit {_fmt(best_match.get('similarity'), 3)})."
                        + (f" Abbildung {fig_top3} zeigt die Messung mit den "
                           "drei \u00e4hnlichsten Spektren."
                           if fig_top3 else ""),
                        ["\u00e4hnlich", "datenbank", "faiss", "vergleich",
                         "treffer", "match", "spektren"], fig_top3)
                db_sources = data.get("database_references")
                if db_sources:
                    add("Datenbank",
                        "Wie viele Referenzspektren kamen aus der Datenbank?",
                        f"In den Vergleich flossen {db_sources} "
                        "persistente Datenbankeintr\u00e4ge ein (nur Spektren "
                        "auf demselben Wellenl\u00e4ngengitter, gleiche "
                        "Sichtbarkeit vorausgesetzt).",
                        ["datenbank", "referenz", "eintrag", "wie viele"])

            # --- recommendations / optimization -----------------------------------
            options: List[str] = []
            for section in per_agent:
                for rec in ((section.get("recommendations")
                             or (section.get("data") or {}).get("recommendations")
                             or (section.get("data") or {})
                             .get("optimization_recommendations") or [])):
                    text = str(rec)
                    if text not in options:
                        options.append(text)
            for rec in crew_results.get("recommendations") or []:
                text = str(rec)
                if text not in options:
                    options.append(text)
            if options:
                add("Optimierung",
                    "Was kann ich optimieren?",
                    "Die Analyse schl\u00e4gt folgende Massnahmen vor: "
                    + " ".join(f"({i}) {o}" for i, o in enumerate(options, 1)),
                    ["optimierung", "verbessern", "empfehlung", "massnahme",
                     "tip", "was kann ich"])
            warnings = list(crew_results.get("warnings") or [])
            if warnings:
                add("Warnungen",
                    "Welche Warnungen gibt es?",
                    "Der Bericht enth\u00e4lt folgende Warnungen: "
                    + " ".join(f"({i}) {w}" for i, w in enumerate(warnings, 1)),
                    ["warnung", "problem", "fehler", "kritisch"])

            # --- methods glossary (fixed knowledge, no data) ---------------------
            add("Methoden", "Was ist PLS?",
                "PLS (Partial Least Squares) ist eine Regressionsmethode der "
                "Chemometrie: Sie b\u00fcndelt viele stark korrelierte "
                "Wellenl\u00e4ngen zu wenigen latenten Komponenten und berechnet "
                "damit eine Vorhersagegleichung f\u00fcr den Zielwert (z. B. "
                "Brix). Vorteil gegen\u00fcber klassischer Regression: Sie "
                "funktioniert auch, wenn die Wellenl\u00e4ngenzahl die "
                "Probenzahl \u00fcbersteigt (Multikollinearit\u00e4t).",
                ["pls", "partial least", "methode", "regression", "chemometrie"])
            add("Methoden", "Was ist PCA?",
                "PCA (Principal Component Analysis, Hauptkomponentenanalyse) "
                "ist ein un\u00fcberwachtes Verfahren: Sie projiziert die "
                "hochdimensionalen Spektren auf wenige Achsen maximaler "
                "Streuung. Sie zeigt \u00c4hnlichkeiten, Cluster und "
                "Ausreisser - sagt aber nichts \u00fcber den Gehalt aus "
                "(daf\u00fcr braucht es eine Kalibration).",
                ["pca", "hauptkomponente", "methode", "cluster",
                 "un\u00fcberwacht"])
            add("Methoden", "Was bedeutet R\u00b2?",
                "R\u00b2 (Bestimmtheitsmass) sagt aus, welcher Anteil der "
                "Streuung der Referenzwerte vom Modell erkl\u00e4rt wird: "
                "1 = perfekte Vorhersage, 0 = nicht besser als der Mittelwert. "
                "Faustregel f\u00fcr NIR-Kalibrationen: ab 0.9 sehr gut, 0.8-0.9 "
                "gut, 0.6-0.8 Screening, darunter eingeschr\u00e4nkt.",
                ["r2", "r\u00b2", "bestimmtheitsmass", "statistik", "g\u00fcte"])
            add("Methoden", "Was ist der Unterschied zwischen RMSE, RMSECV "
                "und RMSEP?",
                "RMSE ist der mittlere Vorhersagefehler (Wurzel der "
                "mittleren Fehlerquadrate). RMSECV entsteht bei der "
                "Kreuzvalidierung (jedes Sample wird einmal aussen vor "
                "getestet), RMSEP auf einer unabh\u00e4ngigen "
                "Validierungsstichprobe. RMSEP ist der ehrlichste Wert, "
                "liegt in diesem Bericht aber nur vor, wenn eine separate "
                "Validierung durchgef\u00fchrt wurde - sonst ist RMSECV der "
                "beste Sch\u00e4tzer.",
                ["rmse", "rmsecv", "rmsep", "fehler", "validierung",
                 "unterschied"])

            if not entries:
                add("Projekt", "Was kann ich hier fragen?",
                    "Es liegen noch keine detaillierten Analysedaten vor. "
                    "Fragen Sie nach dem Wellenl\u00e4ngenbereich, der "
                    "Kalibration, dem Sensor oder den Optimierungsvorschl\u00e4gen.",
                    ["hilfe", "was", "fragen"])

            self.status = AgentStatus.COMPLETED
            self.logger.info("Chatbot knowledge base ready: %s entries",
                             len(entries))
            return self._create_success_output({
                "knowledge_base": entries,
                "num_entries": len(entries),
                "categories": sorted({e["category"] for e in entries}),
            })
        except Exception as e:
            return self._handle_error(e)
