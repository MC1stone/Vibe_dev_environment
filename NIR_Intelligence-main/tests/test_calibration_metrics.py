"""Calibration metrics verification: RMSECV and RPD alongside R2.

RPD = std(y) / RMSECV is the standard chemometric quality figure: >2 usable,
>3 good, >5 excellent for screening calibrations. Without it, a CV R2 alone
cannot be judged against the reference method spread."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_fit_method_reports_rmse_cv_and_rpd():
    import logging
    logging.disable(logging.WARNING)
    from agents.calibration_agent import CalibrationAgent
    rng = np.random.RandomState(42)
    n = 60
    X = rng.rand(n, 50)
    y = 3.0 * X[:, 0] + 0.5 * X[:, 1] + rng.normal(0, 0.1, n)
    agent = CalibrationAgent()
    result = agent._fit_method("PLS", X, y, folds=5)
    assert result["status"] == "ok", result
    assert "rmse_cv" in result and result["rmse_cv"] > 0
    assert "rpd" in result and result["rpd"] is not None
    y_std = float(np.std(y, ddof=1))
    assert abs(result["rpd"] - y_std / result["rmse_cv"]) < 1e-9
    assert abs(result["y_std"] - y_std) < 1e-9


def test_rpd_quality_classification_values():
    import logging
    logging.disable(logging.WARNING)
    from agents.calibration_agent import CalibrationAgent
    rng = np.random.RandomState(7)
    n = 80
    X = rng.rand(n, 30)
    y = 5.0 * X[:, 0] + rng.normal(0, 0.01, n)   # low noise -> high RPD
    agent = CalibrationAgent()
    result = agent._fit_method("PLS", X, y, folds=5)
    assert result["rpd"] > 5.0, result   # excellent screening calibration


def test_ui_template_and_js_show_metrics():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    tpl = open(os.path.join(root, 'django_project', 'templates',
                            'calibration_overview.html'), encoding='utf-8').read()
    assert 'RMSECV' in tpl and 'RPD' in tpl
    assert 'model.rmse_cv|floatformat:4' in tpl
    assert 'model.rpd|floatformat:1' in tpl
    js = open(os.path.join(root, 'django_project', 'static', 'js',
                           'analysis.js'), encoding='utf-8').read()
    assert 'PLS RMSECV' in js and 'PLS RPD' in js
    assert 'PCR RMSECV' in js and 'PCR RPD' in js


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
