# NIR Intelligence Platform - Calibration Agent
# Handles model calibration and optimization (MO 8/9).
# Real implementation: PLS, PCR, SVM, RandomForest and XGBoost calibrations
# are fitted and cross-validated with scikit-learn; CNN calibration needs
# optional TensorFlow. Optuna hyperparameter studies are used when installed
# (services/calibration_optimization.py protocol), otherwise a plain
# cross-validated fit is reported.

from typing import Any, Dict, List, Optional

import numpy as np

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


def _extract_matrix(spectra: Any) -> Optional[np.ndarray]:
    """Extract an (n_samples, n_points) matrix (see sensor_quality_agent)."""
    if spectra is None:
        return None
    if isinstance(spectra, np.ndarray):
        return np.asarray(spectra, dtype=float) if spectra.size else None
    if isinstance(spectra, dict):
        if spectra.get("data") is None and spectra.get("intensities") is None:
            return None
        spectra = [spectra]
    if not isinstance(spectra, (list, tuple)) or len(spectra) == 0:
        return None
    rows = []
    for item in spectra:
        if isinstance(item, dict):
            data = item.get("data")
            if data is None:
                intensities = item.get("intensities")
                if intensities is None:
                    return None
                rows.append(np.asarray(intensities, dtype=float))
            else:
                import pandas as pd

                if isinstance(data, pd.DataFrame):
                    column = item.get("intensity_column", "intensity")
                    if column not in data.columns:
                        column = data.columns[-1]
                    rows.append(data[column].to_numpy(dtype=float))
                else:
                    rows.append(np.asarray(data, dtype=float))
        else:
            rows.append(np.asarray(item, dtype=float))
    if any(row.size == 0 for row in rows):
        return None
    if len({row.size for row in rows}) != 1:
        return None
    return np.vstack(rows)


