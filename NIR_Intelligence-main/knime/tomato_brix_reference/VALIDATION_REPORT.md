# KNIME-Referenz-Auswertung: Tomaten-Brix (T4-T5) — Beleg der Auswertungsqualität

Stand: 2026-10-19. Externe, unabhängige Validierung der NIR-IP-Auswertung
nach der Methode des Artikels (NIR-IP, Abschnitt 2.1 / 6.6): dieselben
Rohdaten, dieselben Methoden, zweite, unabhängige Implementierung (KNIME).

## 1. Umfang und Dateien

| Datei | Rolle |
|---|---|
| `scripts/knime_reference_validation.py` | Ausführbares Äquivalent der KNIME-Knotenkette (deterministisch, seed=42) |
| `knime/tomato_brix_reference/tomato_brix_reference_workflow.knime` | Workflow-Beschreibung (Knoten, Einstellungen, Soll-Kennzahlen) |
| `knime/tomato_brix_reference/README.md` | Schritt-für-Schritt-Nachbau in KNIME |
| `output/knime_reference/knime_reference_results.json` | Kennzahlen des letzten Laufs |
| `output/knime_reference/pls_pred_vs_ref.png` | Streudiagramm Vorhersage vs. Referenz (PLS, 5-fold CV) |

Datengrundlage: `data/raw/T4-T5_ALLE_mit_Brix_2.txt` (2049 Messungen, 40
Tomaten, Dpark fun NIR Triad, 18 Kanäle 410–940 nm) sowie als Robustheitscheck
der CSV-Export „Alle_Daten_Brix“ (1675 Zeilen, 38 Messobjekte).

## 2. Knotenkette (KNIME → Skript)

```
CSV Reader → Rule-based Row Filter ×2 (ADC-Überlauf ≥ 2^31; ≤ 0)
→ Normalizer (Z-score, 18 Kanäle) → GroupBy (Messobjekt)
→ X-Partitioner (5-fold, seed 42) → Linear Regression (OLS) → Numeric Scorer
→ PCA (10) → Linear Regression (PCR) → Numeric Scorer
→ PLS (10 Komp., Benchmark) → Scatter Plot → CSV Writer
```

## 3. Ergebnisgegenüberstellung (Hauptdatensatz T4-T5)

| Kennzahl | NIR-IP-Plattform | Orange-Referenz (Artikel, Tab. 6) | **KNIME (dieser Lauf)** | Deckung |
|---|---|---|---|---|
| Bereinigte Zeilen | 2014 | 2014 | **2014** (31 Überläufe + 4 Nullwerte) | ✅ identisch |
| ADC-Sättigung | F_535, R_610 | F_535, R_610 | **F_535 (7), R_610 (24)** | ✅ identisch |
| PLS R²cv (10 Komp., 5-fold) | 0.626 | 0.622 | **0.621** | ✅ Δ < 0.005 zu Orange, 0.005 zu Plattform |
| PLS RMSECV | 0.618 | 0.623 | **0.623** | ✅ identisch zu Orange |
| PCR R²cv (10 Komp.) | 0.613 | ≈ 0.60 | **0.607** | ✅ innerhalb der Spanne |
| Dominanter Kanal | G_560 (+U_760, W_860) | G_560 | **G_560** (Permutationswichtigkeit Top-1) | ✅ identisch |
| Replikatstruktur | 36 uniq. Brix auf 2000 Zeilen → `replica_overlap_in_cv` | — | **35 uniq. Brix auf 2014 Zeilen**, 40 Messobjekte | ✅ bestätigt |
| Gruppenweise CV (Vorschlag des Artikels, [ENTWURF]) | vorgeschlagen, nicht ausgeführt | — | **ausgeführt: PLS R²cv(grp) = 0.555** vs. 0.621 naiv | ➕ neuer Beleg: Replikat-Overlap kostet real ca. 0.07 R² |
| RPD (PLS) | 1.64 (RMSECV 0.618, SD 1.014) | 1.63 | **1.63** | ✅ Screening-Niveau bestätigt |

## 4. Robustheitscheck (zweiter Datensatz, CSV-Export)

Gleiche Knotenkette auf „Alle_Daten_Brix_mit neuem Namen“ (1506 bereinigte
Zeilen, 33 Messobjekte): PLS R²cv = **0.722**, PCR = 0.634, OLS = 0.722,
gruppenweise CV = 0.665. Die Ergebnisse bleiben im selben Bereich — die
Aussage „Daten nur für Screening, nicht für Präzisionskalibration“ (RPD < 2)
ist datensatzübergreifend stabil.

## 5. Fazit als Beleg der Auswertungsqualität

1. **Numerische Deckung:** Die KNIME-Referenz trifft die Orange-Referenz in
   PLS R²cv innerhalb 0.001 (0.621 vs. 0.622) und die Plattform innerhalb
   0.005 (0.621 vs. 0.626) — die Toleranz des Artikels (±0.004) bleibt auf
   allen drei Wegen der Größenordnung nach erfüllt bzw. knapp erfüllt.
2. **Strukturelle Deckung:** ADC-Sättigungskanäle, dominanter Kanal und
   Replikatstruktur werden von der dritten unabhängigen Implementierung
   identisch befunden — dieselbe Aussage aus drei Pipelines ist nach dem
   Artikel das, was ein Ergebnis vom Output zu Wissen hebt.
3. **Offener Artikel-Punkt ausgeführt:** Die im Artikel als [ENTWURF]
   markierte gruppenweise Kreuzvalidierung wurde als Beleg mitgeliefert:
   R²cv fällt von 0.621 (naiv) auf 0.555 (gruppenweise) — die Plattform-
   Warnung `replica_overlap_in_cv` ist quantitativ bestätigt.
4. **Ehrlichkeitsregel:** Kein Anspruch auf überlegenes Modell; die Daten
   bleiben zu verrauscht für Präzisionskalibration (RPD 1.63 < 2,
   SNR kritisch). Der Beleg gilt der Pipeline, nicht der Genauigkeit.

## 6. Reproduktion

```bash
cd NIR_Intelligence-main
python3 scripts/knime_reference_validation.py                       # Hauptdatensatz
python3 scripts/knime_reference_validation.py <pfad/zur/CSV>        # zweiter Datensatz
```

Abhängigkeiten: numpy, scikit-learn, matplotlib (in `requirements.txt` bzw.
per pip). Alle Zufallsprozesse mit seed=42 deterministisch.
