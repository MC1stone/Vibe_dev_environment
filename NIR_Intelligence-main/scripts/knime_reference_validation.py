#!/usr/bin/env python3
"""KNIME-Referenz-Auswertung der Tomaten-NIR-Daten (T4-T5).

Reproduziert die Knotenkette des KNIME-Workflows
`knime/tomato_brix_reference/` als ausfuehrbares Skript und erzeugt die
Kennzahlen, die als Beleg der Auswertungsqualitaet gegen die Artikel- und
Plattform-Zahlen (PLS R2cv 0.622 Orange vs. 0.626 Plattform, PCR 0.613,
Replikatstruktur, ADC-Saettigung F_535/R_610) geprueft werden.

Workflow-Aequivalenz (KNIME-Knoten -> Skript-Schritt):
  CSV Reader                 -> load_data()
  Rule-based Row Filter x2   -> clean_data() (ADC-Ueberlauf >= 2^31, <= 0)
  Normalizer (Z-score)       -> standardize()
  GroupBy                    -> replicate_structure()
  X-Partitioner (5-fold)     -> KFold(n_splits=5, shuffle, seed=42)
  Linear Regression          -> OLS
  PCA + Linear Regression    -> PCR (10 Komponenten)
  Numeric Scorer / X-Agg     -> r2_score / RMSE
  (PLS als Artikel-Benchmark, sklearn cross_val_predict)
"""

import json
import os

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE, "data", "raw", "T4-T5_ALLE_mit_Brix_2.txt")
OUT_DIR = os.path.join(BASE, "output", "knime_reference")
os.makedirs(OUT_DIR, exist_ok=True)

CHANNELS = [
    "A_410", "B_435", "C_460", "D_485", "E_510", "F_535", "G_560",
    "H_585", "R_610", "I_645", "S_680", "J_705", "T_730", "U_760",
    "V_810", "W_860", "K_900", "L_940",
]

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.cross_decomposition import PLSRegression  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.linear_model import LinearRegression  # noqa: E402
from sklearn.metrics import mean_squared_error, r2_score  # noqa: E402
from sklearn.model_selection import GroupKFold, KFold, cross_val_predict  # noqa: E402


def load_data(path=None):
    """CSV Reader (dateiagnostisch): Header-Zeile enthaelt 'Brix' und Kanalspalten."""
    with open(path or RAW_FILE, encoding="utf-8") as f:
        lines = f.read().splitlines()
    header_idx = next(i for i, l in enumerate(lines) if "Brix" in l and ";" in l)
    header = [h.strip() for h in lines[header_idx].split(";")]
    rows = []
    for line in lines[header_idx + 1:]:
        if not line.strip():
            continue
        rows.append(line.split(";"))
    data = [dict(zip(header, r)) for r in rows]
    def _val(d, c):
        v = d.get(c, "")
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    data = [d for d in data if _val(d, "Brix") is not None
            and all(_val(d, c) is not None for c in CHANNELS)]
    X = np.array([[_val(d, c) for c in CHANNELS] for d in data])
    y = np.array([_val(d, "Brix") for d in data])
    groups = [d["Messobjekt"] for d in data]
    return X, y, groups


def clean_data(X, y, groups):
    """Rule-based Row Filter: ADC-Ueberlauf (>= 2^31) und Null-/Fehlwerte."""
    overflow = (X >= 2 ** 31).any(axis=1)
    zero = (X <= 0).any(axis=1)
    bad = overflow | zero
    keep = ~bad
    return (X[keep], y[keep], [g for i, g in enumerate(groups) if keep[i]],
            int(overflow.sum()), int(zero.sum()),
            int((overflow & ~zero).sum()))


def standardize(X):
    """Normalizer (Z-score, spaltenweise) auf allen 18 Kanaelen."""
    mu = X.mean(axis=0)
    sd = X.std(axis=0, ddof=0)
    return (X - mu) / sd, mu, sd


def cv_metrics(X, y, model, n_splits=5, seed=42):
    """X-Partitioner (5-fold, shuffle, seed) + Learner + Predictor + Scorer."""
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    pred = cross_val_predict(model, X, y, cv=kf)
    return {
        "r2": float(r2_score(y, pred)),
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
        "pred": pred.tolist(),
    }


def group_cv_metrics(X, y, groups, model, n_splits=5):
    """Gruppenweise Kreuzvalidierung (GroupKFold nach Messobjekt)."""
    gkf = GroupKFold(n_splits=n_splits)
    pred = cross_val_predict(model, X, y, cv=gkf, groups=np.array(groups))
    return {
        "r2": float(r2_score(y, pred)),
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
    }


def permutation_importance_top(X, y, model, n_rep=10, seed=42):
    rng = np.random.default_rng(seed)
    base = r2_score(y, cross_val_predict(
        model, X, y, cv=KFold(5, shuffle=True, random_state=seed)))
    scores = {}
    for j, c in enumerate(CHANNELS):
        drops = []
        for _ in range(n_rep):
            Xp = X.copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            drops.append(base - r2_score(y, cross_val_predict(
                model, Xp, y, cv=KFold(5, shuffle=True, random_state=seed))))
        scores[c] = float(np.mean(drops))
    return sorted(scores.items(), key=lambda kv: -kv[1])[:5]


