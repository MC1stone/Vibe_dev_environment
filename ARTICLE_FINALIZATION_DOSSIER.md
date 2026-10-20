# ARTIKEL-FINALISIERUNGS-DOSSIER (Stand 20.10.2026)

> **Zweck:** Zentrale Zusammenstellung ALLER während der Entwicklung
> (OP63–OP72) entstandenen Informationen für die Finalisierung des
> Manuskripts „NIR-IP: An Open-Science Infrastructure for Iterative,
> Reproducible Low-Cost VIS/NIR Spectroscopy" (konsolidierter Stand
> 19.10.2026). Alles zum direkten Übernehmen; Quellen sind verlinkt/genannt.
>
> **Grundregel durchgehend:** Ehrlichkeitsregel OP14/OP18 — Live-Zahlen als
> reale Messungen gekennzeichnet, Vertragsverifikationen als kontrolliert/
> synthetisch; KNIME und Orange sind ausschließlich externe Referenzen,
> nie App-Bestandteil.

---

## A. ENTWICKLTER STAND DER SOFTWARE (OP63–OP72, alles auf main gemerged)

| OP | Inhalt | Status |
|----|--------|--------|
| OP63 | Fusion-Zweig St. 1–3: Similarity-Trigger, Fusionsprojekt (Originale unangetastet), vergleichende Kalibration (3× PLS + Levene/Welch) | gemerged |
| OP64 | Trefferquoten ±0,5/±1,0 °Brix pro Messung (vorhergesagt vs. tatsächliche Brix), Toleranzen aus Messauflösung 0,1 | gemerged |
| OP65 | Doppel-Fusionsschutz (422), KI-Metadaten-Vorschläge mit Übernehmen-Buttons, UI-Redesign Vergleich | gemerged |
| OP65b | Generischer Metadaten-Abgleich (kein Fachkontext-Hardcoding, Grundregel) | gemerged |
| OP66 | Brix-Chart (Vorhersage vs. Messung) des Fusionsprojekts als EIN Datensatz; Chart-Erklärungen unter jeder Grafik auch in /kalibration/; Fusionsergebnisse als Chatbot-Diskussionskontext (MO 10) | gemerged |
| OP67/OP69 | Artikel-Dokumentation (die beiden ARTICLE_UPDATE-Dateien) | gemerged |
| OP68 | Sensor-Analyse + Korrektur-Loop der Fusion: Vollständiger Sensor-Vergleich, Konfundierungs-Diagnose, sensoragnostischer Dark/White-Referenzvertrag (≥ 50 Wiederholungen), Gain-Kurve aus White-Referenzen, SNV/MSC/Gain-Korrekturvarianten + automatisch formuliertes korrigiertes Verdict | gemerged |
| OP70 | Brix-Band-Konfusionsmatrix (gemessen × geschätzt, je Kalibration, am Fusionsprojekt pro Quelle getrennt); XAI/CNN-Graphen IMMER (sklearn-MLP-Fallback ohne TensorFlow) | gemerged |
| OP71 | Warnungs-Aggregation aller Datensätze; Noise-Warnung konsolidiert (nur das höchste Rauschniveau, mit Quellenangabe) | gemerged |
| OP72 | INTRO-Seite „Richtig messen" unter Start (Grundprinzip, Licht, Schwarz/Weiß-Abgleich, Metadaten aus der Sensor-DB, Sensor-Dropdown) | gemerged |
| FL1–FL6 | Federated Learning: Kern (FedAvg/FedProx), Flower-Transport, föderierte PLS-Kalibration, DP-Privacy, UI/Consent, Deployment — Testplan als FEDERATED_LEARNING_STAND_UND_TESTPLAN.md | gemerged |

---

## B. DIE ZAHLEN (alle gegen die gleichen Echtdaten: T4-T5 vs. CSV-Export)

### B.1 Kernvalidierung (drei unabhängige Implementierungen, Tabelle 6)

