# NIR Intelligence Platform - student report sections (OP23)
# The final report lists per-agent results but was not written for
# students. OP23 adds three sections rendered from the REAL analysis
# results (no invented findings):
#
#   Diskussion      - interpretation of the spectra (band assignment from
#                     the measured wavelength range), model quality
#                     assessment (R2, RMSE/RMSECV from the agent results,
#                     with an honest RMSEP note) and possible error sources
#                     (spectral issues, sensor findings, general NIR
#                     effects) plus a detailed explanation of every figure
#   Fazit           - summary of the key findings and the optimization
#                     options (collected from all agent recommendations,
#                     each with a short explanation)
#   Literatur       - real, accessible standard works cited in APA style
#
# Fachbegriffe werden bei der ersten Nutzung im Fließtext erklärt
# (z. B. PLS = Partial Least Squares). Alles fällt sauber auf einen
# Minimaltext zurück, wenn Ergebnisse fehlen - der Report bleibt immer
# renderbar.
import html
from typing import Any, Dict, List, Optional, Tuple

_LITERATURE = [
    ("Pasquini, C. (2003). Near infrared spectroscopy: Fundamentals, practical "
     "aspects and analytical applications. <i>Journal of the Brazilian Chemical "
     "Society, 14</i>(2), 198\u2013219. https://doi.org/10.1590/S0103-50532003000200006",
     "Umfassender Review-Artikel: Grundlagen und Anwendungen der NIR-Spektroskopie."),
    ("Workman, J., & Weyer, L. (2012). <i>Practical guide to interpretive "
     "near-infrared spectroscopy</i>. CRC Press.",
     "Standardwerk zur Interpretation von NIR-Spektren und Bandenzuordnung."),
    ("Geladi, P., & Kowalski, B. R. (1986). Partial least-squares regression: "
     "A tutorial. <i>Analytica Chimica Acta, 185</i>, 1\u201317. "
     "https://doi.org/10.1016/S0003-2670(00)62328-9",
     "Tutorial zur PLS-Regression (Partial Least Squares), der hier verwendeten "
     "Kalibrationsmethode."),
    ("Wold, S., Sj\u00f6str\u00f6m, M., & Eriksson, L. (2001). PLS-regression: "
     "A basic tool of chemometrics. <i>Chemometrics and Intelligent Laboratory "
     "Systems, 58</i>(2), 109\u2013130. https://doi.org/10.1016/S0169-7439(01)00155-1",
     "Grundlagenarbeit zur PLS-Regression in der Chemometrie."),
    ("Williams, P., & Norris, K. (Hrsg.). (2001). <i>Near-infrared technology "
     "in the agricultural and food industries</i> (2. Aufl.). American "
     "Association of Cereal Chemists.",
     "Standardwerk zur NIR-Analytik von Lebens- und Futtermitteln (u. a. Brix, "
     "Zucker, Feuchte)."),
    ("N\u00e6s, T., Isaksson, T., Fearn, T., & Davies, T. (2002). <i>A "
     "user-friendly guide to multivariate calibration and classification</i>. "
     "NIR Publications.",
     "Einf\u00fchrung in multivariate Kalibration und Validierung (Kreuzvalidierung, "
     "RMSECV, RMSEP)."),
    ("Burns, D. A., & Ciurczak, E. W. (Hrsg.). (2007). <i>Handbook of "
     "near-infrared analysis</i> (3. Aufl.). CRC Press.",
     "Handbuch mit Spektraltafeln und Kapiteln zu Instrumentierung, Streulicht "
     "und Probenpr\u00e4paration."),
]

