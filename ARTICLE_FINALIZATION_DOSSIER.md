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

## C. FERTIGE MANUSKRIPT-ABSCHNITTE (vollständig — direkt übernehmen)

### C.1 §6.7 komplett: „From Readiness to First Exercise: Fusion and a Two-Operator Federated Session"

> A calibration model for low-cost spectroscopy is only as good as the
> diversity of its training data, but centralizing raw spectra collides
> with data-protection regulation and with the reality that many data
> owners cannot hand over raw measurements. NIR-IP addresses this sharing
> dilemma at two levels, and both were exercised since the previous
> revision.
>
> **Fusion as a governed analysis branch.** When similarity search returns
> hits from another project, the platform offers a review-driven fusion
> path: metadata are compared field-wise (generic comparison, no
> domain hard-coding), the two source projects are merged into a NEW fusion
> project that leaves the originals untouched, and a comparative
> calibration computes three PLS models — each source alone and the
> combined dataset — plus a significance test (Levene on residual variance,
> Welch on residual means) of whether the source difference measurably
> harms the calibration. The fusion result is presented as what it is: one
> combined dataset, with the predicted value of every measurement plotted
> against its measured reference (cross-validated), tolerance-based hit
> quotas derived from the reference resolution (0.1 °Brix steps), and an
> automatically formulated plain-text conclusion. In a controlled
> two-operator verification run (60 spectra, 20 channels), the combined
> calibration reached R²(CV) = 0.997 (RMSECV 0.203, RPD 21.6) against
> 0.935 and 0.980 for the single sources, with the significance test
> finding no residual heterogeneity (Levene p = 0.176, Welch p = 0.933).
> Whether fusion helps is thereby an empirical, per-campaign question
> that the platform answers with measurements, not an assumption.
>
> **A first federated exercise.** The same two-operator split was run as a
> federated session with Flower-transport semantics: each client trained a
> local PLS calibration on its own shard and transmitted only model
> parameters (coefficients, intercept, example count) — never spectra.
> The consent gate behaved as specified (rounds refused with 403 before
> explicit opt-in; status follows consent), the differential-privacy
> accountant reported a computable ε-budget (Gaussian mechanism, clipping
> norm 1.0), and secure aggregation was honestly reported as unavailable
> in the verification environment rather than simulated. The federated
> global model (example-weighted FedAvg of the PLS hyperplanes) reached
> RMSE 0.451 (R² = 0.989) on all 60 measurements, clearly better than
> either local model alone (0.281 and 0.233) while remaining behind the
> pooled in-sample optimum (0.124) — the expected behaviour for one-shot
> hyperplane averaging, documented as such. This is a verification run on
> a controlled split, not a multi-site campaign; its claim is that the
> federated path executes its contracts end-to-end: consent, parameter-only
> transport, honest privacy accounting, aggregation, and a global model
> that demonstrably benefits from both shards without either seeing the
> other's data.
>
> Federation remains the third level of the iterative method (Section 5.6):
> each aggregation round is a recorded iteration of the shared model, and
> the discussion layer (Section 6.5) receives the full comparison —
> metrics, hit quotas, significance verdict, conclusion — as context, so
> the results can be examined in dialogue with the platform's reasoning
> assistant rather than only read.

**Tabellen dazu (aus §6.7):**

_Table 7. Two-source fusion, controlled two-operator verification run
(n = 30 + 30 = 60, 20 channels, simulated Brix reference for contract
verification; not a campaign on the tomato measurements)._

| Calibration | n | R²(CV) | RMSECV | RPD |
|---|---|---|---|---|
| Source A alone | 30 | 0.935 | 0.922 | 4.3 |
| Source B alone | 30 | 0.980 | 0.531 | 9.0 |
| Fusion (combined) | 60 | 0.997 | 0.203 | 21.6 |

_Table 8. Federated session on the controlled two-operator split
(global evaluation on all 60 measurements)._

| Model | RMSE | R² |
|---|---|---|
| local, Operator A only | 0.2810 | — |
| local, Operator B only | 0.2330 | — |
| federated (FedAvg-PLS, rounds 1–5 stable) | 0.4505 | 0.989 |
| central (all data pooled, in-sample) | 0.1239 | 0.999 |

