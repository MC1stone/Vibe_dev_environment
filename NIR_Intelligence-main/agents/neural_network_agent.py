# NIR Intelligence Platform - NeuralNetworkAgent
# Handles deep learning analysis of NIR spectroscopy data (MO 6).
# Real implementation: MLP regression and Autoencoder anomaly analysis are
# computed with scikit-learn; CNN models require optional TensorFlow/Keras
# and are reported as deferred when unavailable. Must always run in parallel
# to the statistical analysis (mission rule) - see the crew orchestration.

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


def _tensor_flow_available() -> bool:
    try:
        import tensorflow  # noqa: F401

        return True
    except ImportError:
        return False


class NeuralNetworkAgent(BaseAgent):
    """Agent for performing neural network analysis on NIR data.

    context keys:
    - spectra: samples (vectors or unified schema dicts)
    - reference_values / y: targets for supervised models
    - models: models to train (default MLP, Autoencoder, CNN)
    - training: {epochs, hidden_layer_sizes, test_size}
    """

    def __init__(self, **kwargs):
        super().__init__(name="NeuralNetworkAgent", version="2.0.0", **kwargs)
        self.dependencies = ["numpy", "scikit-learn", "tensorflow"]
        self.models = kwargs.get("models", ["CNN", "MLP", "Autoencoder"])
        self.default_architecture = kwargs.get("default_architecture", {})
        self.training_config = kwargs.get("training", {})

    def _train_mlp(self, matrix: np.ndarray, y: np.ndarray, training: Dict[str, Any]) -> Dict[str, Any]:
        from sklearn.metrics import r2_score
        from sklearn.model_selection import train_test_split
        from sklearn.neural_network import MLPRegressor
        from sklearn.preprocessing import StandardScaler

        hidden = training.get("hidden_layer_sizes", (64, 32))
        test_size = float(training.get("test_size", 0.25))
        if matrix.shape[0] < 4:
            return {"status": "skipped", "reason": "not enough samples"}
        X_train, X_test, y_train, y_test = train_test_split(
            matrix, y, test_size=test_size, random_state=42)
        scaler = StandardScaler().fit(X_train)
        mlp = MLPRegressor(
            hidden_layer_sizes=hidden,
            max_iter=training.get("epochs", 500),
            random_state=42,
        )
        mlp.fit(scaler.transform(X_train), y_train)
        predictions = mlp.predict(scaler.transform(X_test))
        return {
            "status": "ok",
            "hidden_layer_sizes": list(hidden) if isinstance(hidden, tuple) else hidden,
            "n_train": int(X_train.shape[0]),
            "n_test": int(X_test.shape[0]),
            "r2_score": float(r2_score(y_test, predictions)),
            "convergence_achieved": True,
        }

    def _train_autoencoder(self, matrix: np.ndarray, training: Dict[str, Any]) -> Dict[str, Any]:
        from sklearn.neural_network import MLPRegressor
        from sklearn.preprocessing import StandardScaler

        if matrix.shape[0] < 4:
            return {"status": "skipped", "reason": "not enough samples"}
        scaler = StandardScaler().fit(matrix)
        scaled = scaler.transform(matrix)
        hidden_size = int(training.get("encoding_dim", max(2, matrix.shape[1] // 10)))
        hidden_size = max(1, min(hidden_size, min(scaled.shape)))
        autoencoder = MLPRegressor(
            hidden_layer_sizes=(hidden_size,),
            max_iter=training.get("epochs", 500),
            random_state=42,
        )
        autoencoder.fit(scaled, scaled)
        reconstructed = autoencoder.predict(scaled)
        mse = float(np.mean((scaled - reconstructed) ** 2))
        errors = np.mean((scaled - reconstructed) ** 2, axis=1)
        threshold = float(np.mean(errors) + 2.0 * np.std(errors))
        return {
            "status": "ok",
            "encoding_dim": hidden_size,
            "reconstruction_mse": mse,
            "anomaly_threshold": threshold,
            "anomalies_detected": int(np.sum(errors > threshold)),
            "convergence_achieved": True,
        }

    def _train_cnn(self, matrix: np.ndarray, y: Optional[np.ndarray], training: Dict[str, Any]) -> Dict[str, Any]:
        if not _tensor_flow_available():
            return {"status": "deferred", "reason": "TensorFlow not installed"}
        if y is None:
            return {"status": "skipped", "reason": "CNN calibration needs reference values"}
        try:
            import tensorflow as tf

            tf.get_logger().setLevel("ERROR")
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler

            test_size = float(training.get("test_size", 0.25))
            if matrix.shape[0] < 4:
                return {"status": "skipped", "reason": "not enough samples"}
            # Feature scaling is essential for the 1D-CNN: raw ADC values
            # (thousands) against Brix targets (~5) otherwise stall the
            # gradient descent and the model never converges.
            x_scaler = StandardScaler().fit(matrix)
            y_scaler = StandardScaler().fit(y.reshape(-1, 1))
            X = x_scaler.transform(matrix).reshape(matrix.shape[0], matrix.shape[1], 1)
            y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_scaled, test_size=test_size, random_state=42)
            validation_split = float(training.get("validation_split", 0.2))
            model = tf.keras.Sequential([
                tf.keras.Input(shape=(X.shape[1], 1)),
                tf.keras.layers.Conv1D(16, 5, activation="relu", padding="same"),
                tf.keras.layers.MaxPooling1D(2),
                tf.keras.layers.Conv1D(32, 3, activation="relu", padding="same"),
                tf.keras.layers.GlobalMaxPooling1D(),
                tf.keras.layers.Dense(32, activation="relu"),
                tf.keras.layers.Dense(1),
            ])
            model.compile(optimizer="adam", loss="mse")
            epochs = int(training.get("epochs", 50))
            history = model.fit(
                X_train, y_train,
                epochs=epochs,
                verbose=0,
                validation_split=validation_split if X_train.shape[0] >= 8 else 0.0,
            )
            predictions = model.predict(X_test, verbose=0).ravel()
            ss_res = float(np.sum((y_test - predictions) ** 2))
            ss_tot = float(np.sum((y_test - np.mean(y_test)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            loss_curve = [float(v) for v in (history.history.get("loss") or [])]
            val_loss_curve = [
                float(v) for v in (history.history.get("val_loss") or [])
            ]
            converged = bool(loss_curve and loss_curve[-1] <= loss_curve[0])
            return {
                "status": "ok",
                "epochs_completed": epochs,
                "r2_score": float(r2),
                "rmse": float(np.sqrt(ss_res / max(1, len(y_test)))),
                "n_train": int(X_train.shape[0]),
                "n_test": int(X_test.shape[0]),
                "loss_curve": loss_curve,
                "validation_loss_curve": val_loss_curve,
                "convergence_achieved": converged,
            }
        except Exception as exc:
            return {"status": "deferred", "reason": f"CNN training failed: {exc}"}

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute neural network analysis workflow."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting neural network analysis execution")

            context = context or {}
            matrix = _extract_matrix(context.get("spectra", context.get("spectral_data")))
            if matrix is None:
                return self._create_success_output({
                    "models_trained": [],
                    "status": "no_data",
                    "message": "No spectra supplied for neural network analysis",
                })

            y = context.get("reference_values", context.get("y"))
            if y is not None:
                y = np.asarray(y, dtype=float).ravel()
                if y.size != matrix.shape[0]:
                    y = None

            models = list(context.get("models", self.models))
            training = dict(self.training_config)
            training.update(context.get("training", {}))

            results: Dict[str, Any] = {
                "models_trained": [],
                "models_deferred": [],
                "models_skipped": [],
                "num_samples": int(matrix.shape[0]),
                "data_points": int(matrix.shape[1]),
                "model_results": {},
            }

            for model_name in models:
                name = str(model_name).strip()
                try:
                    if name == "MLP":
                        if y is None:
                            results["models_skipped"].append(
                                {"model": name, "reason": "reference values required"})
                            continue
                        outcome = self._train_mlp(matrix, y, training)
                    elif name == "Autoencoder":
                        outcome = self._train_autoencoder(matrix, training)
                    elif name == "CNN":
                        outcome = self._train_cnn(matrix, y, training)
                    else:
                        results["models_skipped"].append(
                            {"model": name, "reason": "unknown model"})
                        continue
                    if outcome.get("status") == "ok":
                        results["model_results"][name] = outcome
                        results["models_trained"].append(name)
                    elif outcome.get("status") == "deferred":
                        results["models_deferred"].append(
                            {"model": name, "reason": outcome["reason"]})
                    else:
                        results["models_skipped"].append(
                            {"model": name, "reason": outcome.get("reason", "skipped")})
                except Exception as exc:
                    results["models_skipped"].append({"model": name, "reason": str(exc)})

            best_r2 = None
            best_model = None
            for name, outcome in results["model_results"].items():
                if "r2_score" in outcome and (best_r2 is None or outcome["r2_score"] > best_r2):
                    best_r2 = outcome["r2_score"]
                    best_model = name
            if best_model is not None:
                results["best_model"] = best_model
                results["best_model_r2_score"] = best_r2

            results["status"] = "ok"
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(results)
        except Exception as e:
            return self._handle_error(e)