_BANDS = [
    (430.0, 15.0, "Chlorophyll-Absorption im sichtbaren Bereich (Blattfarbstoffe, "
                  "Pigmentzustand der Probe)"),
    (520.0, 15.0, "Carotinoid-/Anthocyan-Bereich (F\u00e4rbung, Reifezustand)"),
    (660.0, 15.0, "Chlorophyll-Bande im Roten (Pigmentabbau, Vergilbung)"),
    (730.0, 20.0, "\u00dcbergang zum NIR: Streuung dominiert, Information zur "
                  "Gewebestruktur und Partikelgr\u00f6sse"),
    (840.0, 15.0, "schwache Wasserbande (O-H, 3. Oberschwingung)"),
    (910.0, 15.0, "C-H-Bande (3. Oberschwingung, Fett- und Zuckeranteil)"),
    (970.0, 20.0, "Wasserbande (O-H, 2. Oberschwingung, Feuchtegehalt)"),
    (1190.0, 20.0, "C-H-Bande (2. Oberschwingung, Fett- und Zuckeranteil)"),
    (1450.0, 25.0, "starke Wasserbande (O-H, 1. Oberschwingung) - im NIR meist die "
                   "dominante Absorption"),
    (1720.0, 25.0, "C-H-Bande (1. Oberschwingung, Lipide/Fette)"),
    (1940.0, 30.0, "sehr starke Wasser-Kombinationsbande (O-H, Feuchte)"),
    (2100.0, 30.0, "O-H/C-O-Kombinationsbanden (St\u00e4rke, Zucker)"),
    (2270.0, 25.0, "C-H-Kombinationsbande (Zucker)"),
    (2350.0, 25.0, "CH2-Kombinationsbande (Cellulose, Zellwandsubstanz)"),
]

