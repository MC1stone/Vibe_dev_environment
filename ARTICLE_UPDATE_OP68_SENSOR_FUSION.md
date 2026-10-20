# Artikel-Update OP68: Sensor-Analyse und Korrektur-Loop der Fusion

> Ergänzung zum konsolidierten Artikel-Stand (19 October 2026) für die
> Programm-Änderungen aus **OP68** (PR #201): Sensor-Analyse und -Vergleich
> in allen Details beim Merge, sensoragnostischer Dark/White-Referenzvertrag
> (>= 50 Wiederholungen), Gain-Kurven-Schätzung aus Referenzen, und der
> Korrektur-Loop, der bei Restheterogenität nicht abbricht, sondern auf
> Basis korrigierter Zahlen neu bewertet. Alle Texte sind fertig
> formuliert zum direkten Übernehmen in das Manuskript.
>
> **Ehrlichkeitsregel:** Die Zahlen aus dem Live-Befund (Tomaten-Quellen
> T4-T5 vs. CSV-Export) sind reale Messungen; die Verifikation der
> Programm-Verträge (Konfundierungs-Diagnose, Gain-Kurve-Verhalten)
> wurde zusätzlich mit synthetischen Quellen gerechnet (Testmatrix 44/44).

---

## 1. Fertige Manuskript-Ergänzungen (Englisch, zum Übernehmen)

### 1.1 §6.7 — nach dem Fusions-Absatz ergänzen (neuer Unterabschnitt)

> **Sensor-aware fusion: comparison, confounding diagnosis, and a
> reference-protocol contract.** Fusion across acquisition runs requires
> more than a significance test on residuals: it requires an explicit
> account of *why* sources differ. The fusion branch therefore extends
> the comparative calibration with a full sensor comparison of the two
> sources — per-channel medians and B/A ratios (colour-coded for review),
> per-source coefficients of variation, the difference of the
> channel-correlation structures as a sensor signature, and the count of
> channels whose value distributions differ significantly
> (Mann–Whitney, p < 0.001). Applied to the two real acquisition runs of
> the proof-of-concept sensor (2,014 and 1,506 cleaned rows, zero shared
> objects), the comparison localizes the heterogeneity precisely: ten of
> eighteen channels differ significantly, the B/A ratios are not a
> global factor but a channel-dependent pattern (from 1.91 at 560 nm
> down to 0.75 at 900 nm — the sources differ by gain *and* by spectral
> shape), and the correlation-structure difference peaks at the very
> channel that carries the Brix information (G_560, |Δ| = 0.64).
>
> The decisive diagnostic is the **confounding diagnosis**. Without
> shared measured objects, sensor gain and sample population are
> statistically confounded: the ratio spread between objects (IQR 2.2
> at G_560 for the real source pair) shows that the apparent "gain
> difference" is entangled with which fruits were measured — a gain
> curve estimated from such data alone would absorb sample effects and
> is therefore not trustworthy. The platform states this as a finding
> rather than papering over it. To make the gain curve estimable in a
> sensor-agnostic way, NIR-IP defines a **reference-measurement protocol
> contract** for fusion projects: each source declares dark and white
> reference measurements (metadata: reference type, artifact, and at
> least 50 repetitions) — no specific hardware is prescribed, because
> the contract is a measurement condition, not a device. From compliant
> references the platform estimates the sensor transfer function
> radiometrically — (raw − dark)/(white − dark) per channel, smoothed
> over the wavelength axis, with a confidence note derived from the
> repetition spread — and offers the resulting gain curve as an
> additional correction variant. Without compliant references the gain
> curve is honestly reported as not estimable, together with the
> protocol text; it is never simulated.
>
> **Correction loop.** When the significance test reports residual
> heterogeneity, the platform does not stop at the verdict. It computes
> correction variants — standard normal variate (SNV) and multiplicative
> scatter correction (MSC) always; the reference-based gain curve when
> the contract is met — re-runs the identical cross-validated PLS
> pipeline on the corrected data, and formulates a corrected verdict
> automatically. On the real source pair the loop produces a
> first-class methodological finding: SNV measurably improves the
> fusion (R²(CV) 0.545 → 0.646), yet the corrected fusion remains below
> the better single source (0.722), and the significance test on the
> corrected residuals becomes *stronger*, not weaker (Levene p < 0.001)
> — the heterogeneity does not live in the spectral offset and gain
> that SNV removes, but deeper in the acquisition conditions. The
> corrected verdict states exactly this: the recommendation is to
> calibrate per source, or to acquire the reference measurements the
> contract demands and repeat the fusion. Negative results remain
> first-class: the loop measures whether correction helps, it does not
> assume it.

### 1.2 Table 9 (neu) — Sensor comparison and correction loop on the real source pair

> Table 9. Sensor-aware fusion on the two real acquisition runs
> (T4-T5 vs. CSV export; identical PLS methodology: 10 components,
> 5-fold CV, seed 42; correction variants evaluated on the corrected
> data).
>
> | Variant | R²(CV) | RMSECV | Hit ±0.5 °Brix | Levene p | Welch p |
> |---|---|---|---|---|---|
> | Source A alone | 0.621 | 0.623 | 63 % | — | — |
> | Source B alone | 0.722 | 0.568 | 66 % | — | — |
> | Fusion, baseline (global z-score) | 0.545 | 0.724 | 51 % | 0.006 | <0.001 |
> | Fusion, SNV correction | 0.646 | 0.639 | 60 % | <0.001 | <0.001 |
> | Fusion, MSC (per source) | 0.453 | 0.794 | 50 % | 0.185 | <0.001 |
> | Fusion, MSC (shared anchor curve) | 0.472 | 0.780 | 48 % | <0.001 | <0.001 |
>
> Sensor comparison: 10/18 channels significantly different (p < 0.001);
> B/A channel ratios from 1.91 (G_560) to 0.75 (K_900); correlation-
> structure difference max |Δ| = 0.64 at G_560; object-level ratio
> spread (IQR) up to 2.2 at G_560 → sensor gain and sample population
> confounded; reference contract (dark/white, ≥ 50 repetitions) not
> met in either source → gain curve honestly reported as not estimable.

### 1.3 §7.3 Limitations — Satz ergänzen

> Fusion path: the sensor comparison, confounding diagnosis, and
> reference-protocol contract are implemented and verified on a real
> source pair, but the reference-based gain curve has not yet been
> exercised on a campaign that actually acquires dark/white references
> (≥ 50 repetitions) — the corrected-verdict machinery is in place, and
> its empirical validation on reference-equipped sources is a scheduled
> iteration of the loop.

### 1.4 §8 Roadmap — Satz ergänzen

> …; acquisition of dark/white reference measurements (≥ 50 repetitions
> per source, per the fusion reference contract) for the two tomato
> sources, to promote the gain-curve correction from contract-verified
> to empirically validated; …

### 1.5 Abstract — nach dem Federated-Satz ergänzen

> The fusion path is sensor-aware: a full source comparison with a
> confounding diagnosis separates sensor gain from sample effects, a
> sensor-agnostic reference-measurement contract (dark/white, ≥ 50
> repetitions) makes the inter-sensor gain curve estimable without
> prescribing hardware, and a correction loop re-evaluates fusion on
> corrected data — reporting on real data that spectral correction
> measurably improves a heterogeneous fusion yet cannot replace
> compliant reference measurements.

### 1.6 §3 Agent-Beschreibung — Sensor Quality Agent ergänzen

> Sensor quality agent. (…) For fusion projects the agent additionally
> contributes the source-pair sensor comparison and the reference-
> measurement compliance check (dark/white, ≥ 50 repetitions) to the
> fusion branch (Section 6.7).

---

## 2. Verifikation (Programm-Stand, PR #201)

- OP68-Matrix `tests/test_op68_fusion_sensor_correction.py`: **44/44 grün**
- Referenzverhalten identisch nachgerechnet in der KNIME-Referenz
  (`FUSION_ANALYSIS.md`, Abschnitt 2b): SNV 0.646 / MSC 0.453 / 0.472 —
  Plattform und externe Referenz liefern dieselbe Methodik und dasselbe
  Verdict-Muster (Beste Korrektur: SNV; bleibt unter Einzelquelle B).
- Regressionen: OP63 St3 37/37, OP63 St1+2 45/45, OP64 19/19,
  OP65 30/30, OP66 28/28 grün; `manage.py check` OK; CI erweitert.
- Live-Befunde (echte Daten) in Tabelle 9: siehe
  `knime/tomato_brix_reference/FUSION_ANALYSIS.md` (PR #200) und die
  Sensor-Analyse vom 2026-10-19 (Session-Verifikation).

## 3. Offene [ENTWURF]-Punkte (unverändert)

Die bestehenden Entwurfsmarken (E-Mail/Korrespondenz, CRediT,
Schwellen-Herleitungen, XAI-Zitate) bleiben unberührt. Neu offen aus
OP68: die empirische Validierung der Gain-Kurve an referenz-ausgestatteten
Quellen (siehe Roadmap-Satz 1.4).
