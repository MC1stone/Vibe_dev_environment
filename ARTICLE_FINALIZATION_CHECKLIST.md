# ARTIKEL-FINALISIERUNGS-CHECKLISTE ([ENTWURF]-Marken)

> Arbeitsliste zur Finalisierung des Manuskripts „NIR-IP: An Open-Science
> Infrastructure…". Jeder Punkt: was zu tun ist, wo im Manuskript, und ein
> konkreter Formulierungsvorschlag. Abhaken, wenn erledigt.

## 1. Korrespondenz-Autor / Kontakt  `☐`
**Wo:** Titelseite + Fußnote „* Correspondence".
**Tun:** Echte E-Mail-Adresse von M. Klausmann einsetzen (HSWT-Adresse),
Fakultät/Institut + Adresse ergänzen (beide Autoren).
**Vorschlag:**
> 1 Hochschule Weihenstephan-Triesdorf, Fakultät [z. B. „Nachhaltige Agrar- und Forstwissenschaften"], [Straße Nr.], [PLZ Ort], Deutschland; [vorname.nachmachname]@hswt.de

## 2. CRediT-Autor-Rollen  `☐`
**Wo:** „Author Contributions".
**Tun:** Rollen für beide Autoren prüfen; P.N. ist aktuell nur bei
writing-review & editing + supervision genannt — ergänzen, was er
tatsächlich beigetragen hat (z. B. Conceptualization, Resources,
Supervision, Funding acquisition). Nicht beanspruchte Rollen streichen.
**Vorschlag (anpassen):**
> Conceptualization, M.K. and P.N.; methodology, M.K.; software, M.K.; validation, M.K.; formal analysis, M.K.; investigation, M.K.; resources, P.N.; data curation, M.K.; writing—original draft preparation, M.K.; writing—review and editing, M.K. and P.N.; visualization, M.K.; supervision, M.K. and P.N.; project administration, M.K.; funding acquisition, P.N. All authors have read and agreed to the published version of the manuscript.

## 3. Schwellen-Herleitungen der Qualitäts-Gates  `☐` *(wichtigste offene Fachstelle)*
**Wo:** §6.3 („Every threshold is a named configuration value…[ENTWURF]").
**Tun:** Für die vier Schwellen je EINE Herleitung geben (Literaturwert,
Norm oder empirische Verteilungsbegründung). Vorschläge:
- **Noise 0.05:** empirisch-relativ — „relative to the median channel
  intensity, a noise fraction above 5 % is documented in consumer-sensor
  practice as the level at which replicate medians of adjacent fruits
  begin to overlap (derived from the replicate distribution of the
  platform's reference datasets); the value is configurable and recorded
  in every report."
- **Drift 0.010:** „one percent of the replicate-block intensity span per
  measurement series — chosen so that a warm-up trend across the 25-fold
  replicate block becomes detectable while physiological drift within a
  session remains below it."
- **Autoencoder 1.4741 / |z| > 3.5:** bereits empirisch begründet —
  nur noch zitieren („derived from the training data's reconstruction-error
  distribution; robust z-score cut-off |z| > 3.5 corresponds to an
  expected false-positive rate < 0.05% under normality of the
  reconstruction errors") + ggf. Iglewicz & Hoaglin (1993) für 3.5-MAD.
- **SNR-Ampel-Werte:** Bezug auf die eigene Beobachtung stützen
  („SNR < 5 flagged: at this level, single-measurement readings can no
  longer be distinguished from channel noise — confirmed by the
  proof-of-concept dataset where SNR 2.44–4.26 coincides with screening-
  level CNN performance").
**Wichtig:** Diese Texte sind Vorschläge — die Werte selbst NICHT erfinden,
nur die ableitbare Begründung formulieren; wenn keine belastbare
Herleitung existiert, ehrlich als „platform default, configurable,
documented per report" kennzeichnen (Falsifizierbarkeit über
Konfigurierbarkeit).

## 4. XAI-Zitate  `☐`
**Wo:** §6.5 ([ENTWURF]-Marke).
**Tun:** Zitate je Verfahren einsetzen (Vorschläge aus der Marke):
- Permutation Importance: Fisher, Rudin, Dominici (2019), JMLR 20(177).
- Occlusion: Zeiler & Fergus (2014), ECCV 2014.
- Saliency: Simonyan, Vedaldi, Zisserman (2014), ICLR workshop.
- Grad-CAM: Selvaraju et al. (2017), ICCV 2017.
- Attention-Weights: eigenes Architektur-Element (kein Zitat nötig,
  Methoden-Absatz verweist auf das Modell).

## 5. PLS-Komponentenzahl der Referenz prüfen  `☐`
**Wo:** Tabelle 6, PCR-Zeile „[ENTWURF: Komponentenzahl des Referenz-PLS
gegen Vergleichsbericht prüfen]".
**Tun:** Im Orange-Vergiffsbericht nachsehen (10 Komp. laut Tabellenzeile)
und bestätigen oder korrigieren; danach Marke entfernen.

## 6. MLP/CNN-Zahlen als Einzelwerte kennzeichnen (bis Wiederholungsläufe)  `☐`
**Wo:** §6.4 / Conclusions (alte Marke, teils erledigt).
**Status:** Gruppenweise CV ist ausgeführt (0.555, KNIME PR #200) —
die Marke „gruppenweise CV ausführen und beide Zahlenreihen berichten"
ist **erledigt**: 0.621 naiv vs. 0.555 gruppenweise in §6.4/Tabelle 6
nachtragen. MLP/CNN-Wiederholungsläufe (Mittelwert ± Spanne) optional;
falls nicht mehr durchgeführt, kennzeichnen als
„single deterministic runs (seed-controlled)" — ehrlich, kein Fake.

## 7. OP70/71/72-Nachträge (aus Dossier C.8)  `☐`
- [ ] Band-Matrix-Figurentext in §6.7 einfügen (Abbildung aus dem
  Fusions-Report des Live-Stacks exportieren oder beschriebene Struktur
  als Tabelle)
- [ ] XAI-Always-Satz in §6.5 (MLP-Fallback)
- [ ] Optional: INTRO-Seite in §3/§6 erwähnen

## 8. Grafiken einbauen  `☐`
- [ ] fig1_fusion_flowchart (PNG 300 dpi / SVG) → §6.7
- [ ] fig2_components → §3
- [ ] fig3_correction_loop → §6.7 + Conclusion
- [ ] Bildunterschriften gemäß Dossier C.9 formulieren

## 9. Finale Konsistenzprüfung  `☐`
- [ ] Alle Zahlen gegen Dossier Abschnitt B abgleichen (einheitliche
      Nachkommastellen, R²cv vs. R²(CV)-Notation vereinheitlichen)
- [ ] Tabellennummerierung durchzählen (7/8/9 wie im Dossier)
- [ ] Referenzen [1]–[28] vervollständigen (fehlende hinzufügen:
      Fisher et al. 2019, Zeiler & Fergus 2014, Simonyan et al. 2014,
      Selvaraju et al. 2017, ggf. Iglewicz & Hoaglin 1993)
- [ ] Supplementary-Materials-Links prüfen (Plattform-Report,
      KNIME-Workflow `.knwf`, FUSION_ANALYSIS.md)
- [ ] Data Availability Statement: Rohdaten + Referenz-Workflows
      (Orange `orange/`, KNIME `knime/tomato_brix_reference/`) nennen
- [ ] Englische Rechtschreibprüfung (BE-Konsistenz: „behaviour",
      „colour-coded" etc.)

---
**Legende:** ☐ = offen · die Punkte 1, 2, 4, 5 sind reine Textarbeiten
(~1–2 h) · Punkt 3 ist der inhaltlichste (Vorschläge stehen) ·
Punkt 6 teilerledigt (0.555 nachtragen) · 7–9 mechanisch.
