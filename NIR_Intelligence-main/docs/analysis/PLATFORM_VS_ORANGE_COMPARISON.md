# Vergleich: NIR Intelligence Platform vs. Orange-Workflow-Analyse

**Datengrundlage (identisch):** `data/raw/T4-T5_ALLE_mit_Brix_2.txt` – Dpark fun NIR Triad, 18 Kanäle (410–940 nm), 2049 Messungen, 40 Tomaten, °Brix-Referenz 4.32–8.1

- **Plattform:** `run_project_crew` über alle 7 Agenten, Abschlussbericht `final_op14test_*.html` (OP14-Testlauf, 31/31 Checks grün)
- **Orange-Workflow-Äquivalent:** `scripts/orange_workflow_analysis.py` bzw. `orange/tomato_nir_brix_analysis.ows`, Bericht `docs/analysis/ANALYSIS_REPORT.md`

---

## 1. Kennzahlen-Gegenüberstellung

| Kennzahl | NIR Intelligence Platform | Orange-Workflow (Skript) | Unterschied |
|---|---|---|---|
| **Datenbasis** | 2049 Messungen erkannt; Agenten nutzen max. 200 gestaffelte Kalibrationszeilen + 25 Replikate | 2014 Messungen nach vollständiger Bereinigung (35 entfernt) | Platform stichprobenartig, Orange vollständig |
| **Bereinigung (ADC-Überlauf)** | 5 gesättigte (nur im 25er-Replikatenblock gezählt) | 31 Überläufe (F_535, R_610) + 4 Nullwerte, dateiweit | Orange reinigt die ganze Datei |
| **Rauschen** | 0.294 (> Schwelle 0.05, detektiert) | 0.406 (> Schwelle 0.05) | beide kritisch; Orange über alle 40 Tomaten, Platform über 25 Replikate |
| **Drift** | 0.0224 – **detektiert** (> 0.01) | ≈ 0.0000 – **nicht detektiert** | Platform sieht Drift im Replikatenblock, Orange trendbereinigt über die Gesamtreihe |
| **SNR** | 4.26 (Median-Vorschau) | 2.44 (Median), Min 1.96 | unterschiedliche Bezugsbasis |
| **Gesamtqualität** | **73.2 / 100** | **Ampel ROT** (Score 0.00 nach Schwellenformel) | Platform milder aggregiert |
| **PCA** | PC1 63.1 %, PC2 22.7 %, kumulativ 99.4 % (200 Proben) | PC1 38.0 %, PC2 25.9 %, kumulativ 97.0 % (2014 Proben) | andere Stichprobe → andere Struktur |
| **PLS (CV)** | **mean R² = −1.83** (10 Komp., 5-fold, Rohdaten) | **R² = 0.622, RMSECV 0.623** (10 Komp., standardisiert); bestes Modell: 9 Komp. | Vorzeichenwechsel! (s. § 3.1) |
| **CNN** | R² = 0.547, RMSE 0.663 (50 Testzeilen) | R² = 0.587, RMSE 0.651 (5-fold, 2014) | praktisch gleichwertig |
| **MLP** | R² = 0.001 (150 Trainingszeilen, konvergiert) | **R² = 0.846, RMSE 0.398** (5-fold, 2014, Early Stopping) | großer Unterschied (s. § 3.2) |
| **Autoencoder** | 9 Anomalien (200 Proben, MSE 0.699) | 101 Anomalien (95. Perzentil, 2014) | Stichprobengröße + Schwellenlogik |
| **Clustering** | k=3 fest, Silhouette 0.347, Größen 90/90/20 | k=2 gewählt, Silhouette 0.448, Größen 1797/217 | Platform defaults auf k=3, Orange optimiert k |
| **ANOVA** | 36 Gruppen, 18 signifikante Merkmale, min p = 1.6·10⁻⁴⁹ | Cluster vs. Brix: F = 91.3, p = 3.5·10⁻²¹ | andere Fragestellung |
| **Kalibrations-Agent** | **„no_reference"** – wurde übersprungen („Calibration requires reference values"), aber 3 PLS-Charts aus 200 Messungen gerendert | PLS 9 Komp., RMSECV 0.623; PCR 10 Komp., RMSECV 0.635 | Platform-Agent erhielt die Referenzen nicht (s. § 3.3) |
| **FAISS** | 0 Referenzen → Vergleich übersprungen („keine anderen Datensätze im Projekt") | Index über 2014 Spektren, Top-3 mit Distanzen (0.41/0.55/0.55) | Orange vergleicht innerhalb des Datensatzes |
| **XAI** | 7 Diagramme (Permutation, Occlusion, Saliency, Grad-CAM, Attention) am CNN | Permutationswichtigkeit am PLS (Top: G_560, U_760, W_860) | Platform breiter (CNN-XAI), Orange am Kalibrationsmodell |
| **Metadaten** | 70.6 „fair", ISO-19115/Dublin-Core-Empfehlungen | nicht bewertet (nicht Teil des Skripts) | Platform hat eigenen Metadaten-Agent |
| **Bericht** | HTML: 20+ Abbildungen, Diskussion, Fazit, Literatur (APA), Chatbot | Markdown + JSON + 11 Grafiken | Platform deutlich ausführlicher |

### 1b. Nach-Integration-Vergleich (Stand nach Merge von PR #64, Fresh-Lauf 2026-09-24 09:21)

Selber Datensatz, dieselbe Plattform — nach Integration der Fixes aus Issues #65–#67 (Bericht `final_op14test_20260924_092127.html`):

| Kennzahl | Platform vor Fixes | Platform nach Fixes | Orange-Workflow | Bewertung |
|---|---|---|---|---|
| **Kalibrationsstichprobe** | max. 200 Zeilen | **2000 Zeilen** (von 2014 bereinigten) | 2014 Zeilen | ✅ annähernd gleichwertig (Issue #66) |
| **PLS (CV, statistisch)** | mean R² = −1.83 | **mean R² = +0.626** (10 Komp., standardisiert, KFold shuffle) | R² = 0.622, RMSECV 0.623 | ✅ Deckungsgleich mit Orange (Issue #65) |
| **PCR (CV, statistisch)** | kollabiert | **mean R² = +0.613** | R² ≈ 0.60 (PCR 10 Komp.) | ✅ konsistent |
| **MLP** | R² = 0.001 (150 Trainingszeilen) | **R² = 0.870** (1500 Train / 500 Test) | R² = 0.846 (5-fold, 2014) | ✅ jetzt auf Orange-Niveau — gleiche Datenbasis heben das MLP |
| **CNN (neural)** | R² = 0.547 (50 Testzeilen) | **R² = 0.782, RMSE 0.488** (500 Testzeilen) | R² = 0.587, RMSE 0.651 | ⚠️ Platform-CNN profitiert vom größeren Trainingsset; Orange zurückhaltender |
| **Kalibrations-Agent** | `no_reference`, übersprungen | **alle 6 Methoden positiv:** PLS 0.626, PCR 0.613, SVM 0.862, RF 0.872 (best), XGBoost 0.867, CNN 0.860 | PLS/PCR als Kalibration | ✅ Agent arbeitsfähig (Issue #67); Achtung: RF/XGB/SVM-Werte sind optimistisch (Replikat-Overlap) |
| **Group-wise-CV-Empfehlung** | — | **automatisch erkannt**: 36 eindeutige Brix-Werte auf 2000 Zeilen, Risiko `replica_overlap_in_cv`, Empfehlung Group-wise CV | — | ✅ Plattform „lernt“: schlägt die Verbesserungsoption vor, ohne sie auszuführen |
| **PCA** | PC1 63.1 %, kum. 99.4 % (200 Proben) | PC1 67.5 %, kum. 99.5 % (2000 Proben) | PC1 38.0 %, kum. 97.0 % (2014, standardisiert) | ⚠️ Platform-PCA rechnet unskaliert → Varianzdominanz einzelner Kanäle; Orange standardisiert |
| **Clustering** | k=3, Silhouette 0.347 | k=3, Silhouette 0.356 (2000 Proben) | k=2, Silhouette 0.448 | ⚠️ weiterhin k=3-Default vs. Orange-Optimierung |
| **Rauschen/Drift/Sensor** | Rauschen 0.294, Drift 0.0224 detektiert | unverändert: Drift 0.0224 detektiert (Replikatenblock) | Drift ≈ 0 nicht detektiert | unchanged, beide Aussagen bleiben kontextabhängig wahr |
| **Gesamtqualität** | 73.2 / 100 | 75.0 / 100 | Ampel ROT | Platform milder aggregiert (unchanged) |

**Fazit Nach-Integration:** Die drei kritischen Differenzen aus § 3.1–3.3 sind geschlossen — PLS, MLP und der Kalibrations-Agent liefern jetzt Werte auf Orange-Niveau bzw. darüber. Verbleibende methodische Unterschiede (PCA ohne Standardisierung, k=3-Default beim Clustering, Replikat-Overlap in CV) sind dokumentiert; der Replikat-Overlap wird nun automatisch erkannt und die Group-wise-CV-Option als Empfehlung vorgeschlagen.

> Der vollständige Nachher-Bericht mit derselben Struktur wie dieser Vergleich: [POST_INTEGRATION_COMPARISON.md](POST_INTEGRATION_COMPARISON.md).

---

## 2. Was beide Analysen konsistent finden (Robuste Kernergebnisse)

Unabhängig von Implementierung und Stichprobe stimmen beide überein:

1. **Datenqualität ist der limitierende Faktor:** Rauschen (0.29–0.41) und SNR (2.4–4.3) liegen klar jenseits der Schwellen; beide Analysen empfehlen, die Messzeit zu erhöhen bzw. Replikate zu mitteln.
2. **ADC-Überläufe existieren real** (F_535/R_610) und müssen als eigene Warnung behandelt werden – beide tun das, nur mit unterschiedlichen Zählweisen.
3. **CNN ist stabil:** R² 0.547 vs. 0.587 – die Vorhersagekraft des 1D-CNN ist auf beiden Wegen „eingeschränkt, für Screening geeignet" (Originalton des Plattform-Fazits).
4. **Die Brix-relevanten Kanäle liegen im VIS/grünen Bereich** (G_560 dominiert in Orange; Plattform diskutiert Chlorophyll-/Carotinoid-Banden bei 435–645 nm) – physikalisch plausibel für Reifegrad/Pigmentabbau.
5. **Kreuzvalidierung ist Standard** in beiden (5-fold), Vorhersagen sind out-of-sample.

---

## 3. Wichtige Unterschiede – erklärt und bewertet

### 3.1 PLS: R² = −1.83 (Platform) vs. +0.62 (Orange) ⚠️

Der drastischste Unterschied. Ursachenkette:

- Der **statistische Agent der Platform** füttert PLS mit den **Roh-ADC-Werten** der 200 Kalibrationszeilen; ein explizites Feature-Scaling vor `cross_val_score` fehlt (OP18 behob das nur für den CNN-Agenten).
- Dazu kommen **konstante Brix-Werte pro Tomate** bei nur 40 einzigartigen Zielwerten auf 200 Zeilen – Replikate derselben Frucht landen teils in Train- und Testfold. Ein unskaliertes 10-Komponenten-PLS auf dominiert-by-offset-Daten bricht in der Kreuzvalidierung zusammen (negative R² = schlechter als Mittelwert).
- **Orange/Skript** standardisiert zuerst (μ=0, σ=1) und nutzt alle 2014 Messungen → R² 0.62, RMSECV 0.623 °Brix.

**Bewertung:** Der Plattformwert ist ein **echtes Schwachstellen-Signal**, kein Datenproblem – dasselbe PLS liefert mit Skalierung positive R². Das deckt sich mit dem OP18-Befund („raw ADC values against Brix ~5 stall the gradient descent"), nur eben für den statistischen Agenten noch nicht umgesetzt. **Nachbesserungs-Kandidat Nr. 1.**

> **✅ Behoben (Issue #65):** `agents/statistical_analysis_agent.py` und `agents/calibration_agent.py` standardisieren die Features jetzt per `StandardScaler` in einer Pipeline und validieren mit `KFold(shuffle=True, random_state=42)` statt ungeschshuffletem KFold (die Kalibrationszeilen sind nach Tomate sortiert – ohne Shuffle sieht jeder Fold nur einen schmalen Brix-Bereich, was die negative R² unabhängig von der Skalierung verursachte). Verifikation auf denselben Tomatendaten: **PLS mean R² = +0.626** (vorher −1.83), PCR +0.613, CNN-Kalibration +0.865 (vorher −2093 durch divergiertes Training auf unskalierten ADC-Werten). Damit entspricht die Plattform dem Orange-Referenzwert (0.622).

### 3.2 MLP: R² = 0.001 (Platform) vs. 0.846 (Orange)

- Platform: MLP mit 64–32 auf nur **150 Trainingszeilen** (75/25-Split der 200 Kalibrationszeilen), 200 Iterationen – bei konstanten Zielwerten pro Tomate und Replikat-Überschneidung bleibt praktisch keine generalisierbare Struktur übrig; „convergence_achieved: True" ist technisch true, aber inhaltlich bedeutungslos.
- Orange: 5-fold CV über **2014 Messungen**, Early Stopping – das MLP kann die Replikat-Struktur (gleiche Tomate → gleicher Brix) tatsächlich lernen.

**Bewertung:** Der MLP-Vergleich ist etwas **unfair**: das Orange-MLP kann Replikate derselben Fracht in Train und Test haben (leichte Optimismus-Bias), das Plattform-MLP ist dagegen schlicht unterversorgt. Dennoch: **MLP + volle Datenmenge ist mit Abstand der beste Vorhersager** – ein Ergebnis, das die Platform in dieser Form nicht produzieren kann, weil sie maximal 200 Zeilen weiterreicht. **Nachbesserungs-Kandidat Nr. 2** (Stichprobenlimit anheben).

> **✅ Behoben (Issue #66):** `services/project_ingest.py` reicht jetzt bis zu **2000 Kalibrationszeilen** weiter (vorher max. 200). Auf den Tomatendaten werden damit 2000 von 2014 bereinigten Messungen genutzt; OP20-Prüfungen (≥ 50 Zeilen) bleiben erfüllt, OP14 weiterhin 31/31 grün.

### 3.3 Kalibrations-Agent: „no_reference" trotz vorhandener Referenzen

Der Kalibrations-Agent der Platform meldet „Calibration requires reference values" und springt – obwohl der statistische Agent mit denselben 200 Kalibrationsmessungen arbeitet und sogar 3 PLS-Kalibrierungsdiagramme rendert. Offenbar werden `reference_values` nicht in den Kontext des Kalibrations-Agenten gereicht (der statistical agent bekommt `calibration_samples`).

**Bewertung:** Konsistenzfehler in der Agenten-Verkabelung, von OP18 nur für statistik/CNN behoben. Der Agent, dessen Kernaufgabe Kalibration ist, läuft leer – **Nachbesserungs-Kandidat Nr. 3**.

> **✅ Behoben (Issue #67):** `agents/nir_analysis_crew.py` reicht im `calibration_context` jetzt `spectra` und `reference_values` aus dem `supervised_context` (dateiweite Kalibrationsmessungen) durch. Verifikation auf den Tomatendaten: der Kalibrations-Agent liefert vollständige Ergebnisse statt `no_reference` – PLS +0.626, PCR +0.613, SVM +0.862, RandomForest +0.872, XGBoost +0.867, CNN +0.865.

### 3.4 Sensorurteile: Drift ja/nein

- Platform: Drift 0.0224 **detektiert** (betrachtet die 25-Replikaten-Serie, `drift_detected: True`, Status **degraded**)
- Orange: Drift ≈ 0.0000 **nicht detektiert** (linearer Trend über die gemittelte Gesamtintensität von 2014 Messungen)

Beide rechnen „Drift", aber auf unterschiedlichen Zeitfenstern: Der Replikatenblock (aufeinanderfolgende Messungen einer Tomate) zeigt den sensorischen Kurzzeittrend, die Gesamtreihe mittelt ihn weg. Beide Aussagen sind in ihrem Kontext wahr – die Platform ist hier **sensibler und ehrlicher** auf Instrumentenebene.

**Bewertung:** Kein Fehler, aber ein Beleg, dass „Drift" ohne Definition des Bezugsfensters nicht vergleichbar ist. Für die Praxis ist das Plattform-Ergebnis (Warm-up-Phase beachten, rekalibrieren) die nützlichere Aussage.

### 3.5 Stichproben-Design: 200 Zeilen vs. komplette Datei

Die Platform komprimiert die Kalibrationsdaten auf **maximal 200 gestaffelte Zeilen** (OP18-Design: „one reference value per measured object" war das Ziel, faktisch werden aber Zeilen über die ganze Datei gestaffelt). Der Orange-Weg nutzt **alle 2014 bereinigten Messungen**. Folgen:

- PCA erklärt auf der kleinen Stichprobe mehr Varianz (99.4 % vs. 97.0 %) – klassischer Small-Sample-Effekt
- Clustering fällt unterschiedlich aus (k=3 vorgegeben, 90/90/20 vs. k=2 optimiert, 1797/217)
- Modellqualität insgesamt (s. 3.1/3.2)

**Bewertung:** Das Sampling spart Rechenzeit und dämpft Replikat-Dominanz, kostet aber Signal. Für 18-Kanal-Daten mit 2049 Zeilen gibt es keinen Grund, 90 % der Information wegzulassen.

### 3.6 FAISS: leer vs. funktionsfähig

Platform: „0 Referenzen" – der Projekt-Modus vergleicht nur **gegen andere Datensätze des Projekts**, und es liegt nur eine Datei vor → sinnvoller Skip. Orange/Skript: Self-Retrieval im selben Datensatz („finde die 3 ähnlichsten Messungen"). Unterschiedliche Semantik – die Plattform-Entscheidung ist für den Projekt-Kontext richtig, beantwortet aber nicht die Frage „welche Messungen ähneln sich?".

### 3.7 Berichtsqualität: klarer Plattform-Sieg

Der Plattform-Abschlussbericht ist in einer anderen Liga: 20+ Abbildungen mit durchgehender Nummerierung (Abbildung 1–21), studentengerechte Diskussion mit Bandenzuordnung (Chlorophyll 435 nm, Carotinoide 510 nm …), Fazit mit realen Zahlen, APA-Literatur, eingebetteter Chatbot, Metadaten-Standardbewertung (ISO 19115 etc.). Der Orange-Bericht ist ein solides technisches Ergebnis-protokoll, aber kein Lehrdokument. **Für die Zielgruppe (Studierende, Laien) ist der Plattformbericht überlegen.**

---

## 4. Gesamtbewertung

| Dimension | besser | Begründung |
|---|---|---|
| Datenhygiene | **Orange** | vollständige dateiweite Bereinigung statt Replikatenfenster |
| Sensor-Interpretation | **Platform** | drift-sensibel, degraded-Status, konkrete Empfehlungen |
| Statistische Korrektheit | **Orange** | PLS positiv statt kollabiert; MLP nutzbar |
| Neuronale Netze | **Remis** | CNN quasi identisch (0.547/0.587); MLP-Vorteil Orange ist teils Replikat-Bias |
| XAI | **Platform** (Breite) | 7 Verfahren am CNN inkl. Grad-CAM/Attention vs. 1 Verfahren |
| FAISS/Similarity | **Orange** (funktional) | liefert echte Top-3 statt Skip |
| Metadaten | **Platform** | eigener Agent mit Standard-Scorecard |
| Bericht/Dokumentation | **Platform** | Diskussion, Fazit, Literatur, Chatbot, Abbildungsnummerierung |
| Reproduzierbarkeit | **Remis** | beide deterministisch; Platform via Tests (31/31), Orange via Skript + validierte .ows |

### Fazit

Beide Analysen sehen denselben Datensatz und kommen beim Kernbefund überein: **Die Daten sind für Präzisionskalibration zu rau** (SNR/Rauschen), **ein CNN erreicht moderates Screening-Niveau (R² ≈ 0.55–0.59)**, und die **visuellen Kanäle (G_560, U_760, W_860)** tragen die Brix-Information.

Die markanten Differenzen (PLS-Vorzeichenwechsel, MLP 0.001 vs. 0.846, übersprungener Kalibrations-Agent) sind **überwiegend Implementierungs-, nicht Dateneffekte** – alle drei sind inzwischen behoben:

1. ✅ **Issue #65:** Feature-Skalierung + geschshufflede KFold in den statistischen Agenten (PLS/PCR) und der CNN-Kalibration nachgezogen – PLS mean R² jetzt +0.626 statt −1.83
2. ✅ **Issue #66:** Stichprobenlimit von 200 auf 2000 Kalibrationszeilen angehoben
3. ✅ **Issue #67:** `reference_values` und `spectra` werden an den Kalibrations-Agenten durchgereicht – dieser liefert jetzt alle sechs Methoden mit positiven R²

Als nächster Verbesserungsschritt bliebe eine **Group-wise CV nach Tomate** (Replikate derselben Frucht strikt in denselben Fold), um den verbleibenden Optimismus-Bias zu eliminieren.

Umgekehrt profitiert der Orange-Weg von den Plattform-Vorstößen: Drift-Fenster, degraded-Status und XAI-Breite wären sinnvolle Erweiterungen des Skripts/Workflows.

---

## 5. Verwendete Artefakte

| Artefakt | Pfad |
|---|---|
| Plattform-Abschlussbericht (HTML, 20+ Abb.) | `output/projects/reports/final_op14test_20260924_083118.html` |
| Plattform-Testlauf (31/31 grün) | `tests/test_op14_agent_truthfulness.py` |
| Orange-Bericht | `docs/analysis/ANALYSIS_REPORT.md` + `docs/analysis/orange_analysis_results.json` |
| Orange-Workflow | `orange/tomato_nir_brix_analysis.ows` + `orange/tomato_nir_brix.tab` |
| Analyseskript | `scripts/orange_workflow_analysis.py` |