_CHART_EXPLANATIONS = {
    "quality_bar": "die Qualit\u00e4tsbewertung der einzelnen Analysebereiche als "
                  "Balkendiagramm: Jeder Balken ist ein Bereich (z. B. "
                  "Spektralanalyse, Kalibration), die Balkenh\u00f6he die erreichte "
                  "Punktzahl. So sieht man auf einen Blick, welche Bereiche "
                  "gut liefen und wo Handlungsbedarf besteht.",
    "spectrum": "das aufgenommene Spektrum der Messdaten. Die x-Achse zeigt die "
                "Wellenl\u00e4nge in Nanometern (nm), die y-Achse die gemessene "
                "Intensit\u00e4t. Auff\u00e4llige Erh\u00f6hungen (Peaks) und "
                "Einbr\u00fcche (Absorptionsbanden) zeigen, bei welchen "
                "Wellenl\u00e4ngen die Probe Licht absorbiert - daraus l\u00e4sst "
                "sich auf Inhaltsstoffe wie Wasser, Zucker oder Pigmente "
                "schliessen (siehe Interpretation der Spektren).",
    "similarity_top3": "die Messung (schwarze Kurve) zusammen mit den drei "
                       "\u00e4hnlichsten Spektren aus der Datenbank und dem "
                       "Projekt. Der \u00c4hnlichkeitswert (Sim) in der "
                       "Legende liegt nahe 1, wenn zwei Spektren fast "
                       "identisch sind. \u00dcberlappen sich die Kurven, "
                       "handelt es sich vermutlich um \u00e4hnliche Proben.",
    "sensor_dashboard": "das Sensorqualit\u00e4ts-Dashboard mit vier Bereichen: "
                        "(A) eine Kontrollkarte (Shewhart), bei der jede "
                        "Messung als Punkt mit einem \u00b13\u03c3-Toleranzband "
                        "eingetragen ist - Punkte ausserhalb des Bandes "
                        "deuten auf eine systematische Ver\u00e4nderung (Drift) "
                        "hin; (B) alle Messkurven \u00fcbereinander, in denen "
                        "eine systematische Verschiebung als Drift sichtbar "
                        "wird; (C) ein Box-Plot pro Kanal, der zeigt, welche "
                        "Wellenl\u00e4ngen die gr\u00f6sste Streuung (Rauschen) "
                        "haben; (D) eine Ampel-Anzeige des Gesamt-Scores mit "
                        "Teilwerten f\u00fcr Drift, Offset und Rauschen.",
    "score_plot": "den Score-Plot der Hauptkomponentenanalyse (PCA - ein "
                  "Verfahren, das die vielen Wellenl\u00e4ngen zu wenigen "
                  "\u201eHauptkomponenten\u201c zusammenfasst). Jeder Punkt ist "
                  "eine Messung; nah beieinanderliegende Punkte sind "
                  "\u00e4hnliche Proben, einzelne Randpunkte sind m\u00f6gliche "
                  "Ausreisser.",
    "loading_plot": "die Ladungen (Loadings) der Hauptkomponenten: Sie zeigen, "
                    "welche Wellenl\u00e4ngen jede Hauptkomponente am st\u00e4rksten "
                    "pr\u00e4gen. Grosse positive oder negative Ladungen bedeuten "
                    "grossen Einfluss.",
    "biplot": "Scores und Ladungen kombiniert: Die Punkte sind die Messungen, "
              "die Vektoren die Wellenl\u00e4ngen. Zeigt ein Vektor zu einer "
              "Messgruppe, tr\u00e4gt die entsprechende Wellenl\u00e4nge zur "
              "Trennung dieser Gruppe bei.",
    "scree_plot": "den Scree-Plot: die Gr\u00f6sse (Eigenwert) jeder "
                  "Hauptkomponente, absteigend sortiert. Wird die Kurve flach, "
                  "liefern weitere Komponenten kaum zus\u00e4tzliche Information - "
                  "dort wird die Componentenzahl gew\u00e4hlt.",
    "r2_per_wavelength": "welchen Anteil der Streuung (R\u00b2, "
                          "Bestimmtheitsmass) jede Hauptkomponente pro "
                          "Wellenl\u00e4nge erkl\u00e4rt. Hohe S\u00e4ulen "
                          "markieren Spektralbereiche mit viel Information.",
    "spe_plot": "den Standardized Prediction Error (SPE) pro Messung: einen "
                "Abstand zum Modell. Ausreisser nach rechts weichen vom "
                "Modell ab und sollten kontrolliert werden.",
    "prediction_vs_actual": "die Modellg\u00fcte des neuronalen Netzes: Jeder "
                            "Punkt ist eine Messung - auf der x-Achse der "
                            "wirkliche (referenzierte) Wert, auf der y-Achse "
                            "der vom Modell vorhergesagte. Je n\u00e4her die "
                            "Punkte an der gestrichelten Ideallinie (y = x) "
                            "liegen, desto besser die Vorhersage.",
    "loss_curves": "den Trainings- und Validierungs-Loss pro Epoche. Der Loss "
                   "ist das Fehlermass w\u00e4hrend des Lernens. Sinkt die "
                   "Kurve nur beim Training, w\u00e4hrend der Validierungs-Loss "
                   "wieder ansteigt, \u00fcberlappt das Modell die Daten "
                   "(Overfitting).",
    "shap_summary": "die globale Wichtigkeit jeder Wellenl\u00e4nge (per "
                    "Permutation berechnet): Wird eine Wellenl\u00e4nge "
                    "durchgeschmischt und das Ergebnis verschlechtert sich "
                    "stark, ist diese Wellenl\u00e4nge wichtig f\u00fcr die "
                    "Vorhersage.",
    "shap_waterfall": "die lokale Erkl\u00e4rung EINER Messung: Wird eine "
                      "Wellenl\u00e4nge neutral \u00fcberschrieben (Occlusion), "
                      "\u00e4ndert sich die Vorhersage um den eingetragenen "
                      "Betrag - so sieht man, welche Wellenl\u00e4ngen diese "
                      "eine Vorhersage treiben.",
    "saliency_map": "den Betrag des Gradienten \u2202Ausgabe/\u2202Eingabe: "
                    "helle Bereiche sind Wellenl\u00e4ngen, an denen eine kleine "
                    "\u00c4nderung der Intensit\u00e4t die Vorhersage stark "
                    "\u00e4ndert.",
    "grad_cam": "die aktivierten spektralen B\u00e4nder im Faltungsnetz (CNN, "
                "convolutional neural network - ein Netz, das lokale Muster "
                "im Spektrum erkennt): helle Zonen sind B\u00e4nder, die das "
                "Netz f\u00fcr die Vorhersage nutzt.",
    "attention_weights": "die gelernten Aufmerksamkeitsgewichte: Das Netz "
                         "gewichtet jede Wellenl\u00e4nge vor der Zusammenfassung; "
                         "hohe Gewichte markieren die \u201ebetrachteten\u201c "
                         "Wellenl\u00e4ngen.",
    "ref_vs_pred": "die Kalibrierg\u00fcte: Referenzwert gegen die "
                   "kreuzvalidierte Vorhersage (PLS). Die Kreuzvalidierung "
                   "l\u00e4sst jedes Sample einmal aussen vor und testet daran "
                   "- die Punkte liegen also nicht im Trainingssatz. R\u00b2cv "
                   "und RMSECV stehen im Titel.",
    "reg_coefficients": "die Regressionskoeffizienten pro Wellenl\u00e4nge - "
                        "die zentrale Erkl\u00e4rgrafik: Positive S\u00e4ulen "
                        "erh\u00f6hen die Vorhersage mit steigender Intensit\u00e4t, "
                        "negative senken sie. Grosse Betr\u00e4ge zeigen die "
                        "Wellenl\u00e4ngen, \u00fcber die das Modell den Gehalt "
                        "\u201elesieht\u201c.",
    "rmsecv_vs_n": "den Kreuzvalidierungsfehler (RMSECV) in Abh\u00e4ngigkeit "
                   "von der Anzahl der PLS-Komponenten (Modellkomplexit\u00e4t). "
                   "Das Minimum (rote Linie) ist die optimale Componentenzahl: "
                   "mehr Komponenten f\u00fchren zu Overfitting, weniger "
                   "unternutzen die Information.",
}