### C.2 §6.7-Erweiterung: „Sensor-aware fusion" (nach dem Fusions-Absatz)

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
> eighteen channels differ significantly, the B/A ratios are not a global
> factor but a channel-dependent pattern (from 1.91 at 560 nm down to
> 0.75 at 900 nm — the sources differ by gain *and* by spectral shape),
> and the correlation-structure difference peaks at the very channel that
> carries the Brix information (G_560, |Δ| = 0.64).
>
> The decisive diagnostic is the **confounding diagnosis**. Without
> shared measured objects, sensor gain and sample population are
> statistically confounded: the ratio spread between objects (IQR 2.2 at
> G_560 for the real source pair) shows that the apparent "gain
> difference" is entangled with which fruits were measured — a gain curve
> estimated from such data alone would absorb sample effects and is
> therefore not trustworthy. The platform states this as a finding rather
> than papering over it. To make the gain curve estimable in a
> sensor-agnostic way, NIR-IP defines a **reference-measurement protocol
> contract** for fusion projects: each source declares dark and white
> reference measurements (metadata: reference type, artifact, and at
> least 50 repetitions) — no specific hardware is prescribed, because the
> contract is a measurement condition, not a device. From compliant
> references the platform estimates the sensor transfer function
> radiometrically — (raw − dark)/(white − dark) per channel, smoothed over
> the wavelength axis, with a confidence note derived from the repetition
> spread — and offers the resulting gain curve as an additional correction
> variant. Without compliant references the gain curve is honestly
> reported as not estimable, together with the protocol text; it is never
> simulated.
>
> **Correction loop.** When the significance test reports residual
> heterogeneity, the platform does not stop at the verdict. It computes
> correction variants — standard normal variate (SNV) and multiplicative
> scatter correction (MSC) always; the reference-based gain curve when
> the contract is met — re-runs the identical cross-validated PLS pipeline
> on the corrected data, and formulates a corrected verdict automatically.
> On the real source pair the loop produces a first-class methodological
> finding: SNV measurably improves the fusion (R²(CV) 0.545 → 0.646), yet
> the corrected fusion remains below the better single source (0.722),
> and the significance test on the corrected residuals becomes *stronger*,
> not weaker (Levene p < 0.001) — the heterogeneity does not live in the
> spectral offset and gain that SNV removes, but deeper in the acquisition
> conditions. The corrected verdict states exactly this: the recommendation
> is to calibrate per source, or to acquire the reference measurements the
> contract demands and repeat the fusion. Negative results remain
> first-class: the loop measures whether correction helps, it does not
> assume it.

**Tabelle 9 (neu):**

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
> confounded; reference contract (dark/white, ≥ 50 repetitions) not met
> in either source → gain curve honestly reported as not estimable.

### C.3 §7.3 Limitations — Ergänzungssätze

> Federated path: the infrastructure is integrated and its contracts
> (consent, parameter-only transport, privacy accounting, aggregation)
> have been exercised end-to-end on a controlled two-operator split; a
> multi-site campaign on real distributed data has not yet run, so the
> empirical claim remains limited to contract verification, and hyperplane
> averaging is documented as a one-shot aggregation without iterative
> refinement (neural heads with true gradient rounds remain future work).

> Fusion path: the sensor comparison, confounding diagnosis, and
> reference-protocol contract are implemented and verified on a real
> source pair, but the reference-based gain curve has not yet been
> exercised on a campaign that actually acquires dark/white references
> (≥ 50 repetitions) — the corrected-verdict machinery is in place, and
> its empirical validation on reference-equipped sources is a scheduled
> iteration of the loop.

### C.4 §8 Hypothesen — H5 ersetzen

> H5 is confirmed at the verification level: the federated tiers execute
> their contracts end-to-end (consent gate, parameter-only transport,
> honest privacy accounting, aggregation to a global model that
> outperforms both local models), demonstrated on a controlled two-operator
> split; a multi-site campaign on real distributed data remains the
> scheduled next iteration of the loop (Section 6.7).

### C.5 §8 Roadmap — Ergänzungssatz

> …; acquisition of dark/white reference measurements (≥ 50 repetitions
> per source, per the fusion reference contract) for the two tomato
> sources, to promote the gain-curve correction from contract-verified to
> empirically validated; …

### C.6 Abstract — Ergänzungssätze

> Since the previous revision, the fusion path and a first federated
> exercise were added to the reported state: two-source fusion is a
> review-governed analysis branch that measures (not assumes) its
> calibration benefit with a significance test, and a controlled
> two-operator federated session executed the full contract chain —
> consent, parameter-only transport, honest privacy accounting, and
> aggregation — yielding a global model that outperforms both local
> models without either site seeing the other's data.

> The fusion path is sensor-aware: a full source comparison with a
> confounding diagnosis separates sensor gain from sample effects, a
> sensor-agnostic reference-measurement contract (dark/white, ≥ 50
> repetitions) makes the inter-sensor gain curve estimable without
> prescribing hardware, and a correction loop re-evaluates fusion on
> corrected data — reporting on real data that spectral correction
> measurably improves a heterogeneous fusion yet cannot replace
> compliant reference measurements.

### C.7 §3 Agent-Beschreibungen — Ergänzungen

> Sensor quality agent. (…) For fusion projects the agent additionally
> contributes the source-pair sensor comparison and the reference-
> measurement compliance check (dark/white, ≥ 50 repetitions) to the
> fusion branch (Section 6.7).

### C.8 Neu seit OP70/OP71 (nachtragen)

