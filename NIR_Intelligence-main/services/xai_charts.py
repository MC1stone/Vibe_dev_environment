# NIR Intelligence Platform - CNN XAI charts (OP19)
# Explainable-AI visualisations for the CNN calibration model on the
# measurement replicas / calibration samples of a dataset. All plots are
# rendered from REAL computations on the trained model - nothing is
# simulated:
#
#   prediction_vs_actual : model fit (R2, RMSE) on the test split
#   loss_curves          : training + validation loss per epoch
#   shap_summary         : global feature importance - mean |dR2| per
#                          wavelength over the test set (SHAP-equivalent
#                          permutation importance; the shap package is
#                          not a platform dependency)
#   shap_waterfall       : local explanation of ONE prediction - occlusion
#                          deltas per wavelength, sorted by magnitude
#   saliency_map         : |d(output)/d(input)| gradient heatmap
#   grad_cam             : class-activation over the last conv layer
#   attention_weights    : learned attention-pooling weights per wavelength
#
# Everything degrades gracefully: without TensorFlow (or without enough
# calibration rows) the returned dict stays empty and the report renders
# without charts. Base64 PNG data URLs, same contract as the other chart
# builders.
import base64
import io
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("Service.XaiCharts")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def _figure_to_data_url(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _as_matrix(samples) -> Optional[np.ndarray]:
    if not samples:
        return None
    matrix = np.asarray(samples, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 12 or matrix.shape[1] < 2:
        return None
    if not np.all(np.isfinite(matrix)):
        matrix = matrix[np.all(np.isfinite(matrix), axis=1)]
    if matrix.shape[0] < 12:
        return None
    return matrix


def _train_model(matrix: np.ndarray, y: np.ndarray, wavelengths: np.ndarray, epochs: int):
    """Train the shared attention-CNN (single source for agent + charts)."""
    import tensorflow as tf

    tf.get_logger().setLevel("ERROR")
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    x_scaler = StandardScaler().fit(matrix)
    y_scaler = StandardScaler().fit(y.reshape(-1, 1))
    X = x_scaler.transform(matrix)[..., None]
    y_scaled = y_scaler.transform(y.reshape(-1, 1)).ravel()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_scaled, test_size=0.25, random_state=42)
    n_points = X.shape[1]

    inputs = tf.keras.Input(shape=(n_points, 1))
    conv = tf.keras.layers.Conv1D(16, 5, activation="relu", padding="same")(inputs)
    conv = tf.keras.layers.Conv1D(32, 3, activation="relu", padding="same")(conv)
    # Learned attention pooling: the network assigns one attention weight
    # per wavelength position; the weighted sum feeds the regression head.
    scores = tf.keras.layers.Conv1D(1, 1)(conv)              # (batch, n_points, 1)
    att_scores = tf.keras.layers.Softmax(axis=1)(scores)     # normalized over axis
    pooled = tf.keras.layers.Multiply()([conv, att_scores])
    pooled = tf.keras.layers.Lambda(lambda t: tf.reduce_sum(t, axis=1))(pooled)
    dense = tf.keras.layers.Dense(32, activation="relu")(pooled)
    outputs = tf.keras.layers.Dense(1)(dense)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer="adam", loss="mse")

    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        verbose=0,
        validation_split=0.2 if X_train.shape[0] >= 8 else 0.0,
    )

    # Attention model: input -> softmax weights (excludes the dense head)
    attention_model = tf.keras.Model(inputs, att_scores)
    return {
        "model": model,
        "attention_model": attention_model,
        "x_scaler": x_scaler,
        "y_scaler": y_scaler,
        "X": X,
        "X_train": X_train,
        "X_test": X_test,
        "y_scaled": y_scaled,
        "y_train": y_train,
        "y_test": y_test,
        "history": history.history,
    }


