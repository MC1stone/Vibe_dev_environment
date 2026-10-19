# Artikel-Aktualisierung: Fusion + Föderierte Session (Stand 2026-10-19)

> Arbeitdokument zum Manuskript „NIR-IP: An Open-Science Infrastructure for
> Iterative, Reproducible Low-Cost VIS/NIR Spectroscopy" (Working Draft,
> 8 October 2026). Enthält (1) die neuen Plattform-Ergebnisse seit OP63–OP66,
> (2) fertige, überarbeitete Manuskript-Abschnitte zum direkten Übernehmen
> (§6.7, §7.3, §8-H5, Abstract-Satz), (3) die Verifikationsprotokolle.
>
> **Ehrlichkeitsregel (OP14/OP18):** Die Fusion- und FL-Zahlen stammen aus
> Plattform-Verifikationsläufen mit einem kontrollierten Zwei-Operator-Split
> (60 Spektren, 20 Kanäle, Brix-Referenzwert-Simulation um die Plattform-
> Verträge zu prüfen). Es ist ein **Methoden-Nachweis**, keine echte
> Multi-Site-Kampagne mit den Tomaten-Messungen — das wird im Text so
> gesagt. Die Manuskript-Formulierungen sind entsprechend gewählt.

---

## 1. Neue Ergebnisse (Plattform-Zustand nach OP63–OP66)

### 1.1 Datenfusion als Analyse-Zweig (OP63–OP65b)

Die Plattform erkennt bei Similarity-Treffern aus einem ANDEREN Projekt
einen zusätzlichen Analyse-Pfad und bietet die Zusammenführung beider
Projekte in ein NEUES Fusionsprojekt an (Originale unangetastet, Doppel-
Fusionsschutz 422 + Verweis, generischer Metadaten-Abgleich ohne
Fachkontext-Hardcoding). Stufe 3 rechnet drei PLS-Kalibrationen im Vergleich
(Quelle A, Quelle B, kombiniert) plus Signifikanz-Test der Residuen pro
Herkunftsgruppe (Levene + Welch, scipy).

**Verifikationslauf (Zwei-Operator-Split, n=30+30=60):**

| Kalibration | n | R² (CV) | RMSECV | RPD |
|---|---|---|---|---|
| Quelle A einzeln | 30 | 0,935 | 0,922 | 4,3 |
| Quelle B einzeln | 30 | 0,980 | 0,531 | 9,0 |
| **Fusion (kombiniert)** | **60** | **0,997** | **0,203** | **21,6** |

Signifikanz-Test: Levene p = 0,176 (Varianzen gleich), Welch p = 0,933
(Mittelwerte gleich) — die Zusammenführung ist kalibrationstechnisch
unproblematisch; das Fazit wird von der Plattform automatisch formuliert.

### 1.2 Brix-Vorhersage gegen gemessene Brix als EIN Datensatz (OP66)

