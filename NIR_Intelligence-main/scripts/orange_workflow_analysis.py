#!/usr/bin/env python3
"""Orange-workflow-equivalente Analyse der Tomaten-NIR-Daten (T4-T5).

Fuehrt die gestern vorgeschlagenen Orange-Workflow-Schritte als Skript aus:
Datenvorbereitung, Qualitaetsbewertung, Spektralanalyse, statistische
Modellierung (PCA, PLS, Clustering, ANOVA), neuronale Netze (CNN, MLP,
Autoencoder), XAI (SHAP), Kalibrierung (PLS, PCR), FAISS-Datenbankvergleich
und Berichterstellung.
"""

import json
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE, "data", "raw", "T4-T5_ALLE_mit_Brix_2_parsed.json")
OUT_DIR = os.path.join(BASE, "output", "orange_analysis")
IMG_DIR = os.path.join(OUT_DIR, "images")

os.makedirs(IMG_DIR, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy import stats
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score, silhouette_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering


def load_data():
    with open(RAW_FILE, encoding="utf-8") as f:
        d = json.load(f)
    spectra = d["spectra"]
    wl_cols = d["wavelength_columns"]
    wavelengths = np.array([int(c.split("_")[1]) for c in wl_cols])
    X = np.array([[s["spectra"][c] for c in wl_cols] for s in spectra], dtype=float)
    y = np.array([s["brix"] for s in spectra], dtype=float)
    return d, spectra, wl_cols, wavelengths, X, y


def savefig(fig, name):
    path = os.path.join(IMG_DIR, name)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] {name}")


def fmt(v):
    return f"{v:.4f}" if isinstance(v, (int, float, np.floating)) else str(v)