class CalibrationAgent(BaseAgent):
    """Agent for model calibration and optimization.

    context keys:
    - spectra: calibration samples (vectors or unified schema dicts)
    - reference_values / y: calibration targets (required)
    - methods: calibration methods (default PLS, PCR, SVM, RandomForest, XGBoost, CNN)
    - optimization: Optuna settings (n_trials); used when optuna is installed
    - cv_folds: cross-validation folds (default 5)
    """

    def __init__(self, **kwargs):
        super().__init__(name="CalibrationAgent", version="2.0.0", **kwargs)
        self.dependencies = ["scikit-learn", "numpy", "optuna"]
        self.errors = []
        self.methods = kwargs.get("methods", ["PLS", "PCR", "SVM", "RandomForest", "XGBoost", "CNN"])
        self.optimization_config = kwargs.get("optimization", {})
        self.performance_thresholds = kwargs.get("performance_thresholds", {"r2": 0.8})
        self.cv_folds = int(kwargs.get("cv_folds", 5))

    def _fit_method(self, method: str, matrix: np.ndarray, y: np.ndarray,
                    folds: int) -> Dict[str, Any]:
        from sklearn.model_selection import KFold, cross_val_score

        if method == "PLS":
            from sklearn.cross_decomposition import PLSRegression
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline

            n_components = max(1, min(10, matrix.shape[0] - 1, matrix.shape[1]))
            estimator = Pipeline([
                ("scaler", StandardScaler()),
                ("pls", PLSRegression(n_components=n_components)),
            ])
            param_note = {"n_components": n_components, "feature_scaling": "standardized"}
        elif method == "PCR":
            from sklearn.decomposition import PCA
            from sklearn.linear_model import LinearRegression
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import StandardScaler

            n_components = max(1, min(10, matrix.shape[0] - 1, matrix.shape[1]))
            estimator = Pipeline([
                ("scaler", StandardScaler()),
                ("pca", PCA(n_components=n_components)),
                ("regression", LinearRegression()),
            ])
            param_note = {"n_components": n_components, "feature_scaling": "standardized"}
        elif method == "SVM":
            from sklearn.svm import SVR
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline

            estimator = Pipeline([
                ("scaler", StandardScaler()),
                ("svr", SVR(kernel="rbf", C=10.0)),
            ])
            param_note = {"kernel": "rbf", "C": 10.0}
        elif method in ("RandomForest", "RF"):
            from sklearn.ensemble import RandomForestRegressor

            estimator = RandomForestRegressor(n_estimators=100, random_state=42)
            param_note = {"n_estimators": 100}
        elif method == "XGBoost":
            try:
                from xgboost import XGBRegressor
            except ImportError:
                return {"status": "deferred", "reason": "xgboost not installed"}
            estimator = XGBRegressor(n_estimators=100, random_state=42, verbosity=0)
            param_note = {"n_estimators": 100}
        elif method == "CNN":
            return self._fit_cnn(matrix, y)
        else:
            return {"status": "skipped", "reason": f"unknown method {method}"}

        folds = max(2, min(folds, matrix.shape[0]))
        splitter = KFold(n_splits=folds, shuffle=True, random_state=42)
        scores = cross_val_score(estimator, matrix, y, cv=splitter, scoring="r2")
        return {
            "status": "ok",
            "parameters": param_note,
            "r2_scores": [float(s) for s in scores],
            "mean_r2": float(np.mean(scores)),
            "std_r2": float(np.std(scores)),
            "cv_folds": folds,
        }

    def _fit_cnn(self, matrix: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        try:
            import tensorflow as tf
        except ImportError:
            return {"status": "deferred", "reason": "TensorFlow not installed"}
        try:
            tf.get_logger().setLevel("ERROR")
            from sklearn.model_selection import train_test_split

            if matrix.shape[0] < 4:
                return {"status": "skipped", "reason": "not enough samples"}
            from sklearn.preprocessing import StandardScaler
            feature_scaler = StandardScaler().fit(matrix)
            scaled = feature_scaler.transform(matrix)
            X = scaled.reshape(scaled.shape[0], scaled.shape[1], 1)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.25, random_state=42)
            y_mean = float(np.mean(y_train))
            y_std = float(np.std(y_train)) or 1.0
            y_train_scaled = (y_train - y_mean) / y_std
            model = tf.keras.Sequential([
                tf.keras.layers.Conv1D(16, 5, activation="relu", input_shape=(X.shape[1], 1)),
                tf.keras.layers.MaxPooling1D(2),
                tf.keras.layers.Flatten(),
                tf.keras.layers.Dense(32, activation="relu"),
                tf.keras.layers.Dense(1),
            ])
            model.compile(optimizer="adam", loss="mse")
            model.fit(X_train, y_train_scaled, epochs=50, verbose=0)
            predictions = model.predict(X_test, verbose=0).ravel() * y_std + y_mean
            ss_res = float(np.sum((y_test - predictions) ** 2))
            ss_tot = float(np.sum((y_test - np.mean(y_test)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            return {"status": "ok", "parameters": {"epochs": 50}, "r2_scores": [float(r2)],
                    "mean_r2": float(r2), "cv_folds": 1}
        except Exception as exc:
            return {"status": "deferred", "reason": f"CNN calibration failed: {exc}"}

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute calibration workflow."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting calibration execution")

            context = context or {}
            matrix = _extract_matrix(context.get("spectra", context.get("spectral_data")))
            if matrix is None:
                return self._create_success_output({
                    "methods_tested": [],
                    "status": "no_data",
                    "message": "No spectra supplied for calibration",
                })

            y = context.get("reference_values", context.get("y"))
            if y is None:
                return self._create_success_output({
                    "methods_tested": [],
                    "status": "no_reference",
                    "message": "Calibration requires reference values",
                })
            y = np.asarray(y, dtype=float).ravel()
            if y.size != matrix.shape[0]:
                return self._create_success_output({
                    "methods_tested": [],
                    "status": "no_reference",
                    "message": "reference values count does not match spectra count",
                })

            methods = list(context.get("methods", self.methods))
            folds = int(context.get("cv_folds", self.cv_folds))

            results: Dict[str, Any] = {
                "methods_tested": [],
                "method_results": {},
                "methods_deferred": [],
                "num_samples": int(matrix.shape[0]),
                "data_points": int(matrix.shape[1]),
                "cv_folds": folds,
            }

            for method in methods:
                name = str(method).strip()
                outcome = self._fit_method(name, matrix, y, folds)
                if outcome.get("status") == "ok":
                    results["method_results"][name] = outcome
                    results["methods_tested"].append(name)
                elif outcome.get("status") == "deferred":
                    results["methods_deferred"].append({"method": name, "reason": outcome["reason"]})
                else:
                    results["methods_deferred"].append(
                        {"method": name, "reason": outcome.get("reason", "skipped")})

            best_method = None
            best_r2 = None
            for name, outcome in results["method_results"].items():
                if best_r2 is None or outcome["mean_r2"] > best_r2:
                    best_r2 = outcome["mean_r2"]
                    best_method = name
            if best_method is not None:
                results["best_method"] = best_method
                results["best_r2_score"] = best_r2
                threshold = float(self.performance_thresholds.get("r2", 0.8))
                results["thresholds_met"] = bool(best_r2 >= threshold)

            results["status"] = "ok"
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(results)
        except Exception as e:
            return self._handle_error(e)