_OPTION_EXPLANATIONS = [
    ("drift", "Drift ist eine langsame systematische Ver\u00e4nderung des "
              "Sensorsignals; sie verf\u00e4lscht alle nachfolgenden Messungen "
              "in dieselbe Richtung."),
    ("rauschen", "Rauschen ist zuf\u00e4llige Messschwankung; mitteln \u00fcber "
                 "mehrere Replikate reduziert es um den Faktor "
                 "\u221aMessanzahl."),
    ("offset", "Ein Offset ist ein konstanter Versatz der Basislinie, oft durch "
               "veraltete Dunkel- oder Weissreferenz verursacht."),
    ("kalibrier", "Eine Kalibrierung gleicht das Modell mit Proben bekannten "
                  "Gehalts ab; ohne sie ist die absolute Vorhersage nicht "
                  "verl\u00e4sslich."),
    ("referenz", "Referenzmessungen an einem stabilen Standard kontrollieren, "
                 "ob sich Sensor oder Probenvorlage \u00fcber die Zeit "
                 "ver\u00e4ndern."),
    ("warm-up", "Viele Sensoren brauchen eine Aufw\u00e4rmphase, bis die "
                "Elektronik thermisch stabil ist; erste Messungen sind dann "
                "weniger reproduzierbar."),
    ("messzeit", "L\u00e4ngere Integrationszeiten sammeln mehr Licht und "
                 "verbessern das Signal-Rausch-Verh\u00e4ltnis."),
]


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def interpret_spectra(wavelengths: List[Any], intensities: List[Any],
                      analyte: Optional[str] = None) -> List[str]:
    """German plain-text sentences assigning the measured range to NIR/VIS
    bands. Only bands inside the measured range are mentioned."""
    if not wavelengths:
        return []
    wl = sorted(float(w) for w in wavelengths if w is not None)
    if not wl:
        return []
    lo, hi = wl[0], wl[-1]
    sentences = [
        f"Der Messbereich umfasst {lo:.0f} bis {hi:.0f} nm und liegt damit "
        + ("im sichtbaren (VIS) und nahen infraroten (NIR) Bereich."
           if lo < 700 and hi > 700 else
           ("vollst\u00e4ndig im sichtbaren Bereich (VIS)."
            if hi <= 700 else "im nahen Infrarot (NIR)."))
        + " Im NIR absorbieren vor allem Oberschwingungen von O-H- (Wasser, "
          "Zucker) und C-H-Bindungen (Fett, Zucker, Zellwand) - deshalb "
          "eignet sich der Bereich zur Gehaltsbestimmung ohne "
          "Probenvorbereitung.",
    ]
    hits = [b for b in _BANDS if any(abs(w - b[0]) <= b[1] for w in wl)]
    for center, _tol, text in hits:
        near = min(wl, key=lambda w: abs(w - center))
        sentences.append(f"Der Bereich um {near:.0f} nm entspricht "
                         f"{text}.")
    if analyte:
        sentences.append(
            f"Der Zielwert ({analyte}) wird im NIR vor allem \u00fcber "
            "O-H- und C-H-Oberschwingungen getragen: Gehalts\u00e4nderungen "
            "zeigen sich direkt als Intensit\u00e4ts\u00e4nderung in den "
            "jeweiligen Bindungsbanden; die Regressionskoeffizienten der "
            "Kalibration zeigen, welche Bereiche das Modell konkret nutzt.")
    else:
        sentences.append(
            "Der Zielwert der Kalibration wird im NIR \u00fcber O-H- und "
            "C-H-Oberschwingungen getragen; die Regressionskoeffizienten "
            "(siehe Kalibration) zeigen, welche Bereiche das Modell konkret "
            "nutzt.")
    return sentences


