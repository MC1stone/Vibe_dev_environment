"""Iterations-Evaluation fuer die Crew-Analyse (Iterationsregel).

Mission Statement: Der Zyklus laeuft Analyse -> Evaluation ->
Optimierung -> Reanalyse bis ERRORS=0, CRITICAL_WARNINGS=0,
OPEN_CHANGE_REQUESTS=0. Dieses Modul bewertet ein AnalysisResult gegen
diese Kriterien und liefert - abgestuft statt blockierend:

- verdict: 'converged' | 'improvable' | 'diverged'
- stop_conditions: {...} - welche Steuerkriterien erfuellt sind
- iteration_plan: konkrete, datengestuetzte Optimierungsschritte fuer
  die naechste Iteration (_was_ soll sich aendern und _warum_)
- Der Plan basiert NUR auf Befunden im Result (Anti-Halluzination):
  z.B. Kalibration unter Schwellwert -> Praeprozessing-Variante /
  mehr Messungen; Metadaten-Konflikte -> Nutzer-Klaerung; fehlende
  Referenzwerte -> Datenergaenzung.
"""

from typing import Any, Dict, List


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def evaluate_iteration(result: Any,
                       iteration: int = 0,
                       max_iterations: int = 100) -> Dict[str, Any]:
    """Bewerte ein AnalysisResult gegen die Stop-Bedingungen und baue
    den Iterationsplan. Never raises."""
    try:
        errors = int(len(getattr(result, "errors", None) or []))
        warnings = list(getattr(result, "warnings", None) or [])
        quality = float(getattr(result, "overall_quality_score", 0.0) or 0.0)
        calib = dict(getattr(result, "calibration_results", None) or {})
        stat = dict(getattr(result, "statistical_analysis_results", None) or {})

        critical_warnings = [w for w in warnings
                              if any(k in str(w).lower()
                                     for k in ("failed", "error", "critical",
                                               "degraded", "not_applicable"))]
        open_change_requests: List[Dict[str, Any]] = []
        plan_steps: List[Dict[str, Any]] = []

        # --- Datengetriebene Planbildung (nur aus Befunden) ---
        if calib.get("status") == "not_applicable":
            # Klassifikations-Kontext: kein Change-Request - die Agenten
            # haben fachlich richtig entschieden.
            pass
        elif calib and calib.get("best_r2_score") is not None:
            threshold = float(calib.get("thresholds", {}).get("r2", 0.8)
                              if isinstance(calib.get("thresholds"), dict)
                              else 0.8)
            best_r2 = float(calib["best_r2_score"])
            if best_r2 < threshold:
                open_change_requests.append({
                    "topic": "kalibration_unter_schwellwert",
                    "finding": f"Beste Kalibration R2={best_r2:.3f} < "
                               f"Schwellwert {threshold}",
                })
                plan_steps.append({
                    "step": "kalibration_optimieren",
                    "finding": f"R2={best_r2:.3f} unter Schwellwert {threshold}",
                    "action": "Praeprozessing-Variante testen (SNV/MSC/"
                              "Savitzky-Golay-Kombination) und Messumfang "
                              "erweitern, dann neu kalibrieren",
                    "agent": "calibration",
                })
        if stat.get("analysis_mode") == "classification":
            lda = (stat.get("method_results", {}) or {}).get("LDA", {})
            acc = lda.get("cv_accuracy_mean")
            if acc is not None and float(acc) < 0.7:
                open_change_requests.append({
                    "topic": "klassifikation_schwach",
                    "finding": f"LDA CV-Genauigkeit {float(acc) * 100:.1f}% "
                               f"unter 70%",
                })
                plan_steps.append({
                    "step": "klassifikation_verbessern",
                    "finding": f"CV-Genauigkeit {float(acc) * 100:.1f}%",
                    "action": "Mehr Messungen je Klasse aufnehmen; Kanal-"
                              "Auswahl pruefen (informationsarme Kanaele "
                              "koennen Streuung erhoehen)",
                    "agent": "statistical_analysis",
                })
        if quality < 60.0 and not plan_steps:
            open_change_requests.append({
                "topic": "qualitaet_niedrig",
                "finding": f"Overall-Qualitaet {quality:.1f}/100",
            })
            plan_steps.append({
                "step": "qualitaet_pruefen",
                "finding": f"Overall {quality:.1f}/100",
                "action": "Sensor-/Datenqualitaet pruefen (Drift, Ausreisser, "
                          "Saugeraettigung) und Metadaten ergaenzen",
                "agent": "crew",
            })

        stop_conditions = {
            "errors_zero": errors == 0,
            "critical_warnings_zero": len(critical_warnings) == 0,
            "open_change_requests_zero": len(open_change_requests) == 0,
        }
        converged = all(stop_conditions.values())
        at_limit = iteration + 1 >= max_iterations
        verdict = ("converged" if converged
                   else ("diverged" if at_limit else "improvable"))

        return _json_safe({
            "iteration": iteration,
            "verdict": verdict,
            "stop_conditions": stop_conditions,
            "errors": errors,
            "critical_warnings": [str(w) for w in critical_warnings],
            "open_change_requests": open_change_requests,
            "iteration_plan": plan_steps,
            "overall_quality_score": quality,
            "note": ("Iterationsregel: Konvergiert wenn ERRORS=0, "
                     "CRITICAL_WARNINGS=0, OPEN_CHANGE_REQUESTS=0; sonst "
                     "Plan fuer die naechste Iteration." if not converged
                     else "Alle Stop-Bedingungen erfuellt."),
        })
    except Exception as exc:
        return _json_safe({
            "iteration": iteration,
            "verdict": "diverged",
            "evaluation_error": str(exc),
            "stop_conditions": {"errors_zero": False,
                                "critical_warnings_zero": False,
                                "open_change_requests_zero": False},
            "iteration_plan": [],
        })