def main():
    report_lines = []
    results = {}

    def emit(text=""):
        report_lines.append(text)
        if text:
            print(text)

    print("== 1. Datenvorbereitung ==")
    d, spectra, wl_cols, wavelengths, X_raw, y = load_data()
    n_total = len(X_raw)

    overflow = (X_raw >= 2**31).any(axis=1)
    zero = (X_raw <= 0).any(axis=1)
    bad = overflow | zero
    X = X_raw[~bad]
    y = y[~bad]
    groups = [spectra[i]["messobjekt"] for i in range(n_total) if not bad[i]]
    tags = [spectra[i]["tag"] for i in range(n_total) if not bad[i]]
    n_clean = len(X)
    emit(f"Rohdaten: {n_total} Messungen, 18 Kanaele (410-940 nm)")
    emit(f"Entfernt (ADC-Ueberlauf >= 2^31): {int(overflow.sum())} Messungen (Kanaele F_535, R_610)")
    emit(f"Entfernt (Null-/Fehlwerte): {int(zero.sum())} Messungen (Kanaele I_645, K_900)")
    emit(f"Bereinigter Datensatz: {n_clean} Messungen von {len(set(groups))} Tomaten")
    results["datenvorbereitung"] = {
        "rohdaten": n_total,
        "entfernt_ueberlauf": int(overflow.sum()),
        "entfernt_null": int(zero.sum()),
        "bereinigt": n_clean,
    }

    # SNV-Normalisierung (Standard Normal Variate) pro Spektrum
    X_snv = (X - X.mean(axis=1, keepdims=True)) / X.std(axis=1, keepdims=True)
    emit(f"SNV-Normalisierung angewendet (Streuung/Streulicht-Effekte reduziert)")
    results["datenvorbereitung"]["snv"] = True

    print()
    print("== 2. Qualitaetsbewertung ==")
    # Rauschen: Standardabweichung der Wiederholungsmessungen pro Tomate und Kanal
    unique_groups = sorted(set(groups))
    noise_per_group = []
    for g in unique_groups:
        mask = np.array([gg == g for gg in groups])
        Xg = X[mask]
        noise_per_group.append(Xg.std(axis=0).mean() / max(Xg.mean(axis=0).mean(), 1e-9))
    noise_per_group = np.array(noise_per_group)
    # Drift: Trend der Gruppenmittelwerte ueber die Messreihenfolge (Counter)
    counters = [spectra[i]["counter"] for i in range(n_total) if not bad[i]]
    order = np.argsort(counters)
    mean_intensity = X[order].mean(axis=1)
    drift_slope = stats.linregress(np.arange(n_clean), mean_intensity).slope / max(
        mean_intensity.mean(), 1e-9
    )
    # SNR: Mittelwert / Std der Wiederholungen
    snr = X.mean(axis=0) / np.array(
        [X[np.array([gg == g for gg in groups])].std(axis=0) for g in unique_groups]
    ).mean(axis=0)
    noise_level = float(noise_per_group.mean())
    drift_level = float(abs(drift_slope))
    emit(f"Relatives Rauschen (Wiederholungen, CV): {fmt(noise_level)} (Schwelle 0.05)")
    emit(f"Relativer Drift (Trend ueber Messreihe): {fmt(drift_level)} (Schwelle 0.01)")
    emit(f"SNR Median: {fmt(np.median(snr))}, Minimum: {fmt(snr.min())}")
    q_score = float(np.clip(1 - noise_level / 0.05 * 0.5 - drift_level / 0.01 * 0.5, 0, 1))
    emit(f"Qualitaets-Score (Ampel): {fmt(q_score)} -> {'GRUEN' if q_score > 0.7 else 'GELB' if q_score > 0.4 else 'ROT'}")
    warnings = []
    if noise_level > 0.05:
        warnings.append(f"Rauschen {fmt(noise_level)} > Schwelle 0.05: Messzeit erhoehen, um SNR zu verbessern")
    if drift_level > 0.01:
        warnings.append(f"Drift {fmt(drift_level)} > Schwelle 0.01: Geraet neu kalibrieren bzw. Dunkelmessung wiederholen")
    results["qualitaet"] = {
        "rauschen_cv": noise_level,
        "drift_relativ": drift_level,
        "snr_median": float(np.median(snr)),
        "snr_min": float(snr.min()),
        "score": q_score,
        "ampel": "GRUEN" if q_score > 0.7 else "GELB" if q_score > 0.4 else "ROT",
    }

    # Shewhart-Kontrollkarte (Mittelwert +- 3 sigma) der Intensitaets-Mittelwerte
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(mean_intensity, lw=0.8, alpha=0.7, label="Mittelwert-Intensitaet")
    cl = mean_intensity.mean()
    sigma = mean_intensity.std()
    ax.axhline(cl, color="green", ls="--", lw=1, label=f"Mittelwert {cl:.0f}")
    ax.axhline(cl + 3 * sigma, color="red", ls=":", lw=1, label="+/- 3 sigma")
    ax.axhline(cl - 3 * sigma, color="red", ls=":", lw=1)
    out_of_ctrl = np.abs(mean_intensity - cl) > 3 * sigma
    ax.scatter(np.where(out_of_ctrl)[0], mean_intensity[out_of_ctrl], color="red", s=12, zorder=5, label="ausserhalb +-3 sigma")
    ax.set_xlabel("Messung (Reihenfolge)")
    ax.set_ylabel("Intensitaet (ADC)")
    ax.set_title("Shewhart-Kontrollkarte: Intensitaets-Mittelwerte")
    ax.legend(fontsize=7)
    savefig(fig, "02_shewhart_kontrollkarte.png")

    print()
    print("== 3. Spektralanalyse ==")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    step = max(len(X_snv) // 200, 1)
    for row in X_snv[::step]:
        ax.plot(wavelengths, row, lw=0.5, alpha=0.3, color="steelblue")
    ax.plot(wavelengths, X_snv.mean(axis=0), lw=2, color="crimson", label="Mittelwertsspektrum")
    for band in [435, 510, 645, 730, 900]:
        ax.axvline(band, color="gray", ls=":", lw=0.8)
    ax.set_xlabel("Wellenlaenge (nm)")
    ax.set_ylabel("Intensitaet (SNV-normalisiert)")
    ax.set_title("Rohspektren (SNV) mit typischen Absorptionsbanden")
    ax.legend()
    savefig(fig, "03_spektren.png")

    corr = np.array([np.corrcoef(X[:, i], y)[0, 1] for i in range(len(wavelengths))])
    best = np.argsort(-np.abs(corr))[:5]
    emit("Korrelation Kanal vs. Brix (Top 5): " + ", ".join(f"{wl_cols[i]} ({corr[i]:+.3f})" for i in best))
    results["spektralanalyse"] = {
        "korrelationen": {wl_cols[i]: float(corr[i]) for i in range(len(wavelengths))},
        "snr_median": float(np.median(snr)),
    }

    fig, ax = plt.subplots(figsize=(9, 4))
    colors = plt.cm.coolwarm((corr - corr.min()) / (corr.max() - corr.min() + 1e-12))
    ax.bar(range(len(wavelengths)), corr, color=colors)
    ax.set_xticks(range(len(wavelengths)))
    ax.set_xticklabels([str(w) for w in wavelengths], rotation=45, fontsize=7)
    ax.set_xlabel("Wellenlaenge (nm)")
    ax.set_ylabel("Pearson-Korrelation mit Brix")
    ax.set_title("Korrelation der Kanaele mit dem Brix-Referenzwert")
    savefig(fig, "03_korrelation_brix.png")

    # Vorbereitung modellierung: X standardisiert, y mitgefuehrt
    Xs = StandardScaler().fit_transform(X)

    print()
    print("== 4. Statistische Analyse (PCA, PLS, Cluster, ANOVA) ==")
    pca = PCA(n_components=10).fit(Xs)
    scores = pca.transform(Xs)
    evr = pca.explained_variance_ratio_
    emit(f"PCA: PC1 {evr[0] * 100:.1f}% | PC2 {evr[1] * 100:.1f}% | PC1-10 kumulativ {evr.sum() * 100:.1f}%")
    results["pca"] = {
        "erklaerte_varianz": [float(v) for v in evr],
        "kumulativ": float(evr.sum()),
    }

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    sc = axes[0].scatter(scores[:, 0], scores[:, 1], c=y, cmap="viridis", s=8)
    fig.colorbar(sc, ax=axes[0], label="Brix")
    axes[0].set_xlabel(f"PC1 ({evr[0] * 100:.1f}%)")
    axes[0].set_ylabel(f"PC2 ({evr[1] * 100:.1f}%)")
    axes[0].set_title("PCA Score-Plot")
    axes[1].plot(range(1, 11), np.cumsum(evr), "o-")
    axes[1].set_xlabel("Hauptkomponente")
    axes[1].set_ylabel("Kumulative Varianz (%)")
    axes[1].set_title("Scree-Plot")
    axes[2].plot(wavelengths, pca.components_[0], "o-", label="PC1", ms=3)
    axes[2].plot(wavelengths, pca.components_[1], "s-", label="PC2", ms=3)
    axes[2].set_xlabel("Wellenlaenge (nm)")
    axes[2].set_ylabel("Loading")
    axes[2].set_title("PCA Loadings")
    axes[2].legend()
    fig.tight_layout()
    savefig(fig, "04_pca.png")

    # PLS-Regression (10 Komponenten, 5-fold Kreuzvalidierung)
    pls = PLSRegression(n_components=10)
    y_pred_pls = cross_val_predict(pls, Xs, y, cv=KFold(5, shuffle=True, random_state=42))
    r2_pls = r2_score(y, y_pred_pls)
    rmse_pls = np.sqrt(mean_squared_error(y, y_pred_pls))
    emit(f"PLS (10 Komponenten, 5-fold CV): R2 = {fmt(r2_pls)}, RMSECV = {fmt(rmse_pls)}")
    results["pls_statistik"] = {"r2": r2_pls, "rmsecv": rmse_pls}

    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.scatter(y, y_pred_pls, s=10, alpha=0.5)
    lims = [y.min() - 0.2, y.max() + 0.2]
    ax.plot(lims, lims, "r--", lw=1)
    ax.set_xlabel("Brix (Referenz)")
    ax.set_ylabel("Brix (PLS-Vorhersage, CV)")
    ax.set_title(f"PLS: R2={r2_pls:.3f}, RMSECV={rmse_pls:.3f}")
    savefig(fig, "04_pls_cv.png")

    # Hierarchisches Clustering (Ward, euklidisch), Silhouette fuer 2-5 Cluster
    sil = {}
    for k in [2, 3, 4, 5]:
        labels_k = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Xs)
        sil[k] = float(silhouette_score(Xs, labels_k))
    best_k = max(sil, key=sil.get)
    labels = AgglomerativeClustering(n_clusters=best_k, linkage="ward").fit_predict(Xs)
    sizes = [int((labels == i).sum()) for i in range(best_k)]
    emit(f"Hierarchisches Clustering (Ward): bestes k={best_k}, Silhouette {fmt(sil[best_k])}, Cluster-Groessen {sizes}")
    emit("Silhouetten: " + ", ".join(f"k={k}: {v:.3f}" for k, v in sil.items()))
    results["clustering"] = {"silhouetten": sil, "bestes_k": best_k, "groessen": sizes, "silhouette_best": sil[best_k]}

    # ANOVA: Cluster-Labels vs. Brix (sind die Cluster im Brix unterschiedlich?)
    groups_y = [y[labels == i] for i in range(best_k)]
    f_stat, p_val = stats.f_oneway(*groups_y)
    emit(f"ANOVA (Cluster vs. Brix): F = {fmt(f_stat)}, p = {p_val:.2e}")
    results["anova_cluster"] = {"F": float(f_stat), "p": float(p_val)}

    fig, ax = plt.subplots(figsize=(5, 4.5))
    parts = ax.violinplot(groups_y, positions=range(1, best_k + 1), showmedians=True)
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Brix")
    ax.set_title(f"ANOVA: Brix pro Cluster (p={p_val:.1e})")
    savefig(fig, "04_anova_cluster.png")

    print()
    print("== 5. Neuronale Netze (MLP, CNN, Autoencoder) ==")
    # MLP (sklearn) mit 5-fold CV
    mlp = MLPRegressor(
        hidden_layer_sizes=(64, 32), max_iter=2000, early_stopping=True,
        random_state=42, activation="relu",
    )
    y_pred_mlp = cross_val_predict(mlp, Xs, y, cv=KFold(5, shuffle=True, random_state=42))
    r2_mlp = r2_score(y, y_pred_mlp)
    rmse_mlp = np.sqrt(mean_squared_error(y, y_pred_mlp))
    emit(f"MLP (64-32): R2 = {fmt(r2_mlp)}, RMSE = {fmt(rmse_mlp)}")

    # CNN (TensorFlow/Keras): 1D-Konvolution ueber dem Spektrum, 5-fold CV manuell
    import tensorflow as tf

    tf.get_logger().setLevel("ERROR")
    n_splits = 5
    y_pred_cnn = np.zeros_like(y)
    histories = []
    for fold, (tr, te) in enumerate(KFold(n_splits, shuffle=True, random_state=42).split(Xs)):
        tf.keras.utils.set_random_seed(42 + fold)
        model = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(18, 1)),
                tf.keras.layers.Conv1D(16, 3, activation="relu", padding="same"),
                tf.keras.layers.MaxPooling1D(2),
                tf.keras.layers.Conv1D(32, 3, activation="relu", padding="same"),
                tf.keras.layers.GlobalAveragePooling1D(),
                tf.keras.layers.Dense(32, activation="relu"),
                tf.keras.layers.Dense(1),
            ]
        )
        model.compile(optimizer="adam", loss="mse")
        h = model.fit(
            Xs[tr][..., None], y[tr], validation_split=0.2, epochs=60,
            batch_size=32, verbose=0,
        )
        histories.append(h.history)
        y_pred_cnn[te] = model.predict(Xs[te][..., None], verbose=0).ravel()
        tf.keras.backend.clear_session()
    r2_cnn = r2_score(y, y_pred_cnn)
    rmse_cnn = np.sqrt(mean_squared_error(y, y_pred_cnn))
    emit(f"CNN (1D-Conv, Keras): R2 = {fmt(r2_cnn)}, RMSE = {fmt(rmse_cnn)}")

    fig, ax = plt.subplots(figsize=(5, 4))
    for i, h in enumerate(histories):
        ax.plot(h["loss"], lw=1, alpha=0.7, label=f"Fold {i+1} Train")
        ax.plot(h["val_loss"], lw=1, ls="--", alpha=0.5)
    ax.set_xlabel("Epoche")
    ax.set_ylabel("MSE-Loss")
    ax.set_title("CNN: Loss-Kurven (Training vs. Validierung)")
    ax.legend(fontsize=7)
    savefig(fig, "05_cnn_loss.png")

    # Autoencoder zur Anomalieerkennung (Rekonstruktionsfehler)
    ae = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(18,)),
            tf.keras.layers.Dense(12, activation="relu"),
            tf.keras.layers.Dense(6, activation="relu"),
            tf.keras.layers.Dense(12, activation="relu"),
            tf.keras.layers.Dense(18),
        ]
    )
    ae.compile(optimizer="adam", loss="mse")
    tf.keras.utils.set_random_seed(42)
    ae.fit(Xs, Xs, epochs=100, batch_size=64, verbose=0)
    recon = ae.predict(Xs, verbose=0)
    recon_err = ((Xs - recon) ** 2).mean(axis=1)
    thr = np.percentile(recon_err, 95)
    anomalies = int((recon_err > thr).sum())
    emit(f"Autoencoder: {anomalies} Anomalien bei 95. Perzentil-Schwelle")
    tf.keras.backend.clear_session()

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.hist(recon_err, bins=50)
    ax.axvline(thr, color="red", ls="--", label=f"95%-Schwelle")
    ax.set_xlabel("Rekonstruktionsfehler (MSE)")
    ax.set_ylabel("Anzahl")
    ax.set_title("Autoencoder: Anomalieerkennung")
    ax.legend()
    savefig(fig, "05_autoencoder.png")

    results["modelle"] = {
        "pls": {"r2": r2_pls, "rmse": rmse_pls},
        "mlp": {"r2": r2_mlp, "rmse": rmse_mlp},
        "cnn": {"r2": r2_cnn, "rmse": rmse_cnn},
    }
    best_model = max(results["modelle"], key=lambda k: results["modelle"][k]["r2"])
    emit(f"Bester Vorhersage-Mix: {best_model.upper()} (R2 = {fmt(results['modelle'][best_model]['r2'])})")

    print()
    print("== 6. XAI: SHAP-Werte (Permutation) ==")
    # Permutationswichtigkeit als robuste, SHAP-analoge globale Erklaerung
    from sklearn.inspection import permutation_importance

    pls_full = PLSRegression(n_components=10).fit(Xs, y)
    perm = permutation_importance(pls_full, Xs, y, n_repeats=10, random_state=42, scoring="r2")
    imp = perm.importances_mean
    order = np.argsort(-imp)
    emit("Wichtigste Kanaele (Permutation, SHAP-analog): " + ", ".join(f"{wl_cols[i]} ({imp[i]:.4f})" for i in order[:5]))
    results["xai"] = {"permutation_importance": {wl_cols[i]: float(imp[i]) for i in order}}

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(range(len(imp)), imp[order], color="teal")
    ax.set_xticks(range(len(imp)))
    ax.set_xticklabels([wl_cols[i] for i in order], rotation=60, fontsize=7)
    ax.set_ylabel("Wichtigkeit (R2-Abfall bei Vertauschung)")
    ax.set_title("XAI: globale Kanalwichtigkeit (SHAP-analog)")
    savefig(fig, "06_xai_importance.png")

    print()
    print("== 7. Kalibrierung (PLS, PCR) ==")
    # RMSECV vs. Anzahl Komponenten
    comps = range(1, 11)
    rmsecv_pls = []
    for c in comps:
        yp = cross_val_predict(PLSRegression(n_components=c), Xs, y, cv=KFold(5, shuffle=True, random_state=42))
        rmsecv_pls.append(np.sqrt(mean_squared_error(y, yp)))
    best_c = int(np.argmin(rmsecv_pls)) + 1
    emit(f"PLS: beste Komponentenzahl = {best_c}, RMSECV = {fmt(min(rmsecv_pls))}")

    # PCR: PCA + lineare Regression
    rmsecv_pcr = []
    for c in comps:
        pc_scores = PCA(n_components=c).fit_transform(Xs)
        yp = cross_val_predict(LinearRegression(), pc_scores, y, cv=KFold(5, shuffle=True, random_state=42))
        rmsecv_pcr.append(np.sqrt(mean_squared_error(y, yp)))
    best_c_pcr = int(np.argmin(rmsecv_pcr)) + 1
    emit(f"PCR: beste Komponentenzahl = {best_c_pcr}, RMSECV = {fmt(min(rmsecv_pcr))}")
    results["kalibrierung"] = {
        "pls_rmsecv_komponenten": [float(v) for v in rmsecv_pls],
        "pls_beste_komponenten": best_c,
        "pcr_rmsecv_komponenten": [float(v) for v in rmsecv_pcr],
        "pcr_beste_komponenten": best_c_pcr,
        "bester_rmsecv": float(min(min(rmsecv_pls), min(rmsecv_pcr))),
    }

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(comps, rmsecv_pls, "o-", label="PLS")
    ax.plot(comps, rmsecv_pcr, "s--", label="PCR")
    ax.set_xlabel("Anzahl Komponenten")
    ax.set_ylabel("RMSECV (Brix)")
    ax.set_title("Kalibrierung: RMSECV vs. Komponenten")
    ax.legend()
    savefig(fig, "07_kalibrierung_pls_pcr.png")

    # Referenz vs. Vorhersage (bestes PLS)
    yp_best = cross_val_predict(PLSRegression(n_components=best_c), Xs, y, cv=KFold(5, shuffle=True, random_state=42))
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.scatter(y, yp_best, s=10, alpha=0.5)
    lims = [y.min() - 0.2, y.max() + 0.2]
    ax.plot(lims, lims, "r--", lw=1)
    r2b = r2_score(y, yp_best)
    ax.set_xlabel("Brix (Referenz)")
    ax.set_ylabel("Brix (Vorhersage, CV)")
    ax.set_title(f"Bestes PLS ({best_c} Komponenten): R2={r2b:.3f}")
    savefig(fig, "07_pls_best.png")

    print()
    print("== 8. FAISS-Datenbankvergleich ==")
    import faiss

    Xf = X_snv.astype("float32")
    index = faiss.IndexFlatL2(Xf.shape[1])
    index.add(Xf)
    query_idx = 0
    D, I = index.search(Xf[query_idx : query_idx + 1], 4)
    emit(f"FAISS-Index: {index.ntotal} Spektren (L2 auf SNV-Daten)")
    emit(f"Top-3 aehnlichste Spektren zu Messung {groups[query_idx]}: " + ", ".join(f"{groups[j]} (D={dk:.3f})" for j, dk in zip(I[0][1:], D[0][1:])))
    results["faiss"] = {
        "index_groesse": int(index.ntotal),
        "query": groups[query_idx],
        "top3": [{"messobjekt": groups[j], "distanz": float(dk)} for j, dk in zip(I[0][1:], D[0][1:])],
    }

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(wavelengths, X_snv[query_idx], lw=2, label=f"Abfrage: {groups[query_idx]}")
    for rank, (j, dk) in enumerate(zip(I[0][1:], D[0][1:]), 1):
        ax.plot(wavelengths, X_snv[j], lw=1, alpha=0.7, ls="--", label=f"#{rank} {groups[j]} (D={dk:.2f})")
    ax.set_xlabel("Wellenlaenge (nm)")
    ax.set_ylabel("Intensitaet (SNV)")
    ax.set_title("FAISS: Top-3 aehnlichste Spektren")
    ax.legend(fontsize=7)
    savefig(fig, "08_faiss_top3.png")

    print()
    print("== 9. Warnungen & Empfehlungen ==")
    for w in warnings:
        emit(f"WARNUNG: {w}")
    if not warnings:
        emit("Keine kritischen Warnungen (Rauschen und Drift unter den Schwellen).")
    emit(f"Empfehlung: Kalibrierungsmodell PLS mit {best_c} Komponenten weiterverwenden (RMSECV {fmt(min(rmsecv_pls))} Brix).")
    emit("Empfehlung: Die Kanaele R_610 und F_535 zeigen Ueberlaeufe: Geraet-Verstaerkung reduzieren oder Belichtungszeit senken.")
    emit("Empfehlung: Messzeit je Spektrum erhoehen bzw. mehr Wiederholungen mitteln, um SNR weiter zu verbessern.")
    results["warnungen"] = warnings

    # Gesamt-Uebersicht
    summary = {
        "datensaetze_roh": n_total,
        "datensaetze_bereinigt": n_clean,
        "qualitaets_score": q_score,
        "brix_bereich": [float(y.min()), float(y.max())],
        "bestes_modell": best_model.upper(),
        "modelle": results["modelle"],
        "beste_kalibrierung": {"verfahren": "PLS" if min(rmsecv_pls) <= min(rmsecv_pcr) else "PCR", "komponenten": best_c, "rmsecv": float(min(min(rmsecv_pls), min(rmsecv_pcr)))},
        "warnings": warnings,
    }
    results["zusammenfassung"] = summary

    with open(os.path.join(OUT_DIR, "orange_analysis_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nErgebnisse: {os.path.join(OUT_DIR, 'orange_analysis_results.json')}")

    # Markdown-Bericht
    md = []
    md.append("# Analyse der Tomaten-NIR-Daten (T4-T5) - Orange-Workflow als Skript\n")
    md.append(f"**Datenquelle:** `data/raw/T4-T5_ALLE_mit_Brix_2.txt` ({n_total} Messungen, 18 Kanaele, Geraet: Dpark fun NIR Triad)\n")
    md.append("## 1. Datenvorbereitung\n")
    md.append(f"- Rohdaten: **{n_total} Messungen** von {len(set(groups))} Tomaten, 18 Kanaele (410-940 nm)")
    md.append(f"- Entfernt: **{int(overflow.sum())} ADC-Ueberlaeufe** (>= 2^31, Kanaele F_535/R_610) und **{int(zero.sum())} Null-Messungen** (I_645/K_900)")
    md.append(f"- Bereinigt: **{n_clean} Messungen**; SNV-Normalisierung angewendet\n")
    md.append("## 2. Qualitaetsbewertung\n")
    md.append(f"- Rauschen (CV der Wiederholungen): **{fmt(noise_level)}** (Schwelle 0.05)")
    md.append(f"- Drift (relativer Trend): **{fmt(drift_level)}** (Schwelle 0.01)")
    md.append(f"- SNR: Median **{fmt(np.median(snr))}**, Min **{fmt(snr.min())}**")
    md.append(f"- Qualitaets-Score: **{fmt(q_score)}** ({results['qualitaet']['ampel']})\n")
    md.append("![Kontrollkarte](images/02_shewhart_kontrollkarte.png)\n")
    md.append("## 3. Spektralanalyse\n")
    md.append(f"- Korrelation mit Brix am staerksten: " + ", ".join(f"`{wl_cols[i]}` ({corr[i]:+.3f})" for i in best[:5]) + "\n")
    md.append("![Spektren](images/03_spektren.png)\n")
    md.append("![Korrelationen](images/03_korrelation_brix.png)\n")
    md.append("## 4. Statistische Analyse\n")
    md.append(f"- **PCA:** PC1 {evr[0]*100:.1f}%, PC2 {evr[1]*100:.1f}%, kumulativ (10 PCs) {evr.sum()*100:.1f}%")
    md.append(f"- **PLS (10 Komp., 5-fold CV):** R2 = {fmt(r2_pls)}, RMSECV = {fmt(rmse_pls)}")
    md.append(f"- **Clustering (Ward):** bestes k = {best_k}, Silhouette = {fmt(sil[best_k])}, Groessen = {sizes}")
    md.append(f"- **ANOVA (Cluster vs. Brix):** F = {fmt(f_stat)}, p = {p_val:.2e}\n")
    md.append("![PCA](images/04_pca.png)\n")
    md.append("![PLS CV](images/04_pls_cv.png)\n")
    md.append("![ANOVA](images/04_anova_cluster.png)\n")
    md.append("## 5. Neuronale Netze\n")
    md.append(f"- **MLP (64-32):** R2 = {fmt(r2_mlp)}, RMSE = {fmt(rmse_mlp)}")
    md.append(f"- **CNN (1D):** R2 = {fmt(r2_cnn)}, RMSE = {fmt(rmse_cnn)}")
    md.append(f"- **Autoencoder:** {anomalies} Anomalien (95. Perzentil-Schwelle)")
    md.append(f"- **Bester Vorhersager:** **{best_model.upper()}** (R2 = {fmt(results['modelle'][best_model]['r2'])})\n")
    md.append("![CNN Loss](images/05_cnn_loss.png)\n")
    md.append("![Autoencoder](images/05_autoencoder.png)\n")
    md.append("## 6. XAI\n")
    md.append(f"- Wichtigste Kanaele (Permutation, SHAP-analog): " + ", ".join(f"`{wl_cols[i]}` ({imp[i]:.4f})" for i in order[:5]) + "\n")
    md.append("![XAI](images/06_xai_importance.png)\n")
    md.append("## 7. Kalibrierung\n")
    md.append(f"- **PLS:** beste Komponentenzahl {best_c}, RMSECV = {fmt(min(rmsecv_pls))}")
    md.append(f"- **PCR:** beste Komponentenzahl {best_c_pcr}, RMSECV = {fmt(min(rmsecv_pcr))}\n")
    md.append("![Kalibrierung](images/07_kalibrierung_pls_pcr.png)\n")
    md.append("![Bestes PLS](images/07_pls_best.png)\n")
    md.append("## 8. FAISS-Datenbankvergleich\n")
    md.append(f"- Index: {index.ntotal} Spektren; Top-3 zur Abfrage `{groups[query_idx]}`: " + ", ".join(f"`{groups[j]}` (D={dk:.3f})" for j, dk in zip(I[0][1:], D[0][1:])) + "\n")
    md.append("![FAISS](images/08_faiss_top3.png)\n")
    md.append("## 9. Warnungen & Empfehlungen\n")
    if warnings:
        for w in warnings:
            md.append(f"- ⚠️ {w}")
    else:
        md.append("- Keine kritischen Warnungen (Rauschen und Drift unter den Schwellen).")
    md.append(f"- Empfehlung: PLS mit {best_c} Komponenten als Kalibrierungsmodell (RMSECV {fmt(min(rmsecv_pls))} Brix).")
    md.append("- Empfehlung: Verstaerkung/Belichtung an F_535 und R_610 reduzieren (Ueberlaeufe).")
    md.append("- Empfehlung: Mehr Wiederholungen je Tomate mitteln, um SNR zu verbessern.")
    md.append("\n## Gesamtuebersicht\n")
    md.append("| Kennzahl | Wert |")
    md.append("|---|---|")
    md.append(f"| Datensaetze (roh / bereinigt) | {n_total} / {n_clean} |")
    md.append(f"| Qualitaets-Score | {fmt(q_score)} ({results['qualitaet']['ampel']}) |")
    md.append(f"| Brix-Bereich | {y.min():.2f} - {y.max():.2f} |")
    md.append(f"| Bestes Modell | {best_model.upper()} (R2 {fmt(results['modelle'][best_model]['r2'])}) |")
    md.append(f"| Beste Kalibrierung | {'PLS' if min(rmsecv_pls) <= min(rmsecv_pcr) else 'PCR'}, {best_c} Komponenten, RMSECV {fmt(min(min(rmsecv_pls), min(rmsecv_pcr)))} |")

    with open(os.path.join(OUT_DIR, "ANALYSIS_REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Bericht: {os.path.join(OUT_DIR, 'ANALYSIS_REPORT.md')}")


if __name__ == "__main__":
    main()
