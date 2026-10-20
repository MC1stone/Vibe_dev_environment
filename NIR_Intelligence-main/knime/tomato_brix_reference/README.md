# KNIME-Referenz-Workflow: Tomaten-Brix (T4-T5)

Externe Referenz-Auswertung im Sinne von Abschnitt 2.1/6.6 des NIR-IP-Artikels:
valide Plattform-Ergebnisse durch eine zweite, unabhängige Implementierung.

## Schnellstart (Skript, exakte Knotenlogik)

```bash
cd NIR_Intelligence-main
python3 scripts/knime_reference_validation.py
```

Erzeugt `output/knime_reference/knime_reference_results.json` und
`pls_pred_vs_ref.png`. Kennzahlen siehe `VALIDATION_REPORT.md`.

## Nachbau in KNIME (Schritt für Schritt)

| # | KNIME-Knoten | Einstellung |
|---|---|---|
| 1 | CSV Reader | Datei `data/raw/T4-T5_ALLE_mit_Brix_2.txt`; Trennzeichen `;`; Header automatisch (Zeile mit `Brix`/`Messobjekt`) |
| 2 | Rule-based Row Filter | entferne Zeilen mit beliebigem Kanalwert ≥ 2147483647 (ADC-Überlauf, Kanäle F_535/R_610) |
| 3 | Rule-based Row Filter | entferne Zeilen mit beliebigem Kanalwert ≤ 0 |
| 4 | Normalizer | Spalten A_410 … L_940, Modus Z-Score |
| 5 | GroupBy | Gruppierung `Messobjekt`; Aggregation Count — zeigt Replikatstruktur (40 Objekte, ~50 Zeilen/Objekt) |
| 6 | X-Partitioner | 5 Folds, Linear Sampling/Shuffle, Seed 42 |
| 7 | Linear Regression (Learner) | Ziel `Brix`, Prädiktoren A_410 … L_940 (normalisiert) |
| 8 | Regression Predictor | OLS-Vorhersage je Fold |
| 9 | Numeric Scorer | Soll: R² = 0.624, RMSE = 0.621 |
| 10 | PCA | 10 Komponenten auf den normalisierten Kanälen |
| 11 | Linear Regression (Learner) | Ziel `Brix`, Prädiktoren PC1 … PC10 |
| 12 | Regression Predictor | PCR-Vorhersage je Fold (PCA innerhalb des Folds fitten) |
| 13 | Numeric Scorer | Soll: R² = 0.607, RMSE = 0.635 |
| 14 | PLS (10 Komp., Benchmark) | Python/R-Snippet: `PLSRegression(n_components=10)`, `cross_val_predict` mit `KFold(5, shuffle=True, random_state=42)`; Soll R²cv = 0.621 |
| 15 | Scatter Plot (JFreeChart) | x = Brix-Referenz, y = Vorhersage, Diagonale = Ideal |
| 16 | CSV Writer | Kennzahlen als JSON/CSV nach `output/knime_reference/` |

## Referenzwerte (Deckungsziele)

- PLS 5-fold CV: R² 0.621 / RMSECV 0.623 (Orange: 0.622 / 0.623; Plattform: 0.626 / 0.618)
- OLS: R² 0.624 / RMSE 0.621; PCR (10 Komp.): R² 0.607 / RMSE 0.635
- Gruppenweise CV (GroupKFold nach Messobjekt): PLS R² 0.555 — Beleg für die
  `replica_overlap_in_cv`-Warnung des Artikels
- ADC-Sättigung: F_535 (7 Zeilen), R_610 (24 Zeilen)
- Wichtigster Kanal (Permutation): G_560

## Hinweise

- Die Datei `tomato_brix_reference_workflow.knime` beschreibt die Kette im
  Austauschformat; das Skript `scripts/knime_reference_validation.py` ist das
  ausführbare, deterministische Äquivalent (seed 42).
- Kein Anspruch auf ein überlegenes Modell: Die Daten sind zu verrauscht für
  Präzisionskalibration (RPD 1.63); der Beleg gilt der Übereinstimmung der
  Pipelines, nicht der Genauigkeit.


## Wichtiger Hinweis zur .knwf-Datei (Korrektur 2026-10-20)

Die `tomato_fusion_analysis.knwf` ist eine **generierte Beschreibung im
KNIME-XML-Austauschstil** (erzeugt vom NIR-IP-Referenz-Generator), **kein
in KNIME 5.x autorelier, importierbarer Workflow**: Fuer einen echten
Import benoetigt KNIME das volle Node-XML (nodeSettingsXML, Node-IDs,
UI-Koordinaten, exakte Version), das nur eine echte KNIME-Instanz
erzeugt. Die Datei dokumentiert Knotenkette, Einstellungen und
Referenz-Kennzahlen - **zum Nachbau in KNIME** (Schritt fuer Schritt,
siehe unten), nicht zum Direktimport.

**Ehrliche Alternative (vollstaendig ausfuehrbar):**
`scripts/knime_fusion_analysis.py` ist das deterministische Pendant der
Knotenkette (identische Logik, seed 42, gleiche Zahlen) und laeuft ohne
KNIME. Die Workflow-Abbildung fuer den Artikel:
`article_figures/fig4_knime_workflow.png` (300 dpi) bzw. `.svg`.

## Nachbau in KNIME (5.x) - Schritt fuer Schritt

1. **CSV Reader** x2 (Quelle A: T4-T5_ALLE_mit_Brix_2.txt; Quelle B:
   Alle_Daten_Brix-CSV) - Semikolon, Header auto.
2. **Rule-based Row Filter** x2 je Quelle: exclude
   $[alle Kanaele]$ >= 2147483647 (ADC-Ueberlauf) OR <= 0.
3. **Normalizer** je Variante: V0 Z-score (spaltenweise) / V1 SNV
   (zeilenweise) - bzw. **Moving Aggregate** (MSC) fuer V2/V3.
4. **Concatenate**: beide Quellen als EIN Datensatz, Spalte 'source'.
5. **X-Partitioner**: 5 folds, shuffle, seed 42.
6. **PLS Learner** (Python-Snippet: sklearn PLSRegression, 10 Komp.) +
   **Predictor**.
7. **Numeric Scorer** (R², RMSE) + **R-Snippet**
   (car::leveneTest, t.test je Quelle).
8. **Scatter (JFreeChart)**: Vorhersage vs. Referenz; **Bar Chart**:
   RMSE je Variante.

Erwartete Kennzahlen (Referenz, seed 42): A 0.621 / B 0.722 /
Fusion V0 0.545 (Levene p=0.006) / SNV 0.646 / MSC 0.453 / 0.472.
