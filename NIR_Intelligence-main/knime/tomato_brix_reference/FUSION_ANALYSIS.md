# Fusions-Analyse der gemergten Datensätze (KNIME-Referenz, T4-T5 + CSV-Export)

Stand: 2026-10-19. Anwendung des im Artikel (Abschnitt 6.7) beschriebenen
Fusionspfads auf die beiden realen Quell-Datensätze der Session:

- **Quelle A:** `data/raw/T4-T5_ALLE_mit_Brix_2.txt` (2014 bereinigte Zeilen,
  40 Messobjekte, Brix 4.32–8.10)
- **Quelle B:** CSV-Export „Alle_Daten_Brix“ (1506 bereinigte Zeilen,
  33 Messobjekte, Brix 4.00–7.90)
- **Gemeinsame Messobjekte: 0** — die Quellen sind zeitlich/operatorisch
  unabhängige Erfassungsläufe am selben Sensortyp (Dpark fun NIR Triad).

Ausführbar: `scripts/knime_fusion_analysis.py <pfad/zur/CSV-Quelle-B>`,
Ergebnisse: `output/knime_fusion/knime_fusion_results.json` (gitignored) sowie
`fusion_pred_vs_ref.png` und `fusion_rmse_comparison.png`.

## 1. Ergebnisse (PLS, 10 Komp., 5-fold CV, seed 42)

| Kalibration | n | R²cv | RMSECV | RPD | Treffer ±0,5 | Treffer ±1,0 |
|---|---|---|---|---|---|---|
| Quelle A allein | 2014 | 0.621 | 0.623 | 1.63 | 63.3 % | 89.5 % |
| Quelle B allein | 1506 | 0.722 | 0.568 | 1.90 | 66.0 % | 91.0 % |
| **Fusion (global normalisiert)** | 3520 | **0.545** | **0.724** | 1.48 | 50.9 % | 84.3 % |
| Fusion (pro Quelle normalisiert) | 3520 | 0.456 | 0.793 | 1.36 | 47.0 % | 79.8 % |

Signifikanztest der Fusionsresiduen nach Quelle:
**Levene p = 0.006, Welch p < 0.001** → Restheterogenität **signifikant**.

## 2. Interpretation — ein negatives Ergebnis ist ein Ergebnis erster Klasse

Ob Fusion hilft, ist laut Artikel „eine empirische Frage pro Kampagne, die
die Plattform mit Messungen beantwortet, nicht mit Annahmen“. Für dieses
Quellenpaar lautet die Antwort klar: **Fusion schadet messbar.**

- Die Fusion liegt **unter beiden Einzelquellen** (R²cv 0.545 vs. 0.621/0.722;
  R²-Verlust −0.176 gegen die bessere Quelle B).
- Der Signifikanztest bestätigt die Ursache: hochsignifikante
  Restheterogenität (Levene p = 0.006, Welch p < 0.001) — die ADC-Skalen der
  beiden Erfassungsläufe sind nicht kompatibel (unterschiedliche Offsets und
  Verstärkungen, 0 gemeinsame Messobjekte, keine gemeinsame
  Kalibrationsbrücke).
- Das Resultat ist robust gegen die Normalisierungsvariante: globales
  Z-Score (0.545) und pro-Quelle-Z-Score (0.456) verschlechtern sich beide
  gegenüber den Einzelnachweisen.

## 2b. Korrekturvarianten (Nutzeranforderung: Brix bleibt Basis)

Der Nutzer erwartet, dass die KI bei signifikanter Restheterogenität
nicht abbricht, sondern spektrale Korrekturen anwendet und die
Bewertung auf den korrigierten Zahlen erneut vornimmt (Bounded
Autonomy, Artikel §5.4). Deshalb rechnet der Analysepfad zusätzlich
drei Korrekturvarianten (jeweils identische Methodik: PLS 10 Komp.,
5-fold CV, seed 42, Levene/Welch auf den korrigierten Residuen):