def _find_section(per_agent: List[Dict[str, Any]], agent: str) -> Optional[Dict[str, Any]]:
    return next((s for s in per_agent if s.get("agent") == agent), None)


def _grade_r2(r2: float) -> str:
    if r2 >= 0.9:
        return "sehr gut"
    if r2 >= 0.8:
        return "gut"
    if r2 >= 0.6:
        return "brauchbar f\u00fcr Screening-Zwecke"
    if r2 >= 0.4:
        return "eingeschr\u00e4nkt"
    return "unzureichend f\u00fcr quantitative Aussagen"


def _dataset_target_name(datasets: List[Dict[str, Any]]) -> Optional[str]:
    """Return the calibration target recorded at ingest (target-agnostic).

    OP36: the analyte is no longer hardcoded to Brix - it comes from the
    target_name metadata captured during wide-format ingest. None when no
    dataset recorded a target (then the report stays neutral).
    """
    for dataset in datasets or []:
        name = (dataset.get("metadata") or {}).get("target_name")
        if name:
            return str(name)
    return None

def model_quality_paragraphs(per_agent: List[Dict[str, Any]],
                              target_name: Optional[str] = None) -> List[str]:
    """Assess the model quality from the real agent results (R2, RMSE).
    PLS = Partial Least Squares (ein regressionsverfahren, das viele
    korrelierte Wellenl\u00e4ngen zu wenigen Komponenten zusammenfasst)."""
    paragraphs: List[str] = []
    calibration = _find_section(per_agent, "calibration")
    neural = _find_section(per_agent, "neural_network")

    r2_scores: List[Tuple[str, float]] = []
    rmse_values: List[Tuple[str, float]] = []
    if calibration:
        data = calibration.get("data") or {}
        best = data.get("best_r2_score")
        if best is not None:
            r2_scores.append(("PLS-Kalibration (kreuzvalidiert)", float(best)))
        for name, result in (data.get("method_results") or {}).items():
            mean = result.get("mean_r2") if isinstance(result, dict) else None
            if mean is not None:
                r2_scores.append((f"PLS-Methode {name} (kreuzvalidiert)",
                                 float(mean)))
    if neural:
        data = neural.get("data") or {}
        for name, result in (data.get("model_results") or {}).items():
            if not isinstance(result, dict):
                continue
            r2 = result.get("r2_score")
            if r2 is not None:
                model_note = ("CNN (convolutional neural network, ein Netz "
                              "mit Faltungsschichten f\u00fcr lokale Muster)"
                              if name == "CNN" else name)
                r2_scores.append((model_note, float(r2)))
            rmse = result.get("rmse")
            if rmse is not None:
                rmse_values.append((name, float(rmse)))

    if r2_scores:
        best_label, best_r2 = max(r2_scores, key=lambda t: t[1])
        lines = [
            f"Das beste Modell ({_esc(best_label)}) erreicht ein "
            f"R\u00b2 = {best_r2:.3f}. R\u00b2 (Bestimmtheitsmass) sagt aus, "
            "wie viel der Streuung der Referenzwerte das Modell erkl\u00e4rt "
            "(1 = perfekte Vorhersage, 0 = nutzlos). Das ist "
            f"{_grade_r2(best_r2)}.",
        ]
        for label, r2 in r2_scores:
            if (label, r2) != (best_label, best_r2):
                lines.append(f"Zum Vergleich: {label} erreicht "
                             f"R\u00b2 = {r2:.3f} ({_grade_r2(r2)}).")
        paragraphs.append(" ".join(lines))
    else:
        paragraphs.append(
            "Es liegen keine kreuzvalidierten G\u00fctemasse vor - eine "
            "Bewertung der Modellg\u00fcte ist mit diesen Daten nicht "
            "m\u00f6glich.")

    if rmse_values:
        target_unit = target_name if target_name else "Zieleinheit"
        for name, rmse in rmse_values:
            paragraphs.append(
                f"Der {name}-Root Mean Square Error (RMSE) betr\u00e4gt "
                f"{rmse:.3f} {target_unit} - die Vorhersage weicht im Mittel "
                f"um etwa {rmse:.1f} {target_unit} vom Referenzwert ab. "
                "F\u00fcr "
                "eine Freigabemessung sollte der Fehler deutlich kleiner als "
                "die relevante Gehaltsdifferenz der Proben sein.")
        paragraphs.append(
            "Ein echter RMSEP (Root Mean Square Error of Prediction, Fehler "
            "auf einer unabh\u00e4ngigen Validierungsstichprobe) liegt nicht "
            "vor: Die Modelle wurden \u00fcber Kreuzvalidierung gepr\u00fcft. "
            "RMSECV (Kreuzvalidierungsfehler) ist damit der beste verf\u00fcgbare "
            "Sch\u00e4tzer - er ist meist etwas optimistischer als der RMSEP, "
            "weil jedes Sample beim Training der anderen F\u00e4ltter gesehen "
            "wird.")
    return paragraphs


