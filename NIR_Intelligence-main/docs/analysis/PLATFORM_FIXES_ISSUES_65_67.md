# Plattform-Fixes aus dem Orange-Vergleich (Issues #65–#67)

**Datum:** 2026-09-24 · **Branch:** `vibe/orange-workflow-tomato-df558d` (PR #64)
**Ausgangslage:** [PLATFORM_VS_ORANGE_COMPARISON.md](PLATFORM_VS_ORANGE_COMPARISON.md) – derselbe Tomatendatensatz (`data/raw/T4-T5_ALLE_mit_Brix_2.txt`, 2014 bereinigte Messungen, 18 Kanäle) lieferte in Orange PLS R² = +0.62, in der Plattform dagegen R² = −1.83, MLP R² ≈ 0.001 und einen ohnmächtigen Kalibrations-Agenten (`no_reference`).

---

## Issue #65 – PLS/PCR ohne Feature-Scaling und ohne geschshufflede KFold

**Dateien:** `agents/statistical_analysis_agent.py`, `agents/calibration_agent.py`

**Ursache (zweiteilig):**

1. PLS/PCR erhielten die Roh-ADC-Werte (Tausender-Bereich) ohne Standardisierung – OP18 hatte das nur für den CNN-Agenten behoben.
2. Tiefere Ursache, die sich erst nach der Skalierung zeigte: `cross_val_score(..., cv=5)` nutzt **KFold ohne Shuffle**. Die Kalibrationszeilen sind nach Messobjekt sortiert (Brix-Blöcke wie `[6.3, 6.3, …]`), d. h. jeder Fold sieht nur einen schmalen Brix-Bereich → negativer R² **unabhängig von der Skalierung** (gemessen: mit Skalierung, ohne Shuffle weiterhin −1.38).

**Fix:**

- `StandardScaler` in einer `Pipeline` vor PLS/PCR (beide Agenten)
- `KFold(n_splits=folds, shuffle=True, random_state=42)` statt Integer-`cv` (beide Agenten); `random_state` ist neuer Konstruktor-Parameter des statistischen Agenten (Default 42)
- CNN-Kalibration: Feature- und Ziel-Standardisierung vor dem Training (das CNN divergierte auf unskalierten ADC-Werten: R² = −2093)

**Verifikation (2000 Kalibrationszeilen, 5-fold CV):**

| Methode | vorher | nachher |
|---|---|---|
| PLS (statistisch) | −1.83 | **+0.626** |
| PCR (statistisch) | kollabiert | **+0.613** |
| PLS (Kalibration) | −1.38 | **+0.626** |
| CNN (Kalibration) | −2093 | **+0.865** |

Damit entspricht die Plattform dem Orange-Referenzwert (PLS 0.622 / RMSECV 0.623).

## Issue #66 – Stichprobenlimit 200 Kalibrationszeilen

**Datei:** `services/project_ingest.py`

**Ursache:** Die `_ingest_wide_format`-Staffelung begrenzte die Kalibrationsstichprobe auf `min(200, len(paired))` – 90 % der Information der 2014 bereinigten Messungen ging verloren (u. a. MLP R² ≈ 0.001 wegen 150 Trainingszeilen).

**Fix:** `max_samples = min(2000, len(paired))` (gestaffelt wie bisher, nur das Limit angehoben).

**Verifikation:** 2000 Kalibrationszeilen auf den Tomatendaten; OP20-Prüfung „≥ 50 Zeilen" weiterhin erfüllt; OP14 31/31 grün.

## Issue #67 – Kalibrations-Agent ohne Referenzwerte (`no_reference`)

**Datei:** `agents/nir_analysis_crew.py`

**Ursache:** Der `calibration_context` enthielt nur `spectral_data` und `metadata`, aber keine `spectra`/`reference_values` – der statistische Agent bekam die dateiweiten Kalibrationsmessungen (`supervised_context`), der Kalibrations-Agent lief leer.

**Fix:** `calibration_context` reicht jetzt `spectra` und `reference_values` aus dem `supervised_context` durch.

**Verifikation (Tomatendaten, komplette Kalibrations-Agenten-Matrix):**

| Methode | mean R² |
|---|---|
| PLS | +0.626 |
| PCR | +0.613 |
| SVM | +0.862 |
| RandomForest | +0.872 |
| XGBoost | +0.867 |
| CNN | +0.865 |

## Teststatus

| Matrix | Ergebnis |
|---|---|
| `tests/test_op14_agent_truthfulness.py` | 31/31 ✓ |
| `tests/test_op18_cnn_agent.py` | 25/25 ✓ |
| `tests/test_op6_crewai_agents.py` | 51/51 ✓ |
| `tests/test_op11_rendered_final_report.py` | 30/30 ✓ |
| `tests/test_op16_pca_charts.py` | ⚠ env: scheitert an `import django` (Sandbox ohne Django), prä-existent, keine Aussage über die Fixes |
| `tests/test_op20_calibration_charts.py` | ⚠ env: dito |

## Ausblick

- **Group-wise CV nach Tomate** (Replikate derselben Frucht strikt in denselben Fold) würde den verbleibenden Optimismus-Bias eliminieren – als Folge-Issue empfohlen.
