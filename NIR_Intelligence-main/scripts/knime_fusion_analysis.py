#!/usr/bin/env python3
"""Fusions-Analyse der beiden Tomaten-Brix-Quell DATENSAETZE (T4-T5 + CSV-Export).

Fuehrt die im Artikel (Abschnitt 6.7) beschriebene review-gesteuerte
Fusion als KNIME-Referenz aus: jede Quelle einzeln kalibrieren, dann den
kombinierten Datensatz, Signifikanztest (Levene auf Residualvarianz,
Welch auf Residualmittel) ob der Quellenunterschied die Kalibration
messbar schadet, Trefferquoten (+-0,5/+-1,0 Brix aus der Messaufloesung
0,1) sowie Vorhersage-vs-Messung-Streudiagramm als EIN Datensatz.

Aequivalente KNIME-Knotenkette pro Quelle und fusioniert:
  CSV Reader -> Rule-based Row Filter x2 -> Normalizer (Z-score)
  -> Concatenate (Joiner) -> X-Partitioner (5-fold, seed 42)
  -> PLS (10 Komp.) -> Numeric Scorer -> Bar Chart / Scatter Plot
Signifikanztest: R-Snippet (car::leveneTest) / t.test(var.equal=FALSE).
"""

import json
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_A = os.path.join(BASE, "data", "raw", "T4-T5_ALLE_mit_Brix_2.txt")
OUT_DIR = os.path.join(BASE, "output", "knime_fusion")
os.makedirs(OUT_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(BASE, "scripts"))
from knime_reference_validation import CHANNELS, clean_data, load_data  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.cross_decomposition import PLSRegression  # noqa: E402
from sklearn.metrics import mean_squared_error, r2_score  # noqa: E402
from sklearn.model_selection import KFold, cross_val_predict  # noqa: E402


def pls_cv(X, y, n_splits=5, seed=42):
    """X-Partitioner (5-fold) + PLS (10 Komp.) + Predictor + Scorer."""
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    pred = cross_val_predict(PLSRegression(n_components=10), X, y, cv=kf)
    resid = y - pred
    return {
        "n": len(y),
        "r2": float(r2_score(y, pred)),
        "rmsecv": float(np.sqrt(mean_squared_error(y, pred))),
        "rpd": float(np.std(y, ddof=1) / np.sqrt(mean_squared_error(y, pred))),
        "hit_05": float(np.mean(np.abs(resid) <= 0.5)),
        "hit_10": float(np.mean(np.abs(resid) <= 1.0)),
        "resid_var": float(np.var(resid, ddof=1)),
        "resid_mean": float(np.mean(resid)),
        "resid": resid,
        "pred": pred,
    }