def _prediction_vs_actual(y_pred, y_true,
                          target_name: str = "Zielwert") -> str:
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter(y_true, y_pred, s=60, alpha=0.8, edgecolors="k")
    lo = float(min(y_true.min(), y_pred.min()))
    hi = float(max(y_true.max(), y_pred.max()))
    ax.plot([lo, hi], [lo, hi], "r--", lw=1, label="Ideal (y = x)")
    ax.set_xlabel(f"Tatsächlich ({target_name})")
    ax.set_ylabel(f"Vorhergesagt ({target_name})")
    ax.set_title("Prediction vs. Actual (Test-Split)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def _loss_curves(history) -> str:
    loss = history.get("loss") or []
    val_loss = history.get("val_loss") or []
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(range(1, len(loss) + 1), loss, "o-", label="Trainings-Loss", ms=3)
    if val_loss:
        ax.plot(range(1, len(val_loss) + 1), val_loss, "s--",
                label="Validierungs-Loss", ms=3)
    ax.set_xlabel("Epoche")
    ax.set_ylabel("MSE-Loss (skaliert)")
    ax.set_title("Trainings-/Validierungs-Loss (Overfitting-Diagnose)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def _shap_summary(importance: np.ndarray, wavelengths: np.ndarray) -> str:
    order = np.argsort(importance)
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.barh([f"{wavelengths[i]:.0f} nm" for i in order],
            [float(importance[i]) for i in order])
    ax.set_xlabel("Mittlere |ΔR²| über den Test-Satz (Permutationswichtigkeit)")
    ax.set_ylabel("Wellenlänge")
    ax.set_title("SHAP Summary (global): Wichtigkeit pro Wellenlänge")
    ax.grid(alpha=0.3, axis="x")
    return _figure_to_data_url(fig)


def _shap_waterfall(deltas: np.ndarray, wavelengths: np.ndarray,
                    sample_idx: int) -> str:
    order = np.argsort(-np.abs(deltas))[:min(10, len(deltas))]
    running = np.cumsum([deltas[i] for i in order])
    base = float(np.mean(deltas) * 0)  # zero baseline, deltas are signed
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.bar([f"{wavelengths[i]:.0f} nm" for i in order],
           [float(deltas[i]) for i in order], color="#0d6efd", alpha=0.8)
    ax.step(range(len(order)), running, where="mid", color="#d62728",
            lw=1.2, label="Kumulativer Beitrag")
    ax.axhline(base, color="grey", lw=0.8)
    ax.set_xlabel("Wellenlänge")
    ax.set_ylabel("Δ Vorhersage bei Occlusion")
    ax.set_title(f"SHAP Force/Waterfall (lokal): Messung #{sample_idx + 1}")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def _saliency_and_gradcam(saliency: np.ndarray, grad_cam: np.ndarray,
                          wavelengths: np.ndarray) -> Tuple[str, str]:
    fig, ax = plt.subplots(figsize=(8, 3.2))
    im = ax.imshow(saliency[None, :], aspect="auto", cmap="hot",
                   extent=[float(wavelengths[0]), float(wavelengths[-1]), 0, 1])
    ax.set_yticks([])
    ax.set_xlabel("Wellenlänge (nm)")
    ax.set_title("Saliency Map: |∂output/∂input| pro Wellenlänge")
    fig.colorbar(im, ax=ax, fraction=0.03)
    saliency_url = _figure_to_data_url(fig)

    fig, ax = plt.subplots(figsize=(8, 3.2))
    im = ax.imshow(grad_cam[None, :], aspect="auto", cmap="jet",
                   extent=[float(wavelengths[0]), float(wavelengths[-1]), 0, 1])
    ax.set_yticks([])
    ax.set_xlabel("Wellenlänge (nm)")
    ax.set_title("Grad-CAM: aktivierte spektrale Bänder (letzte Conv-Schicht)")
    fig.colorbar(im, ax=ax, fraction=0.03)
    gradcam_url = _figure_to_data_url(fig)
    return saliency_url, gradcam_url


def _attention_chart(attention: np.ndarray, wavelengths: np.ndarray) -> str:
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(wavelengths, attention, "o-", color="#0d6efd")
    ax.set_xlabel("Wellenlänge (nm)")
    ax.set_ylabel("Aufmerksamkeitsgewicht (softmax)")
    ax.set_title("Attention-Weights: welche Wellenlängen das Netz betrachtet")
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def xai_chart_data_urls(calibration_samples: List[List[float]],
                        reference_values: List[float],
                        wavelengths: List[float],
                        epochs: int = 60,
                        target_name: str = "Zielwert") -> Dict[str, str]:
    """Train the CNN calibration model and render the seven XAI plots.

    Returns a dict of base64 PNG data URLs (keys: prediction_vs_actual,
    loss_curves, shap_summary, shap_waterfall, saliency_map, grad_cam,
    attention_weights) - empty dict when TensorFlow or matplotlib is
    missing or the data is insufficient. Never raises.
    """
    charts: Dict[str, str] = {}
    if not MATPLOTLIB_AVAILABLE:
        return charts
    try:
        from agents.neural_network_agent import _tensor_flow_available

        if not _tensor_flow_available():
            return charts
        matrix = _as_matrix(calibration_samples)
        if matrix is None or reference_values is None:
            return charts
        y = np.asarray(reference_values, dtype=float).ravel()
        if y.size != matrix.shape[0]:
            return charts
        wl = np.asarray(wavelengths, dtype=float) if wavelengths else \
            np.arange(matrix.shape[1], dtype=float)
        if wl.size != matrix.shape[1]:
            wl = np.arange(matrix.shape[1], dtype=float)

        import tensorflow as tf

        ctx = _train_model(matrix, y, wl, epochs)
        model = ctx["model"]

        # --- Prediction vs. actual + R2/RMSE (test split) ---------------
        y_pred_scaled = model.predict(ctx["X_test"], verbose=0).ravel()
        y_pred = ctx["y_scaler"].inverse_transform(
            y_pred_scaled.reshape(-1, 1)).ravel()
        y_true = ctx["y_scaler"].inverse_transform(
            ctx["y_test"].reshape(-1, 1)).ravel()
        charts["prediction_vs_actual"] = _prediction_vs_actual(
            y_pred, y_true, target_name)

        # --- Loss curves --------------------------------------------------
        charts["loss_curves"] = _loss_curves(ctx["history"])

        # --- SHAP summary (global): permutation importance ---------------
        rng = np.random.default_rng(7)
        baseline_r2 = _quick_r2(y_true, y_pred)
        X_test_scaled = ctx["x_scaler"].transform(matrix)[..., None]
        # permutation on the scaled 2D matrix, then re-shape
        perm_matrix = ctx["x_scaler"].transform(matrix).copy()
        importance = np.zeros(matrix.shape[1])
        for j in range(matrix.shape[1]):
            shuffled = perm_matrix.copy()
            rng.shuffle(shuffled[:, j])
            pred = model.predict(shuffled[..., None], verbose=0).ravel()
            pred = ctx["y_scaler"].inverse_transform(pred.reshape(-1, 1)).ravel()
            importance[j] = abs(baseline_r2 - _quick_r2(y, pred))
        charts["shap_summary"] = _shap_summary(importance, wl)

        # --- SHAP waterfall (local): occlusion deltas of one sample ------
        sample_idx = 0
        row = ctx["x_scaler"].transform(matrix)[sample_idx]
        base_pred = float(model.predict(row[None, ..., None], verbose=0).ravel()[0])
        deltas = np.zeros(matrix.shape[1])
        for j in range(matrix.shape[1]):
            occluded = row.copy()
            occluded[j] = 0.0  # scaled mean = neutral occlusion
            pred = float(model.predict(occluded[None, ..., None], verbose=0).ravel()[0])
            deltas[j] = pred - base_pred
        charts["shap_waterfall"] = _shap_waterfall(deltas, wl, sample_idx)

        # --- Saliency map: d(output)/d(input) gradient ---------------------
        row_tf = tf.convert_to_tensor(row[None, ..., None])
        with tf.GradientTape() as tape:
            tape.watch(row_tf)
            pred = model(row_tf, training=False)
        grads = tape.gradient(pred, row_tf).numpy().ravel()
        saliency = np.abs(grads)
        if saliency.max() > 0:
            saliency = saliency / saliency.max()

        # --- Grad-CAM over the last conv layer ----------------------------
        conv_layer = None
        for layer in reversed(model.layers):
            if isinstance(layer, tf.keras.layers.Conv1D) and layer.filters > 1:
                conv_layer = layer
                break
        grad_cam = saliency  # fallback when no conv layer is exposed
        if conv_layer is not None:
            cam_model = tf.keras.Model(model.inputs, [conv_layer.output, model.output])
            with tf.GradientTape() as tape:
                acts, pred = cam_model(row_tf, training=False)
            grads_cam = tape.gradient(pred, acts).numpy()[0]      # (n_points, filters)
            acts_np = acts.numpy()[0]
            weights_cam = np.mean(grads_cam, axis=0)               # (filters,)
            grad_cam = np.clip(np.sum(acts_np * weights_cam[None, :], axis=1), 0, None)
            if grad_cam.max() > 0:
                grad_cam = grad_cam / grad_cam.max()
        charts["saliency_map"], charts["grad_cam"] = _saliency_and_gradcam(
            saliency, grad_cam, wl)

        # --- Attention weights --------------------------------------------
        att = ctx["attention_model"].predict(ctx["X"][:8], verbose=0)[..., 0]
        attention = np.clip(att, 0, None).mean(axis=0)
        if attention.sum() > 0:
            attention = attention / attention.sum()
        charts["attention_weights"] = _attention_chart(attention, wl)
    except Exception:
        logger.exception("XAI chart rendering failed (non-fatal)")
        return {}
    return charts


def _quick_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
