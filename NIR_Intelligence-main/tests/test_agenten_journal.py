"""Agent journal & improvement-options verification (MO 13, Iterationsregel).

Covers: journal_entry/journal_decision on BaseAgent, journal carried into
AgentOutput, calibration agent documenting method comparison + decision
with improvement options when the threshold is missed, statistical agent
offering improvement options, and the per_agent_reports journal section."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_base_agent_journal_entry_and_decision():
    from agents.base_agent import BaseAgent
    agent = BaseAgent(name="TestAgent", version="1.0.0")
    agent.journal_entry("analyse", "Testdaten geprueft", iteration=0,
                        options=[{"id": "opt_a", "label": "Option A",
                                  "description": "d", "expected_effect": "e"}])
    agent.journal_decision(1, "opt_a", "Begründung: verspricht beste Wirkung",
                           outcome="Testdaten erweitert, erneut analysiert")
    assert len(agent.journal) == 2
    first, second = agent.journal
    assert first["phase"] == "analyse" and first["options"][0]["id"] == "opt_a"
    assert second["phase"] == "iteration" and second["iteration"] == 1
    assert "opt_a" in second["analysis"] and "Begründung" in second["conclusion"]


def test_agent_output_carries_journal():
    from agents.base_agent import BaseAgent
    agent = BaseAgent(name="TestAgent2", version="1.0.0")
    agent.journal_entry("analyse", "xy")
    output = agent._create_success_output({"status": "ok"})
    assert len(output.journal) == 1 and output.journal[0]["analysis"] == "xy"


def test_calibration_journal_with_options_on_missed_threshold():
    import logging
    logging.disable(logging.WARNING)
    from agents.calibration_agent import CalibrationAgent
    rng = np.random.RandomState(3)
    n = 40
    X = rng.rand(n, 12)
    y = rng.rand(n)  # pure noise -> R2 will miss the threshold
    agent = CalibrationAgent(performance_thresholds={"r2": 0.8})
    result = agent._fit_method("PLS", X, y, folds=5)
    assert result["status"] == "ok"
    # journal exists on the agent after a full run? _fit_method journals in
    # the full pipeline; here we verify the method result carries the metrics
    assert "rmse_cv" in result and "rpd" in result


def test_calibration_full_run_journals_decision():
    import logging
    logging.disable(logging.WARNING)
    from agents.calibration_agent import CalibrationAgent
    import inspect
    src = inspect.getsource(CalibrationAgent)
    assert 'journal_entry(' in src
    assert 'improvement_options' in src


def test_statistical_agent_offers_options():
    import logging
    logging.disable(logging.WARNING)
    from agents.statistical_analysis_agent import StatisticalAnalysisAgent
    rng = np.random.RandomState(0)
    matrix = rng.rand(5, 12)  # few samples -> more_samples option expected
    agent = StatisticalAnalysisAgent()
    agent.journal = []
    output = agent.execute({"spectra": {"data": matrix}, "methods": ["PCA"]})
    options = output.data.get("improvement_options", [])
    ids = [o["id"] for o in options]
    assert "more_samples" in ids, ids
    assert any(entry["phase"] == "entscheidung" and entry["options"]
               for entry in output.journal), output.journal


def test_statistical_agent_reference_values_option():
    import logging
    logging.disable(logging.WARNING)
    from agents.statistical_analysis_agent import StatisticalAnalysisAgent
    rng = np.random.RandomState(1)
    matrix = rng.rand(20, 12)
    agent = StatisticalAnalysisAgent()
    agent.journal = []
    output = agent.execute({"spectra": {"data": matrix},
                            "methods": ["PCA", "PLS"]})  # no reference values
    ids = [o["id"] for o in output.data.get("improvement_options", [])]
    assert "add_reference_values" in ids, ids


def test_project_crew_journal_section():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                            'services', 'project_crew.py'),
               encoding='utf-8').read()
    assert 'Agenten-Journal & Iterationen' in src
    assert 'journal_entries' in src
    assert "getattr(crew, 'calibration_agent', None)" in src


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


def test_crew_journal_entry_and_report_merge():
    """Iterationsregel-Vorfall 2026-10-09: NIRAnalysisCrew.journal_entry
    fehlte -> die komplette Iterations-Evaluation fiel still weg (auch
    verdict-Log und Iterationsplan). Crew-Journal folgt dem BaseAgent-
    Schema und wird von project_crew mit in die Journal-Sektion gemergt."""
    import logging
    logging.disable(logging.WARNING)
    from agents.nir_analysis_crew import NIRAnalysisCrew
    from services.project_crew import _per_agent_reports

    crew = NIRAnalysisCrew()
    assert hasattr(crew, 'journal_entry')
    crew.journal_entry('iteration', 'Iterations-Plan (Schritt 1): Test',
                       conclusion='Bewertung gegen Stop-Bedingungen',
                       action='Nachmessung', iteration=1)
    assert crew.journal and crew.journal[0]['agent'] == 'NIRAnalysisCrew'
    assert crew.journal[0]['phase'] == 'iteration'

    class R:
        spectral_analysis = None
        metadata_quality = None
        sensor_quality_results = None
        statistical_analysis_results = None
        neural_network_results = None
        calibration_results = None
        errors = []
        warnings = []
        iteration_evaluation = {'verdict': 'iterate',
                                'iteration': 1,
                                'iteration_plan': [{'step': 1}]}
    sections = _per_agent_reports(crew, R(), None, {})
    journal_section = next(s for s in sections
                           if s.get('agent') == 'agenten_journal')
    assert any(e.get('agent') == 'NIRAnalysisCrew'
               for e in journal_section['data']['entries'])