def error_source_items(per_agent: List[Dict[str, Any]]) -> List[str]:
    """Possible error sources: concrete findings from the agents plus the
    general NIR-specific effects."""
    items: List[str] = []
    spectral = _find_section(per_agent, "spectral_analysis")
    if spectral:
        issues = (spectral.get("data") or {}).get("issues_detected") or []
        if issues:
            items.append("Die Spektralanalyse meldet konkrete Auff\u00e4lligkeiten: "
                         + "; ".join(str(i) for i in issues) + ".")
    sensor = _find_section(per_agent, "sensor_quality")
    if sensor:
        data = sensor.get("data") or {}
        findings = []
        if data.get("drift_detected"):
            findings.append("eine Drift \u00fcber die Messreihe")
        if data.get("noise_detected"):
            if data.get("noise_level") is not None:
                findings.append(f"erh\u00f6htes Rauschen "
                                f"(Level {float(data['noise_level']):.3f})")
            else:
                findings.append("erh\u00f6htes Rauschen")
        if data.get("offset_detected"):
            findings.append("einen Baseline-Offset")
        if findings:
            items.append("Die Sensorpr\u00fcfung erkennt " + " sowie ".join(findings)
                         + " - das sind direkte Messfehlerquellen.")
    items.extend([
        "Streulichteffekte (Multiplicative/Additive Scatter): Unebene oder "
        "inkonsistente Probenoberfl\u00e4chen lenken Licht unterschiedlich, "
        "was das Spektrum insgesamt hebt oder senkt, ohne chemische "
        "Ursache. Normalisierung (z. B. SNV) oder Ableitungen reduzieren "
        "diesen Effekt.",
        "Ungleichm\u00e4ssige Probenverteilung: Setzen sich Partikel ab oder "
        "ist die Probe inhomogen, misst der Sensor je nach Position etwas "
        "anderes - mehrere Messungen pro Probe und Mischen reduzieren den "
        "Fehler.",
        "Temperatur- und Feuchteeinfluss: NIR-Wasserbanden verschieben sich "
        "mit der Temperatur; Proben sollten unter definierten Bedingungen "
        "gemessen werden.",
        "St\u00f6rsignale durch Umgebungslicht, Bewegung der Probe w\u00e4hrend "
        "der Integration oder Elektronik\u00fcbersteuerung (S\u00e4ttigung) - "
        "ges\u00e4ttigte Messkan\u00e4le sind unbrauchbar und sollten "
        "ausgeschlossen werden.",
    ])
    return items