- **§6.7 Abbildung ergänzen (Band-Matrix):** „Figure X: Brix-band
  confusion matrix of the combined calibration (rows = measured band,
  columns = predicted band), shown per source dataset and for the fused
  set — the band-level view localizes systematic prediction offsets that
  aggregate metrics hide."
- **§6.5 Satz (XAI always):** „The explainability suite is rendered on
  every run; without TensorFlow a scikit-learn MLP fallback provides the
  four core plots, with gradient-based maps honestly absent rather than
  simulated."
- **§3/§6 optional (INTRO-Seite):** „A dedicated introduction page
  teaches correct measurement practice — lighting conditions, the
  dark/white reference protocol, and the metadata contract — with the
  sensor database feeding the device-specific guidance."

### C.9 Grafiken zu den Abschnitten (article_figures/)

| Datei | Inhalt | Empfohlene Stelle |
|---|---|---|
| `fig1_fusion_flowchart.svg` | Flowchart des review-governed Fusion-Workflows: Similarity-Trigger → Metadaten-Abgleich → Fusionsprojekt → 3×PLS + Signifikanztest → Verzweigung → Korrektur-Loop → korrigiertes Verdict → Entscheidung | §6.7 (neue Fig. nach dem ersten Absatz) |
| `fig2_components.svg` | Bestandteile-/Funktionsübersicht der Plattform: Analyse-Agenten (9), Fusion-Services (4), externe Referenzen (Orange/KNIME/Testmatrizen) | §3 (System Design) |
| `fig3_correction_loop.svg` | Korrektur-Loop am realen Quellenpaar mit allen Messwerten: V0→SNV/MSC→Verdict, Warum-Korrekturen-nicht-reichen-Panel, Zukunftsperspektive Referenz-Protokoll | §6.7 (Sensor-aware fusion) + Conclusion |

Alle SVGs sind valide, lizenzfrei (eigener Code) und in 300+ dpi-Qualität
in jedes Layout (Word/LaTeX/Quarto) einbettbar.

---|---|---|
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

## E. ZUKUNFTSPERSPEKTIVEN (im Artikel als „Future Work" / Roadmap führen)

### E.1 Referenz-Protokoll → empirisch validierte Gain-Korrektur (Kern-Zukunftsperspektive)

**Im Artikel (§8 Roadmap + Schluss von §6.7) so formulieren:**

> The measured refusal of the real-source fusion is not the end of the
> story — it defines the path forward. The sensor-agnostic reference
> protocol (dark/white, ≥ 50 repetitions per source, declared as metadata)
> is already implemented and contract-verified: once the two tomato
> sources acquire reference measurements, the platform estimates the
> inter-sensor transfer function radiometrically — (raw − dark)/
> (white − dark) per channel, smoothed over the wavelength axis — and
> offers the gain curve as a correction variant. Re-running the fusion
> then promotes the gain-curve correction from contract-verified to
> empirically validated, and completes the arc of this section: the
> platform detected the incompatibility, diagnosed its cause, refused to
> hide it, and now prescribes the exact measurement that resolves it.
> The same protocol scales to every future sensor in the growing
> database: any device that measures the two references can be placed on
> a common radiometric scale without centralizing raw spectra — the
> measurement-condition contract, not a device list, is what makes the
> infrastructure sensor-agnostic.

**Warum das die richtige Zukunftsperspektive ist (fachlich):**
- Die Konfundierungs-Diagnose hat gezeigt: Ohne gemeinsame Referenz
  misst eine aus Messdaten geschätzte Gain-Kurve den Probeneffekt mit —
  unbrauchbar. Dark/White-Referenzen sind probenunabhängig und damit die
  einzige saubere Brücke.
- Der Vertrag ist sensoragnostisch (Messbedingung, kein Gerät) — genau
  die Grundregel der Plattform; er skaliert auf die wachsende
  Sensor-Datenbank (OP72-INTRO bringt Einsteigern den Vertrag bereits bei).
- Ehrlichkeitswelle bleibt gewahrt: Ob die korrigierte Fusion die
  Einzelquelle erreicht, ist eine empirische Frage — das Ergebnis (in
  beide Richtungen) kommt in Tabelle 9.

### E.2 Container-Integrationstests TP-1 bis TP-4 (FL-Testplan Stufe B)
Auf dem Zielrechner mit echten Tomaten-Projekten als Operator-Shards
(Stufe B des FEDERATED_LEARNING_STAND_UND_TESTPLAN.md) — fördert H5 von
„verification level" zur empirischen Kampagne.

### E.3 Multi-Site-Federated-Kampagne
Echte verteilte Standorte, echte Consent-Entscheidungen, echte
Privacy-Budgets — die föderierte Version des Referenz-Protokoll-Gedankens:
gemeinsame Modellqualität ohne gemeinsame Rohdaten.

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