def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    results = {}
    X_raw, y_raw, groups_raw = load_data(path)
    X, y, groups, n_over, n_zero, n_over_only = clean_data(
        X_raw, y_raw, groups_raw)

    results["datenimport"] = {
        "rohdaten": len(X_raw),
        "entfernt_adc_ueberlauf": n_over,
        "entfernt_nullwerte": n_zero,
        "bereinigt": len(X),
    }
    print(f"Rohdaten: {len(X_raw)}, bereinigt: {len(X)} "
          f"(Ueberlauf {n_over}, Null {n_zero})")

    # Saettigungs-/Problemkanäle (Qualitaetsgate des Artikels)
    sat = {c: int((X_raw[:, i] >= 2 ** 31).sum())
           for i, c in enumerate(CHANNELS)}
    sat = {c: v for c, v in sat.items() if v > 0}
    results["saturierte_kanaele"] = sat
    print(f"ADC-Saettigung pro Kanal: {sat}")

    # Normalizer (Z-score)
    Xz, mu, sd = standardize(X)

    # GroupBy: Replikatstruktur
    uniq_brix = sorted(set(round(v, 2) for v in y))
    uniq_obj = sorted(set(groups))
    results["replikatstruktur"] = {
        "zeilen": len(X),
        "unique_brix": len(uniq_brix),
        "unique_messobjekte": len(uniq_obj),
        "replikate_pro_objekt_mittel": round(len(X) / len(uniq_obj), 2),
    }
    print(f"Replikatstruktur: {len(uniq_brix)} eindeutige Brix-Werte, "
          f"{len(uniq_obj)} Messobjekte")

    # Linear Regression (OLS) auf 18 z-standardisierten Kanaelen, 5-fold CV
    ols = cv_metrics(Xz, y, LinearRegression())
    results["ols_cv"] = {"r2": ols["r2"], "rmse": ols["rmse"]}
    print(f"OLS (KNIME Linear Regression), 5-fold CV: "
          f"R2={ols['r2']:.3f}, RMSE={ols['rmse']:.3f}")

    # PCR: PCA (10 Komp.) + Linear Regression, 5-fold CV
    kf = KFold(5, shuffle=True, random_state=42)
    pred_pcr = np.zeros_like(y)
    for tr, te in kf.split(Xz):
        pca = PCA(n_components=10).fit(Xz[tr])
        m = LinearRegression().fit(pca.transform(Xz[tr]), y[tr])
        pred_pcr[te] = m.predict(pca.transform(Xz[te]))
    results["pcr_cv"] = {
        "r2": float(r2_score(y, pred_pcr)),
        "rmse": float(np.sqrt(mean_squared_error(y, pred_pcr))),
        "komponenten": 10,
    }
    print(f"PCR (PCA 10 + OLS), 5-fold CV: R2={results['pcr_cv']['r2']:.3f}, "
          f"RMSE={results['pcr_cv']['rmse']:.3f}")

    # PLS (10 Komp.) als Artikel-Benchmark, 5-fold CV
    pls = cv_metrics(Xz, y, PLSRegression(n_components=10))
    results["pls_cv"] = {"r2": pls["r2"], "rmse": pls["rmse"],
                         "komponenten": 10}
    print(f"PLS (10 Komp.), 5-fold CV: R2={pls['r2']:.3f}, RMSE={pls['rmse']:.3f}")

    # RPD (SD der Referenz / RMSECV)
    sd_ref = float(np.std(y, ddof=1))
    results["rpd"] = {
        "sd_brix": sd_ref,
        "rpd_pls": sd_ref / pls["rmse"],
        "rpd_pcr": sd_ref / results["pcr_cv"]["rmse"],
    }
    print(f"SD(Brix)={sd_ref:.3f}, RPD(PLS)={results['rpd']['rpd_pls']:.2f}")

    # Gruppenweise CV (nach Messobjekt) — offener Punkt des Artikels [ENTWURF]
    results["pls_group_cv"] = group_cv_metrics(
        Xz, y, groups, PLSRegression(n_components=10))
    results["ols_group_cv"] = group_cv_metrics(Xz, y, groups, LinearRegression())
    # PCR gruppenweise (PCA innerhalb der Folds):
    gkf = GroupKFold(5)
    gp = np.array(groups)
    pred_gpcr = np.zeros_like(y)
    for tr, te in gkf.split(Xz, y, gp):
        pca = PCA(n_components=10).fit(Xz[tr])
        m = LinearRegression().fit(pca.transform(Xz[tr]), y[tr])
        pred_gpcr[te] = m.predict(pca.transform(Xz[te]))
    results["pcr_group_cv"] = {
        "r2": float(r2_score(y, pred_gpcr)),
        "rmse": float(np.sqrt(mean_squared_error(y, pred_gpcr))),
    }
    print(f"Gruppenweise CV (PLS): R2={results['pls_group_cv']['r2']:.3f}, "
          f"RMSE={results['pls_group_cv']['rmse']:.3f}")

    # Permutationswichtigkeit (Top-5 Kanaele) am PLS
    top = permutation_importance_top(Xz, y, PLSRegression(n_components=10))
    results["permutationswichtigkeit_top5"] = dict(top)
    print(f"Permutationswichtigkeit Top-5: {top}")

    # Streudiagramm: Vorhersage vs. Referenz (PLS, 5-fold CV)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(y, np.array(pls["pred"]), s=8, alpha=0.5, color="#2b6cb0")
    lims = [min(y) - 0.5, max(y) + 0.5]
    ax.plot(lims, lims, "r--", linewidth=1)
    ax.set_xlabel("Brix (Referenz, Refraktometer)")
    ax.set_ylabel("Brix (Vorhersage, PLS 5-fold CV)")
    ax.set_title(f"KNIME-Referenz: PLS CV R2={pls['r2']:.3f}, "
                 f"RMSECV={pls['rmse']:.3f}")
    fig.savefig(os.path.join(OUT_DIR, "pls_pred_vs_ref.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)

    with open(os.path.join(OUT_DIR, "knime_reference_results.json"), "w",
              encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Ergebnisse: {OUT_DIR}/knime_reference_results.json")


if __name__ == "__main__":
    main()