def figure_explanations(per_agent: List[Dict[str, Any]],
                        overview_keys: Optional[List[str]] = None) -> List[Tuple[int, str]]:
    """(number, explanation) for every figure in report order. overview_keys
    are the chart keys rendered before the agent sections (Messdaten-Plot,
    Bewertungs-Plot)."""
    figures: List[Tuple[int, str]] = []
    counter = 0
    for key in (overview_keys or []):
        counter += 1
        explanation = _CHART_EXPLANATIONS.get(key) or \
            "eine Übersichtsgrafik der Messdaten und Bewertung."
        figures.append((counter, explanation))
    for section in per_agent:
        charts = section.get("charts") or {}
        for key, url in (charts or {}).items():
            if not url:
                continue
            counter += 1
            explanation = _CHART_EXPLANATIONS.get(key)
            if explanation is None:
                explanation = ("eine Grafik aus dem Bereich "
                               f"{section.get('title', section.get('agent', 'Analyse'))}.")
            figures.append((counter, explanation))
    return figures


def _explain_option(option: str) -> str:
    lowered = option.lower()
    for needle, explanation in _OPTION_EXPLANATIONS:
        if needle in lowered:
            return f"{option} <span class=\"muted\">({explanation})</span>"
    return option


def conclusion_sections(per_agent: List[Dict[str, Any]],
                        crew_results: Dict[str, Any],
                        overall_quality: Optional[float] = None) -> Tuple[List[str], List[str]]:
    """(summary sentences, optimization options) from the real results."""
    r2_scores = []
    calibration = _find_section(per_agent, "calibration")
    neural = _find_section(per_agent, "neural_network")
    if calibration and (calibration.get("data") or {}).get("best_r2_score") is not None:
        r2_scores.append(float(calibration["data"]["best_r2_score"]))
    if neural:
        for result in ((neural.get("data") or {}).get("model_results") or {}).values():
            if isinstance(result, dict) and result.get("r2_score") is not None:
                r2_scores.append(float(result["r2_score"]))
    best_r2 = max(r2_scores) if r2_scores else None

    summary = []
    if overall_quality is not None:
        summary.append(
            f"Die Gesamtqualit\u00e4t der Analyse betr\u00e4gt "
            f"{float(overall_quality):.1f} von 100 Punkten.")
    if best_r2 is not None:
        summary.append(
            f"Die beste gefittete Kalibration erreicht ein "
            f"R\u00b2 = {best_r2:.3f} ({_grade_r2(best_r2)}); "
            "die Vorhersagekraft ist damit "
            + ("f\u00fcr quantitative Anwendungen brauchbar."
               if best_r2 >= 0.6 else
               "derzeit eher f\u00fcr Screening-Zwecke geeignet."))
    num_sections = len([s for s in per_agent if s.get("status") == "completed"])
    if num_sections:
        summary.append(
            f"{num_sections} Analysebereiche wurden vollst\u00e4ndig "
            "durchgef\u00fchrt; die Grafiken im Diskussionsteil erl\u00e4utern "
            "jedes Ergebnis.")
    if not summary:
        summary.append("Es liegen keine vollst\u00e4ndigen Ergebnisse vor.")

    options: List[str] = []
    for section in per_agent:
        recs = (section.get("recommendations")
                or (section.get("data") or {}).get("recommendations")
                or (section.get("data") or {}).get("optimization_recommendations")
                or [])
        for rec in recs:
            text = str(rec)
            if text and text not in options:
                options.append(text)
    for rec in crew_results.get("recommendations") or []:
        text = str(rec)
        if text and text not in options:
            options.append(text)
    if not options:
        options.append(
            "Mehr Kalibrationsproben \u00fcber den gesamten Gehaltsbereich "
            "aufnehmen: Ein Modell kann nur den Bereich lernen, den die "
            "Kalibration abdeckt.")
    options = [_explain_option(o) for o in options]
    return summary, options


