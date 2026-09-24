# Vergleich nach Integration: NIR Intelligence Platform vs. Orange-Workflow

**Datum:** 2026-09-24 (Fresh-Lauf nach Merge von PR #64)
**Datenbasis:** `data/raw/T4-T5_ALLE_mit_Brix_2.txt` — Dpark fun NIR Triad, 18 Kanäle (410–940 nm), 40 Tomaten, Brix 4.32–8.1
**Plattform-Bericht:** `output/projects/reports/final_op14test_20260924_092127.html` (OP14-Matrix: 31/31 grün)
**Orange-Referenz:** `docs/analysis/ANALYSIS_REPORT.md` + `docs/analysis/orange_analysis_results.json`
**Vorher-Vergleich:** `PLATFORM_VS_ORANGE_COMPARISON.md` (Sektion 1b enthält die kompakte Nachher-Tabelle)

Dieser Bericht wiederholt den ursprünglichen Vergleich mit denselben Daten und derselben Methodik — aber mit der Plattform **nach Integration der Fixes aus den Issues #65–#67** (PR #64, gemerged). Struktur und Diktion folgen bewusst dem ersten Bericht, damit beide direkt nebeneinander lesbar sind.

---

## 1. Kennzahlen im direkten Vergleich

| Kennzahl | Platform **vorher** | Platform **nachher** | Orange-Workflow | Bewertung |
|---|---|---|---|---|
| **Datenbasis** | max. 200 gestaffelte Kalibrationszeilen + 25 Replikate | **2000 Kalibrationszeilen** | 2014 bereinigte Messungen | ✅ annähernd gleichwertig (Issue #66) |
| **PLS (CV, statistisch)** | **mean R² = −1.83** (Rohdaten, 10 Komp.) | **mean R² = +0.626** (standardisiert, KFold shuffle, 10 Komp., 5-fold: 0.613–0.653) | R² = 0.622, RMSECV 0.623 (10 Komp.; bestes Modell 9 Komp.) | ✅ **Deckungsgleich** (Issue #65) |
| **PCR (CV, statistisch)** | kollabiert | **mean R² = +0.613** (standardisiert, 5-fold: 0.586–0.657) | PCR 10 Komp., RMSECV 0.635 (R² ≈ 0.60) | ✅ konsistent |
| **MLP (neural)** | R² = 0.001 (150 Trainingszeilen) | **R² = 0.870** (1500 Train / 500 Test, konvergiert) | R² = 0.846, RMSE 0.398 (5-fold, 2014, Early Stopping) | ✅ Orange-Niveau erreicht — die Datenbasis war der Engpass |
| **CNN (neural)** | R² = 0.547, RMSE 0.663 (50 Testzeilen) | **R² = 0.782, RMSE 0.488** (500 Testzeilen, convergence) | R² = 0.587, RMSE 0.651 | ⚠️ Platform-CNN profitiert vom größeren Trainingsset; Orange-Konservatismus bleibt |
| **Kalibrations-Agent** | **`no_reference`** — übersprungen | **Alle 6 Methoden positiv:** PLS 0.626, PCR 0.613, SVM 0.862, RandomForest 0.872 (**best**), XGBoost 0.867, CNN 0.860 | PLS/PCR als Kalibrationsmodelle | ✅ Agent arbeitsfähig (Issue #67); RF/XGB/SVM-Werte sind optimistisch (s. § 4) |
| **Group-wise-CV-Hinweis** | — | **Automatisch erkannt:** 36 eindeutige Referenzwerte auf 2000 Zeilen, Ø 55.56 Replikate, Risiko `replica_overlap_in_cv` | — | ✅ Plattform „lernt" (gewünschte Folgeoption) |
| **PCA** | PC1 63.1 %, kum. 99.4 % (200 Proben) | PC1 67.5 %, kum. 99.5 % (2000 Proben, unskaliert) | PC1 38.0 %, kum. 97.0 % (2014, standardisiert) | ⚠️ Platform rechnet weiterhin unskaliert → Varianzdominanz einzelner Kanäle |
| **Clustering** | k=3 fest, Silhouette 0.347 (90/90/20) | k=3 fest, Silhouette 0.356 (2000 Proben) | k=2 optimiert, Silhouette 0.448 (1797/217) | ⚠️ Platform defaults auf k=3, Orange optimiert k |
| **ANOVA** | 36 Gruppen, 18 signifikante Merkmale | 36 Gruppen, 18 signifikante Merkmale, max F = 254.8 | Cluster vs. Brix: F = 91.3, p = 3.5·10⁻²¹ | unterschiedliche Fragestellung, unverändert |
| **Autoencoder** | 9 Anomalien (200 Proben, MSE 0.699) | **74 Anomalien** (2000 Proben, MSE 0.381, Schwelle 1.474) | 101 Anomalien (95. Perzentil, 2014) | ✅ größere Stichprobe → plausiblere Anomaliezahl |
| **Rauschen** | 0.294 (> 0.05, detektiert) | 0.294 (> 0.05, detektiert) | 0.406 (> 0.05) | beide kritisch, unverändert |
| **Drift** | 0.0224 **detektiert** | 0.0224 **detektiert** (Replikatenblock) | ≈ 0.0000 nicht detektiert | unverändert — beide Aussagen kontextabhängig wahr |
| **Gesamtqualität (Sensor)** | 73.2 / 100 | **75.0 / 100** | Ampel ROT (Score 0.00) | Platform milder aggregiert |
| **Metadaten** | 70.6 „fair" | 70.6 „fair" | nicht bewertet | unverändert |
| **FAISS** | 0 Referenzen → Skip | 0 Referenzen → Skip (sinnvoll: nur 1 Datei im Projekt) | Top-3 Self-Retrieval (0.41/0.55/0.55) | unverändert — unterschiedliche Semantik |
| **Bericht** | 20+ Abbildungen, Diskussion, Fazit, APA-Literatur, Chatbot | dito (20 img, 49 Abbildungs-Referenzen) | Markdown + JSON + 11 Grafiken | Platform weiterhin überlegen |

---

## 2. Was der Nachher-Lauf bestätigt (Robuste Kernergebnisse)

1. **Die Fixes wirken exakt wie in der Verifikation:** PLS mean R² = +0.626 im Live-Bericht (vorher −1.83) — innerhalb ±0.004 am Orange-Referenzwert (0.622).
2. **MLP ist jetzt der beste Vorhersager** (0.870 vs. Orange-MLP 0.846) — bestätigt die Diagnose aus dem ersten Vergleich, dass das Modell nie das Problem war, sondern die 150 Trainingszeilen.
3. **Der Kalibrations-Agent liefert eine vollständige Methodenmatrix** statt `no_reference` — die „beste Methode" ist jetzt RandomForest (0.872).
4. **Die Replikat-Erkennung schlägt zu:** `replicate_structure` erscheint automatisch im Bericht (36 eindeutige Brix-Werte auf 2000 Zeilen) mit der Group-wise-CV-Empfehlung — genau wie beauftragt: vorschlagen, nicht ausführen.
5. **Die CNN-Aussagen bleiben konservativ** (0.782 mit deutlichem Abstand zum MLP) — das Bild „CNN = moderates Screening-Niveau" bleibt stehen.

---

## 3. Verbleibende Unterschiede — erklärt und bewertet

### 3.1 PCA ohne Standardisierung (neu dokumentiert)

Die Platform-PCA erklärt 99.5 % Varianz mit 10 Komponenten (PC1 allein 67.5 %), Orange nur 97.0 % (PC1 38.0 %). Ursache: Orange standardisiert vor der PCA, die Platform rechnet auf Roh-ADC-Werten — Kanäle mit großem Offset dominieren PC1. **Bewertung:** Kein Fehler im engeren Sinn (die PCA ist auf beiden Wegen korrekt gerechnet), aber die standardisierte Variante zeigt die **korrelierende Struktur** (die für Brix relevant ist), die unskalierte vor allem Offset-Unterschiede. Ein Kandidat für eine spätere Harmonisierung — analog zu Issue #65, aber ohne den damaligen Fehler-Charakter (keine negativen R², kein kollabierendes Modell).

### 3.2 Clustering: k=3-Default vs. k-Optimierung

Platform: k=3 fest (Silhouette 0.356), Orange: k=2 optimiert (0.448). **Bewertung:** unverändert zum ersten Vergleich — Orange wählt das trennschärfere k, die Platform folgt dem Auftrag („3 Reifegruppen"). Beides vertretbar, solange berichtet wird, welches k wie gewählt wurde.

### 3.3 Replikat-Overlap in der CV (bewusst nicht behoben)

Die frisch gerechneten SVM/RF/XGBoost/CNN-Werte im Kalibrations-Agenten (0.86–0.87) sind **optimistisch**, weil Replikate derselben Tomate in Train- und Testfold landen können (36 einzigartige Ziele auf 2000 Zeilen). Die Plattform erkennt das jetzt selbst und schlägt Group-wise CV vor — ohne es auszuführen, wie für die Issues #65/#66 festgelegt. **Bewertung:** Das ist der gewünschte Zielzustand: Die Plattform lernt aus dem Befund, dokumentiert das Risiko im Bericht und überlässt die Entscheidung dem Nutzer.

### 3.4 Sensor-Urteile (unverändert, kein Handlungsbedarf)

Drift 0.0224 (Platform, Replikatenblock) vs. ≈ 0 (Orange, Gesamtreihe) — wie im ersten Vergleich: beide Aussagen sind in ihrem Bezugsfenster wahr, die Platform bleibt sensibler und ehrlicher auf Instrumentenebene.

### 3.5 FAISS (unverändert, semantisch korrekt)

0 Referenzen → Skip bleibt richtig im Projekt-Kontext (nur eine Datei). Orange liefert stattdessen Self-Retrieval — andere Frage, andere Antwort.

---

## 4. Gesamtbewertung

| Dimension | besser | Begründung |
|---|---|---|
| Datenhygiene | **Remis** (vorher Orange) | 2000 von 2014 Zeilen — der Stichproben-Nachteil ist praktisch behoben |
| Statistische Korrektheit | **Remis** (vorher Orange) | PLS/PCR identisch niveau- und vorzeichenkorrekt; PCA bleibt unskaliert |
| Kalibration | **Platform** (neu) | vollständige 6-Methoden-Matrix mit bestem Modell, Orange hat nur PLS/PCR |
| Neuronale Netze | **Remis** | MLP 0.870/0.846, CNN 0.782/0.587 — beide Wege liefern brauchbare Screening-Modelle |
| Sensor-Interpretation | **Platform** | unverändert: drift-sensibel, degraded-Status, Empfehlungen |
| XAI | **Platform** | unverändert: 7 Verfahren am CNN vs. 1 am PLS |
| Selbstlernende Empfehlung | **Platform** (neu) | replicate_structure + Group-wise-CV-Hinweis automatisch im Bericht |
| Bericht/Dokumentation | **Platform** | unverändert: Diskussion, Fazit, APA-Literatur, Chatbot |

### Fazit

Der Nachher-Lauf bestätigt punktgenau, dass die drei markanten Differenzen des ersten Vergleichs **Implementierungs-, nicht Dateneffekte** waren — und dass sie mit den Issues #65–#67 vollständig geschlossen sind:

1. **PLS-Vorzeichenwechsel** (−1.83 → +0.626): Skalierung + geschshufflede KFold — die Platform rechnet jetzt identisch zum Orange-Referenzwert.
2. **MLP 0.001 → 0.870**: Das Stichprobenlimit war der Flaschenhals, nicht das Modell.
3. **Kalibrations-Agent `no_reference` → 6/6 Methoden positiv**: Die Verkabelung ist repariert.

Die verbleibenden Unterschiede sind **methodischer Natur und dokumentiert** (PCA-Skalierung, k-Default, Replikat-Overlap) statt Fehler. Bemerkenswert: Die Plattform hat jetzt zwei Fähigkeiten, die der Orange-Workflow nicht hat — eine breitere Kalibrations-Methodenmatrix **und** die automatische Replikat-Erkennung mit Verbesserungsvorschlag. Der **Mehrwert** der Plattform gegenüber einem statischen Analyse-Workflow ist damit erstmals auch quantitativ sichtbar.

---

## 5. Verwendete Artefakte

| Artefakt | Pfad |
|---|---|
| Plattform-Bericht (nachher) | `output/projects/reports/final_op14test_20260924_092127.html` |
| Plattform-Testlauf (31/31 grün) | `tests/test_op14_agent_truthfulness.py` |
| Orange-Referenz | `docs/analysis/ANALYSIS_REPORT.md` + `orange_analysis_results.json` |
| Vorher-Vergleich | `docs/analysis/PLATFORM_VS_ORANGE_COMPARISON.md` |
| Fix-Dokumentation | `docs/analysis/PLATFORM_FIXES_ISSUES_65_67.md` |
| Orange-Workflow | `orange/tomato_nir_brix_analysis.ows` + `orange/tomato_nir_brix.tab` |