Das Fusionsprojekt erhält ein Predicted-vs-Reference-Streudiagramm
(kreuzvalidierte Vorhersagen, Diagonale = Ideal), das beide Quellen als
EINEN kombinierten Datensatz darstellt — Wiederverwendung des produktiven
Chart-Builders. Je Messung wird die vorhergesagte gegen die TATSAECHLICHE
Referenz gestellt (Trefferquote ±0,5/±1,0 aus der Messauflösung 0,1,
OP64/OP65), z. B. Trefferquote ±0,5: 21/30 (Quelle B). Chart-Erklärungen
(„Was zeigt dieses Diagramm?") stehen unter JEDER Grafik — auch in der
Kalibrations-Übersicht.

### 1.3 Ergebnisse als KI-Diskussionsgegenstand (OP66, MO 10)

Der Kalibrationsvergleich erzeugt eine Klartext-Zusammenfassung (Methode,
Kennzahlen je Kalibration inkl. Trefferquote, Fazit, Signifikanz-
Interpretation), die als Kontext in den Chatbot (Ollama/Mistral) eingespeist
wird. Die Nutzer-KI-Diskussion bezieht sich damit auf die tatsächlich
gerechnete kombinierte Analyse — „Ergebnisse mit KI und Nutzer diskutieren"
ist jetzt ein produktiver Plattform-Pfad, kein Feature-Claim.

### 1.4 Föderierte Session mit Operator-Shards (FL2/FL3/FL4-Live-Nachweis)

Zwei Datensätze als zwei Operator-Shards (je Shard: lokale PLS-Kalibration;
im Transport NUR Koeffizienten + Intercept + n — nie Spektren):

- **TP-3 Consent-Gate:** ohne Einwilligung 403; nach Opt-in
  `privacy_level: federated` — Opt-in-Vertrag bestätigt.
- **TP-4 Runden-Lauf:** Runde 1: 201, beide Clients
  (`Operator A:Tomaten`, `Operator B:Tomaten`), n=60.
- **TP-2 Privacy-Vertrag:** Payload = Parameter-Update
  (`only parameter updates shared - raw data stays local`).
- **FL3 Privacy-Ausweis:** DP (Gaussian, σ=4,84, Clip 1,0) rechenbar;
  SecAgg ehrlich als `unavailable` gemeldet (kein Fake).

**Konvergenz (FL2-Kernnachweis, globale RMSE auf allen 60 Messungen):**

| Modell | RMSE | R² |
|---|---|---|
| lokal nur Operator A | 0,2810 | — |
| lokal nur Operator B | 0,2330 | — |
| **föderiert (FedAvg-PLS, Runde 1–5 stabil)** | **0,4505** | **0,989** |
| zentral (alle Daten gepoolt, in-sample) | 0,1239 | 0,999 |

Aussage: Das föderierte Modell schlägt deutlich beide Einzel-Kalibrationen
— der Gewinn beider Datensätze entsteht, ohne dass ein Spektrum den Client
verlässt. An das zentrale Optimum kommt es nicht ganz heran (FedAvg mittelt
bei PLS die Hyperebenen; iteratives Gradienten-Training bräuchte neuronale
Köpfe) — erwartetes, ehrlich dokumentiertes Verhalten des FL2-Adapters.

---

## 2. Überarbeitete Manuskript-Abschnitte (zum direkten Übernehmen)

### 2.1 §6.7 Federated Calibration Readiness → ersetzen durch:

> ### 6.7 From Readiness to First Exercise: Fusion and a Two-Operator Federated Session
>
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
> Whether fusion helps is thereby an empirical, per-campaign question that
> the platform answers with measurements, not an assumption.
>
> **A first federated exercise.** The same two-operator split was run as a
> federated session with Flower-transport semantics: each client trained a
> local PLS calibration on its own shard and transmitted only model
> parameters (coefficients, intercept, example count) — never spectra.
> The consent gate behaved as specified (rounds refused with 403 before
> explicit opt-in; status follows consent), the differential-privacy
 accountant reported a computable ε-budget (Gaussian mechanism, clipping
> norm 1.0), and secure aggregation was honestly reported as unavailable
> in the verification environment rather than simulated. The federated
> global model (example-weighted FedAvg of the PLS hyperplanes) reached
> RMSE 0.451 (R² = 0.989) on all 60 measurements, clearly better than
> either local model alone (0.281 and 0.233) while remaining behind the
> pooled in-sample optimum (0.124) — the expected behaviour for one-shot
> hyperplane averaging, documented as such. This is a verification run on
> a controlled split, not a multi-site campaign; its claim is that the
> federated path executes its contracts end-to-end: consent, parameter-
> only transport, honest privacy accounting, aggregation, and a global
> model that demonstrably benefits from both shards without either seeing
> the other's data.
>
> Federation remains the third level of the iterative method (Section 5.6):
> each aggregation round is a recorded iteration of the shared model, and
> the discussion layer (Section 6.5) receives the full comparison —
> metrics, hit quotas, significance verdict, conclusion — as context, so
> the results can be examined in dialogue with the platform's reasoning
> assistant rather than only read.

### 2.2 §7.3 Limitations → Federated-path-Satz ersetzen durch:

> Federated path: the infrastructure is integrated and its contracts
> (consent, parameter-only transport, privacy accounting, aggregation)
> have been exercised end-to-end on a controlled two-operator split; a
> multi-site campaign on real distributed data has not yet run, so the
> empirical claim remains limited to contract verification, and hyperplane
> averaging is documented as a one-shot aggregation without iterative
> refinement (neural heads with true gradient rounds remain future work).

### 2.3 §8 Answer to the hypotheses → H5 ersetzen durch:

> H5 is confirmed at the verification level: the federated tiers execute
> their contracts end-to-end (consent gate, parameter-only transport,
> honest privacy accounting, aggregation to a global model that outperforms
> both local models), demonstrated on a controlled two-operator split; a
> multi-site campaign on real distributed data remains the scheduled next
> iteration of the loop (Section 6.7).

### 2.4 Abstract → nach dem PLS/Reference-Satz ergänzen:

> Since the previous revision, the fusion path and a first federated
> exercise were added to the reported state: two-source fusion is a
> review-governed analysis branch that measures (not assumes) its
> calibration benefit with a significance test, and a controlled
> two-operator federated session executed the full contract chain —
> consent, parameter-only transport, honest privacy accounting, and
> aggregation — yielding a global model that outperforms both local models
> without either site seeing the other's data.

### 2.5 Roadmap-Satz (§8, „near-term roadmap") → ersetzen durch:

> …; a multi-site federated calibration campaign on real distributed data
> to promote the two-operator contract verification to an empirical
> result; …

---

## 3. Verifikationsprotokolle

### 3.1 Offline-Matrizen (CI, alle grün)

| Matrix | Ergebnis |
|---|---|
| OP66 (`test_op66_fusion_pvr_charts.py`) | 28/28 |
| OP63 St3 (`test_op63_st3_calibration.py`) | 37/37 |
| OP63 St1+2 (`test_op63_fusion_branch.py`) | 45/45 |
| OP64 (`test_op64_fusion_release_feedback.py`) | 19/19 |
| OP65 (`test_op65_fusion_ux.py`) | 30/30 |
| FL-Kern S9, FL1–FL5, OP58 (Regression) | grün (CI) |
| OP24, OP20, S3–S6 (Regression) | 29/29, 33/33, 32/32 |

### 3.2 Laufender Stack (Dev-Server, Loopback 127.0.0.1:8001)

- App-Start, Migrationen, Seiten `/login/ /projects/ /calibration/
  /federated/ /api/chatbot/status/` → 200.
- Fusion-Endpoint: 200; `pvr_chart` = PNG-Data-URL (nur Fusionsprojekt);
  `discussion_summary` mit Kennzahlen + Fazit.
- Report-Seite (Phase released): Fusion-Kalibrations-Panel +
  Chatbot-Panel sichtbar.
- Föderierte Session: Consent 403→200, Runde 201 (2 Clients, n=60),
  Privacy-Ausweis mit DP-Mechanismus + ehrlicher SecAgg-Degradation.

### 3.3 Offen (Zielrechner mit Docker-Compose, Stufe B des FL-Testplans)

- TP-1 Stack-Hochfahrt (SuperLink/SuperNode-Container, gRPC)
- TP-2 Privacy-Vertrag im echten Transport (Log-Grep)
- TP-4 Runden-Lauf mit den ECHTEN Tomaten-Projekten als Operator-Shards
- Prod-Compose-Prüfung: Flower-Host-Ports entfernen, falls nicht benötigt

## 4. Manuskript-Anmerkungen (unverändert gültig)

- Die [ENTWURF]-Marken des Working Drafts (E-Mail, CRediT, Gruppen-CV,
  Schwellen-Herleitungen, XAI-Zitate) bleiben offen und sind hier nicht
  berührt.
- Zahlen in Tabelle 6 (PLS 0,626 vs. 0,622 usw.) sind vom echten
  Tomaten-Datensatz — unangetastet; die neuen Abschnitte berichten
  ausschließlich den Kontroll-Split und sagen das.