| Variante | R²cv | RMSECV | Levene p | Welch p |
|---|---|---|---|---|
| V0 Baseline (global Z-Score) | 0.545 | 0.724 | 0.006 | <0.001 |
| **V1 SNV (zeilenweise) + Z-Score** | **0.646** | **0.639** | <0.001 | <0.001 |
| V2 MSC (pro Quelle) + Z-Score | 0.453 | 0.794 | 0.185 | <0.001 |
| V3 MSC (gemeinsame Anchor-Kurve) + Z-Score | 0.472 | 0.780 | <0.001 | <0.001 |

**Korrigiertes Verdict (automatisch formuliert):**
- Die SNV-Korrektur verbessert die Fusion messbar (R²cv 0.545 → 0.646,
  Trefferquote ±0,5: 51 % → 60 %) — die Bewertung auf Basis der
  korrigierten Zahlen ist also besser als die Baseline-Aussage.
- Sie bleibt aber unter der besten Einzelquelle (0.722). Und der
  Signifikanztest auf den korrigierten Residuen wird nicht schwächer,
  sondern stärker (Levene p < 0.001): die Heterogenität der beiden
  Erfassungsläufe steckt nicht im spektralen Offset/Gain, den SNV
  entfernt — sie sitzt tiefer (Beleuchtungsführung, Probenposition,
  Referenz-Erfassung). Das kann keine Spektralkorrektur beheben,
  nur die Anchor-Messung.
- Ehrliches Fazit: Pro Quelle kalibrieren (B allein: 0.722) oder
  gemeinsame Anchor-Messung nachholen und die Fusion wiederholen.

Der ausführbare Referenz-Workflow inklusive aller Varianten liegt als
KNIME-Import-Datei vor: `tomato_fusion_analysis.knwf` (in KNIME 5.x:
File → Open). Die Variantenzahlen liefert
`python3 scripts/knime_fusion_analysis.py <CSV-Quelle-B>`
(Ausgabe: `output/knime_fusion/knime_fusion_results.json`, jetzt mit
`korrekturvarianten` + `korrektur_verdict`).

## 3. Einordnung gegen die Artikel-Fusion (OP63, Tabelle 7/8)

Die Artikel-Fusion (0.935/0.980 → 0.997, Levene p = 0.176) war eine
**kontrollierte Zwei-Operator-Sitzung mit Brix-Simulation** auf gemeinsamer
Geräte-/Normalisierungsbasis. Das vorliegende Quellenpaar ist real,
aber **unkompatibel skaliert**: gleicher Sensortyp, aber getrennte
Erfassungsläufe ohne Joint-Anchor (kein gemeinsames Messobjekt, keine
gemeinsame Referenzmessung). Genau dafür ist der Signifikanztest da: er
detektiert die Inkompatibilität, statt sie durch Optimismus zu überdecken.

## 4. Methodische Positionen (dokumentiert, nicht geglättet)

1. **Normalisierung der Fusion:** global (Kennzahl 0.545) vs. pro Quelle
   (0.456). Keine Variante erreicht die Einzelquellen — der Befund
   „Fusion schadet“ ist nicht normalisierungsbedingt.
2. **Kein Daten-Cleaning über Quellen:** jede Quelle wurde mit derselben
   Knotenkette (ADC-Überlauf, Nullwerte) einzeln bereinigt, Originale
   bleiben unberührt.
3. **Ehrlichkeitsregel:** Der Fusion-Bericht behauptet keinen Gewinn.
   Empfehlung: Quellen nicht mergen; stattdessen pro Quelle kalibrieren
   oder eine gemeinsame Anchor-Messung (weiße/graue Referenz +
   gemeinsame Fruchtprobe) nachholen und die Fusion wiederholen.

## 5. KNIME-Knotenkette (pro Quelle und fusioniert)

```
CSV Reader ×2 → Rule-based Row Filter ×2 (je Quelle) → Normalizer
→ Concatenate (Fusion) → X-Partitioner (5-fold, seed 42)
→ PLS Learner (10 Komp.) → Predictor → Numeric Scorer
→ R-Snippet: leveneTest / t.test → Bar Chart (RMSE) → Scatter (pred vs ref)
```