def build_student_sections(per_agent: List[Dict[str, Any]],
                           crew_results: Dict[str, Any],
                           datasets: List[Dict[str, Any]],
                           overview_keys: Optional[List[str]] = None) -> Dict[str, str]:
    """Render the three student sections as HTML strings (Diskussion,
    Fazit, Literatur). Falls niemals leer - der Text degrade auf allgemeine
    Erl\u00e4uterungen."""
    wavelengths: List[Any] = []
    intensities: List[Any] = []
    if datasets:
        preview = datasets[0].get("preview") or {}
        wavelengths = datasets[0].get("wavelengths") or preview.get("wavelengths") or []
        intensities = datasets[0].get("intensities") or preview.get("intensities") or []

    analyte = None
    calibration = _find_section(per_agent, "calibration")
    if calibration:
        analyte = _dataset_target_name(datasets)

    spectra_sentences = interpret_spectra(wavelengths, intensities, analyte=analyte)
    spectra_html = "".join(f"<p>{s}</p>" for s in spectra_sentences) or \
        "<p class=\"muted\">Keine Spektraldaten f\u00fcr eine Interpretation.</p>"

    quality_html = "".join(f"<p>{p}</p>"
                           for p in model_quality_paragraphs(
                               per_agent, target_name=analyte))

    errors = error_source_items(per_agent)
    errors_html = "".join(f"<li>{_esc(e)}</li>" for e in errors)

    figures = figure_explanations(per_agent, overview_keys=overview_keys)
    figures_html = "".join(
        f"<li><b>Abbildung {number}:</b> {explanation}</li>"
        for number, explanation in figures) or \
        '<li class="muted">Keine Grafiken vorhanden.</li>'

    discussion = (
        "<h3>Interpretation der Spektren</h3>" + spectra_html +
        "<h3>Bewertung der Modellg\u00fcte</h3>" + quality_html +
        "<h3>M\u00f6gliche Fehlerquellen</h3><ul>" + errors_html + "</ul>" +
        "<h3>Erkl\u00e4rung der Grafiken</h3><ul>" + figures_html + "</ul>"
    )

    overall = crew_results.get("overall_quality_score")
    summary, options = conclusion_sections(per_agent, crew_results,
                                          overall_quality=overall)
    summary_html = "".join(f"<li>{_esc(s)}</li>" for s in summary)
    options_html = "".join(f"<li>{o}</li>" for o in options)
    conclusion = (
        "<h3>Zusammenfassung der wichtigsten Erkenntnisse</h3><ul>"
        + summary_html + "</ul>"
        "<h3>Optimierungsoptionen</h3><ol>" + options_html + "</ol>"
    )

    literature = "".join(
        f'<li>{entry}<br><span class="muted">{annotation}</span></li>'
        for entry, annotation in _LITERATURE)

    return {"discussion": discussion, "conclusion": conclusion,
            "literature": literature}