| Implementierung | PLS R²cv | RMSECV |
|---|---|---|
| Plattform (NIR-IP) | 0,626 | 0,618 |
| Orange (Referenz) | 0,622 | 0,623 |
| KNIME (Referenz, PR #200) | 0,621 | 0,623 |

Deckung innerhalb ±0,005; ADC-Sättigungskanäle (F_535, R_610), dominanter
Kanal G_560 und Replikatstruktur von allen dreien identisch bestätigt.
Gruppenweise CV (Artikel-[ENTWURF] ausgeführt): **0,555** vs. 0,621 naiv —
replica_overlap_in_cv quantitativ belegt.

### B.2 Fusions-Verifikation (kontrollierter Zwei-Operator-Split, OP66)

| Kalibration | n | R²(CV) | RMSECV | RPD |
|---|---|---|---|---|
| Quelle A einzeln | 30 | 0,935 | 0,922 | 4,3 |
| Quelle B einzeln | 30 | 0,980 | 0,531 | 9,0 |
| **Fusion** | 60 | **0,997** | 0,203 | 21,6 |

Signifikanztest: Levene p=0,176, Welch p=0,933 → unproblematisch.
**Kennzeichnung:** kontrollierte Sitzung mit Brix-Simulation zur
Vertragsverifikung, KEINE Kampagne auf den Tomaten-Messungen.

### B.3 Föderierte Session (Operator-Shards, FL2-Live-Nachweis)

| Modell | RMSE | R² |
|---|---|---|
| lokal nur Operator A | 0,2810 | — |
| lokal nur Operator B | 0,2330 | — |
| föderiert (FedAvg-PLS, stabil) | 0,4505 | 0,989 |
| zentral (gepoolt, in-sample) | 0,1239 | 0,999 |

Verträge bestätigt: Consent-Gate 403→200, Parameter-only-Transport,
DP-ε rechenbar, SecAgg ehrlich „unavailable".

### B.4 Reale Fusion der Tomaten-Quellen (negatives Verdict 1. Klasse)

| Kalibration | n | R²cv | RMSECV | Treffer ±0,5 |
|---|---|---|---|---|
| Quelle A allein (T4-T5) | 2014 | 0,621 | 0,623 | 63 % |
| Quelle B allein (CSV) | 1506 | 0,722 | 0,568 | 66 % |
| **Fusion Baseline (V0)** | 3520 | **0,545** | 0,724 | 51 % |
| Fusion SNV (beste Korrektur) | 3520 | 0,646 | 0,639 | 60 % |
| Fusion MSC pro Quelle | 3520 | 0,453 | 0,794 | 50 % |
| Fusion MSC Anchor | 3520 | 0,472 | 0,780 | 48 % |

Signifikanztest: Levene p=0,006, Welch p<0,001 → hochsignifikante
Restheterogenität; unter SNV wird Levene STÄRKER (p<0,001) — die
Heterogenität steckt tiefer als spektraler Offset/Gain. 0 gemeinsame
Messobjekte, keine gemeinsame ADC-Skalierungsbrücke. **Empfehlung der
Plattform: pro Quelle kalibrieren oder Dark/White-Referenzmessung
(≥ 50 Wiederholungen) nachholen, dann Fusion wiederholen.**

### B.5 Sensor-Vergleich der realen Quellen (OP68)

- 10/18 Kanäle signifikant verschieden (Mann-Whitney p<0,001)
- B/A-Ratios kanalabhängig, kein globaler Faktor: G_560 = 0,52 (kritisch),
  E_510 = 0,66, NIR-Ende invertiert (K_900 = 1,33, L_940 = 1,21)
- Korrelationsstruktur-Differenz max |Δ| = 0,64 ausgerechnet bei G_560
  (dem Haupt-Brix-Kanal)
- Konfundierungs-Diagnose: ohne gemeinsame Messobjekte sind Sensor-Gain
  und Probenbestand statistisch konfundiert — Gain-Kurve aus Messdaten
  allein nicht belastbar; nur der Referenzvertrag löst das auf

---

## C. FERTIGE MANUSKRIPT-ABSCHNITTE (zum direkten Übernehmen)

| Artikel-Stelle | Inhalt | Quelle (Repo) |
|---|---|---|
| **§6.7 komplett** | „From Readiness to First Exercise: Fusion and a Two-Operator Federated Session" — Fusion als governed Zweig, Signifikanztest, kontrollierte Verifikation (Tab. 7/8), föderierte Session mit Verträgen | `ARTICLE_UPDATE_FUSION_FL.md` §2.1 |
| **§6.7-Erweiterung** | „Sensor-aware fusion" — Sensor-Vergleich, Konfundierungsdiagnose, Referenz-Vertrag, Korrektur-Loop mit realen Zahlen (B.4) | `ARTICLE_UPDATE_OP68_SENSOR_FUSION.md` §1.1 |
| **Tabelle 9** | Varianten-Vergleich am realen Quellenpaar (V0/SNV/MSC×2) + Sensor-Kennzahlen | `ARTICLE_UPDATE_OP68_SENSOR_FUSION.md` §1.2 |
| **§7.3 Limitations** | Federated-path + Fusion-path-Sätze (Vertragsverifikung vs. empirische Validierung; Gain-Kurve noch nicht an referenz-ausgestatteten Quellen validiert) | beide Dateien §1.3 |
| **§8 Hypothesen** | H5 aktualisiert („confirmed at the verification level") + Roadmap-Sätze (Referenzmessungen beschaffen → Gain-Korrektur validieren; Multi-Site-Kampagne) | `ARTICLE_UPDATE_FUSION_FL.md` §2.3, OP68-Datei §1.4 |
| **Abstract** | Zwei Ergänzungssätze (Fusion + föderierte Session; sensor-bewusste Fusion mit Referenz-Vertrag und Korrektur-Loop) | beide Dateien |
| **§3 Agent-Beschreibung** | Sensor Quality Agent + Kalibrations-Agent: Beitrag zum Fusion-Zweig | OP68-Datei §1.6 |

**Neu seit OP70/71 (noch nicht in den Manuskript-Texten — nachtragen):**
- Band-Konfusionsmatrix (gemessen × geschätzt, pro Quelle): Abbildung für
  §6.7 empfohlen — zeigt die systematische Schätzdifferenz der Quellen
  auf einen Blick
- XAI-Graphen jetzt immer vorhanden (MLP-Fallback) — §6.5 um einen Satz
  ergänzen: „The explainability suite is rendered on every run; without
  TensorFlow a scikit-learn MLP fallback provides the four core plots,
  with gradient-based maps honestly absent rather than simulated."
- INTRO-Seite (OP72) erwähnenswert in §3/§6 als didaktisches Werkzeug
  (Messanleitung mit Referenz-Vertrag für Einsteiger) — optional

---

## D. OFFENE [ENTWURF]-MARKEN DES KONSOLIDIERTEN STANDS

1. Autoren-Korrespondenz (E-Mail, Fakultät/Institut) — nur noch setzen
2. CRediT-Autor-Rollen prüfen/ergänzen
3. Schwellen-Herleitungen der vier Qualitäts-Gates (Literaturwert/Norm/
   empirische Verteilungsbegründung) — Falsifizierbarkeit
4. XAI-Zitate (Fisher/Rudin/Dominici 2019; Zeiler & Fergus 2014;
   Simonyan et al. 2014; Selvaraju et al. 2017)
5. Komponentenzahl des Referenz-PLS gegen Vergleichsbericht prüfen (Tab. 6)
6. ~~Gruppenweise CV ausführen~~ → erledigt: 0,555 (KNIME, PR #200)
7. **Neu:** Gain-Kurven-Korrektur an referenz-ausgestatteten Quellen
   empirisch validieren (Dark/White ≥ 50 Wiederholungen beschaffen,
   Fusion wiederholen, Ergebniszeile ergänzen) — geplante Loop-Iteration

---

## E. EMPIRISCCH-NOCH-OFFENE PUNKTE (Roadmap, ehrlich)

1. **Dark/White-Referenzmessungen** an den beiden Tomaten-Quell-Projekten
   (je ≥ 50 Wiederholungen, als Datensatz mit reference_type/n_repeats/
   reference_artifact deklariert) → App rechnet die Gain-Kurve → Fusion
   wiederholen → Ergebnis in Tabelle 9 nachtragen
2. **TP-1 bis TP-4** (Container-Integrationstests, FL-Testplan Stufe B)
   auf dem Zielrechner mit echten Tomaten-Projekten als Operator-Shards
3. **Multi-Site-Federated-Kampagne** auf real verteilten Daten
   (H5: verifiziert → empirisch)

---

## F. VERWEIS-KETTE (Reproduzierbarkeit)

- Plattform-Stand: main `1b739cd` (OP72 gemerged), alle Matrizen in CI grün
- Testmatrizen: OP63 37+45, OP64 19, OP65 30, OP66 28, OP68 44,
  OP70 23, OP71 14, OP72 33, OP19 19 (neuer Vertrag), FL1–FL6/S9 grün
- Referenz-Implementierungen: Orange (`orange/`), KNIME
  (`knime/tomato_brix_reference/` inkl. echter .knwf + FUSION_ANALYSIS.md
  mit Abschnitt 2b Korrekturvarianten; Skripte `scripts/knime_*`)
- FL-Testplan: `FEDERATED_LEARNING_STAND_UND_TESTPLAN.md`
- Methods-Rohstoff: `MATERIALS_AND_METHODS.md` (16 Unterabschnitte)
- Projekt-Einführung: `PROJECT_OVERVIEW.md`; UI/Workflow-Referenz:
  `NIR_Intelligence-main/docs/WORKFLOW_UI_REDESIGN.md`