def main():
    source_b = sys.argv[1] if len(sys.argv) > 1 else None
    if not source_b or not os.path.isfile(source_b):
        print("Aufruf: knime_fusion_analysis.py <pfad/zur/CSV-Quelle-B>")
        sys.exit(1)

    # Quelle A: T4-T5 (Plattform-Rohdaten)
    Xa_raw, ya_raw, ga_raw = load_data(SOURCE_A)
    Xa, ya, ga, *_ = clean_data(Xa_raw, ya_raw, ga_raw)

    # Quelle B: CSV-Export (identische Sensorik, anderer Erfassungslauf)
    Xb_raw, yb_raw, gb_raw = load_data(source_b)
    Xb, yb, gb, *_ = clean_data(Xb_raw, yb_raw, gb_raw)

    print(f"Quelle A (T4-T5): {len(Xa)} Zeilen, "
          f"{len(set(ga))} Messobjekte, Brix {ya.min():.2f}-{ya.max():.2f}")
    print(f"Quelle B (CSV)  : {len(Xb)} Zeilen, "
          f"{len(set(gb))} Messobjekte, Brix {yb.min():.2f}-{yb.max():.2f}")

    # Concatenate: beide Quellen als EIN Datensatz (Originale bleiben unberuehrt)
    Xf = np.vstack([Xa, Xb])
    yf = np.concatenate([ya, yb])
    src = np.array(["A"] * len(ya) + ["B"] * len(yb))
    mu, sd = Xf.mean(axis=0), Xf.std(axis=0, ddof=0)
    Xfz = (Xf - mu) / sd

    res_a = pls_cv((Xa - Xa.mean(axis=0)) / Xa.std(axis=0, ddof=0), ya)
    res_b = pls_cv((Xb - Xb.mean(axis=0)) / Xb.std(axis=0, ddof=0), yb)
    res_f = pls_cv(Xfz, yf)

    # Methodische Position 2: pro Quelle Z-normalisiert, dann konkateniert
    Xa_z = (Xa - Xa.mean(axis=0)) / Xa.std(axis=0, ddof=0)
    Xb_z = (Xb - Xb.mean(axis=0)) / Xb.std(axis=0, ddof=0)
    res_f_psn = pls_cv(np.vstack([Xa_z, Xb_z]), np.concatenate([ya, yb]))

    print(f"A allein : R2cv={res_a['r2']:.3f} RMSECV={res_a['rmsecv']:.3f} "
          f"RPD={res_a['rpd']:.2f}")
    print(f"B allein : R2cv={res_b['r2']:.3f} RMSECV={res_b['rmsecv']:.3f} "
          f"RPD={res_b['rpd']:.2f}")
    print(f"Fusion   : R2cv={res_f['r2']:.3f} RMSECV={res_f['rmsecv']:.3f} "
          f"RPD={res_f['rpd']:.2f} (n={res_f['n']})")
    print(f"Fusion (pro Quelle normalisiert): R2cv={res_f_psn['r2']:.3f} "
          f"RMSECV={res_f_psn['rmsecv']:.3f}")

    # Signifikanztest: schadet der Quellenunterschied messbar?
    # Residuen je Quelle aus der FUSIONSKalibration (gleiche Skala)
    kf = KFold(5, shuffle=True, random_state=42)
    pred_f = cross_val_predict(PLSRegression(n_components=10), Xfz, yf, cv=kf)
    resid_f = yf - pred_f
    lev = stats.levene(resid_f[src == "A"], resid_f[src == "B"])
    wel = stats.ttest_ind(resid_f[src == "A"], resid_f[src == "B"],
                          equal_var=False)
    print(f"Levene p={lev.pvalue:.3f}, Welch p={wel.pvalue:.3f}")

    results = {
        "quelle_a": {k: v for k, v in res_a.items() if k not in ("pred", "resid")},
        "quelle_b": {k: v for k, v in res_b.items() if k not in ("pred", "resid")},
        "fusion": {k: v for k, v in res_f.items() if k not in ("pred", "resid")},
        "fusion_pro_quelle_normalisiert": {
            k: v for k, v in res_f_psn.items() if k not in ("pred", "resid")},
        "signifikanztest": {
            "levene_p": float(lev.pvalue),
            "welch_p": float(wel.pvalue),
            "restheterogenitaet": bool(lev.pvalue < 0.05 or wel.pvalue < 0.05),
        },
        "fusion_gewinn_r2": res_f["r2"] - max(res_a["r2"], res_b["r2"]),
    }

    # Korrekturvarianten (Nutzeranforderung 2026-10-19): Brix bleibt Basis;
    # bei signifikanter Restheterogenitaet werden spektrale Korrekturen
    # angewendet und die Bewertung auf den korrigierten Zahlen erneut
    # vorgenommen - die Fusion wird nicht verworfen, bevor die Korrektur
    # gerechnet ist (Bounded Autonomy: vorschlagen, messen, ehrlich berichten).
    def _snv(X):
        mu = X.mean(axis=1, keepdims=True)
        sd = X.std(axis=1, ddof=1, keepdims=True)
        return (X - mu) / sd

    def _msc(X, ref=None):
        ref = ref if ref is not None else X.mean(axis=0)
        out = np.empty_like(X, dtype=float)
        for i in range(X.shape[0]):
            slope, intercept = np.polyfit(ref, X[i], 1)
            out[i] = (X[i] - intercept) / slope
        return out

    variants = {}
    Xsnv = _snv(np.vstack([Xa, Xb]))
    variants["snv"] = pls_cv((Xsnv - Xsnv.mean(0)) / Xsnv.std(0), yf)
    Xmsc = np.vstack([_msc(Xa), _msc(Xb)])
    variants["msc_pro_quelle"] = pls_cv(
        (Xmsc - Xmsc.mean(0)) / Xmsc.std(0), yf)
    ref_anchor = Xa.mean(axis=0)
    Xmsc_j = np.vstack([_msc(Xa, ref_anchor), _msc(Xb, ref_anchor)])
    variants["msc_anchor"] = pls_cv(
        (Xmsc_j - Xmsc_j.mean(0)) / Xmsc_j.std(0), yf)
    correction_variants = {}
    for vname, vres in variants.items():
        lev_v = stats.levene(vres["resid"][src == "A"],
                             vres["resid"][src == "B"])
        wel_v = stats.ttest_ind(vres["resid"][src == "A"],
                                vres["resid"][src == "B"],
                                equal_var=False)
        correction_variants[vname] = {
            k: v for k, v in vres.items()
            if k not in ("pred", "resid", "resid_var", "resid_mean")}
        correction_variants[vname].update({
            "levene_p": float(lev_v.pvalue),
            "welch_p": float(wel_v.pvalue),
        })
        print(f"Korrekturvariante {vname}: R2cv={vres['r2']:.3f} "
              f"RMSECV={vres['rmsecv']:.3f} "
              f"(Levene p={lev_v.pvalue:.3f}, Welch p={wel_v.pvalue:.3f})")
    best_single = max(res_a["r2"], res_b["r2"])
    best_variant = max(correction_variants.items(),
                       key=lambda kv: kv[1]["r2"])
    if best_variant[1]["r2"] > res_f["r2"]:
        verdict = (
            f"Die Korrektur ({best_variant[0]}) verbessert die Fusion "
            f"messbar (R2cv {res_f['r2']:.3f} -> {best_variant[1]['r2']:.3f}), "
            "bleibt aber " + ("unter der besten Einzelquelle "
                              f"({best_single:.3f}) - Empfehlung: pro Quelle "
                              "kalibrieren oder Anchor-Messung nachholen."
                              if best_variant[1]["r2"] < best_single else
                              "und erreicht die beste Einzelquelle "
                              "- Fusion ist eine Option.")) 
    else:
        verdict = ("Keine Korrekturvariante verbessert die Fusion - "
                   "Empfehlung unveraendert (pro Quelle kalibrieren, "
                   "Anchor-Messung nachholen).")
    results["korrekturvarianten"] = correction_variants
    results["korrektur_verdict"] = verdict
    print(f"Verdict: {verdict}")
    if (len(set(ga)) and len(set(gb))):
        overlap = set(map(str, set(ga))) & set(map(str, set(gb)))
        results["messobjekte"] = {
            "n_a": len(set(ga)), "n_b": len(set(gb)),
            "gemeinsam": len(overlap),
        }
        print(f"Messobjekte: A={len(set(ga))}, B={len(set(gb))}, "
              f"gemeinsam={len(overlap)}")

    # Trefferquoten aus der Messaufloesung 0,1
    print(f"Trefferquoten Fusion: +-0,5: {res_f['hit_05']*100:.1f} %, "
          f"+-1,0: {res_f['hit_10']*100:.1f} %")

    # Streudiagramm: Vorhersage vs. Messung als EIN Datensatz
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(yf[src == "A"], pred_f[src == "A"], s=8, alpha=0.5,
               color="#2b6cb0", label="Quelle A (T4-T5)")
    ax.scatter(yf[src == "B"], pred_f[src == "B"], s=8, alpha=0.5,
               color="#dd6b20", label="Quelle B (CSV)")
    lims = [min(yf) - 0.5, max(yf) + 0.5]
    ax.plot(lims, lims, "r--", linewidth=1)
    ax.set_xlabel("Brix (Referenz, Refraktometer)")
    ax.set_ylabel("Brix (Vorhersage, Fusion-PLS 5-fold CV)")
    ax.set_title(f"Fusion: R2cv={res_f['r2']:.3f}, RMSECV={res_f['rmsecv']:.3f}, "
                 f"+-0,5: {res_f['hit_05']*100:.0f} %")
    ax.legend()
    fig.savefig(os.path.join(OUT_DIR, "fusion_pred_vs_ref.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)

    # Balkendiagramm RMSE-Vergleich (analog Figure 17)
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["Quelle A", "Quelle B", "Fusion"]
    rmse = [res_a["rmsecv"], res_b["rmsecv"], res_f["rmsecv"]]
    ax.bar(labels, rmse, color=["#718096", "#a0aec0", "#2b6cb0"])
    for i, v in enumerate(rmse):
        ax.text(i, v + 0.01, f"{v:.3f}", ha="center")
    ax.set_ylabel("RMSECV (Brix)")
    ax.set_title("RMSE-Vergleich: Quellen einzeln vs. Fusion")
    fig.savefig(os.path.join(OUT_DIR, "fusion_rmse_comparison.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)

    with open(os.path.join(OUT_DIR, "knime_fusion_results.json"), "w",
              encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Ergebnisse: {OUT_DIR}/knime_fusion_results.json")


if __name__ == "__main__":
    main()
