"""Template filter for plain-text chart explanations (OP60).

Maps chart keys (as produced by services/pca_charts.py, calibration_charts.py,
sensor_charts.py, similarity_charts.py, xai_charts.py, outlier_analysis.py)
to short German explanations for non-experts, rendered as a collapsible
dropdown next to each chart. Unknown keys fall back to a generic hint.
"""
from django import template

register = template.Library()

CHART_EXPLANATIONS = {
    # PCA (statistical agent)
    'score_plot': ('Streudiagramm der Messungen in den ersten beiden Hauptkomponenten '
                   '(PC1 vs. PC2). Ahnliche Punkte = ahnliche Spektren; Gruppen oder '
                   'Ausreisser fallen hier zuerst auf.'),
    'loading_plot': ('Beitrag jeder Wellenlange zu den Hauptkomponenten. Grosse '
                     'Ausschlaege zeigen, welche Wellenlangbereiche die Unterschiede '
                     'zwischen den Spektren treiben.'),
    'biplot': ('Kombination aus Score- und Loading-Plot: Messungen als Punkte, '
               'Wellenlangen als Pfeile. Pfeile in Richtung einer Punktgruppe zeigen, '
               'welche Wellenlangen diese Gruppe erzeugen.'),
    'scree_plot': ('Erklaerte Varianz je Hauptkomponente (absteigend). Zeigt, wie viele '
                   'Komponenten die Daten sinnvoll zusammenfassen - der Knick markiert '
                   'die interessante Anzahl.'),
    'r2_per_wavelength': ('Anteil der Varianz je Wellenlange, den das PCA-Modell '
                          'erklaert. Niedrige Werte markieren Bereiche mit Rauschen oder '
                          'Sensorproblemen.'),
    'spe_plot': ('Squared Prediction Error je Messung: der Abstand des Spektrums zum '
                 'PCA-Modell. Hohe Werte = Spektrum passt nicht zum gelernten Muster '
                 '(moglicher Ausreisser).'),
    # Similarity
    'similarity_top3': ('Ihr Spektrum (blau) gegenueber den drei aehnlichsten '
                        'Referenzspektren (gruen). Je deckungsgleicher die Kuruen, '
                        'desto aehnlicher die Proben.'),
    'spectrum': ('Die gemessene Spektralkurve mit Wellenlange (x) und Intensitaet (y). '
                 'Fake-Kurven werden nie angezeigt - fehlt die Kurve, fehlen die Messdaten.'),
    # Calibration
    'predicted_vs_measured': ('Vorhergesagte vs. gemessene Referenzwerte der Kalibration. '
                             'Punkte auf der Diagonalen = perfekte Vorhersage; die Streuung '
                             'daher ist der Kalibrationsfehler (RMSECV).'),
    'residuals': ('Kalibrationsreste: Differenz Vorhersage minus Messwert je Probe. '
                  'Muster in den Resten deuten auf systematische Fehler, gleichmaessige '
                  'Streung auf zufaelliges Rauschen.'),
    'regression_coefficients': ('Regressionskoeffizienten je Wellenlange. Grosse '
                                'Ausschlaege markieren Wellenlangen, die das Modell fuer '
                                'die Vorhersage nutzt.'),
    'rmse_cv': ('Mittlerer Vorhersagefehler (RMSE) ueber die Kreuzvalidierungs-Folds. '
                'Zeigt, wie gut das Modell auf ungesehene Daten generalisiert.'),
    # Sensor quality
    'drift': ('Sensor-Drift uber die Zeit: systematische Verschiebung der Messwerte. '
              'Ein Trend deutet auf eine Kalibrierungs- oder Umgebungsproblematik hin.'),
    'noise': ('Rauschniveau des Sensors: kurzzeitige Schwankungen der Intensitaet. '
              'Hohes Rauschen verschlechtert die Datenqualität und damit jede Analyse.'),
    'snr': ('Signal-Rausch-Verhaeltnis je Messung: Nutzen ueber Rauschen. '
            'Hohes Verhaeltnis = vertrauenswuerdige Messung.'),
    # XAI (neural network)
    'feature_importance': ('Wichtigkeit der Eingangsmerkmale (Wellenlangen) fuer das '
                           'neuronale Netz. Zeigt, auf welche Spektralbereiche das Modell '
                           'seine Vorhersage stuetzt.'),
    'shap': ('SHAP-Werte: Beitrag jeder Wellenlange zur einzelnen Vorhersage. Rot = '
             'erhoeht die Vorhersage, blau = senkt sie.'),
    # Outlier
    'outlier_scores': ('Ausreisser-Score je Messung (z. B. Mahalanobis-Distanz). '
                       'Punkte uber dem Schwellenwert sind Ausreisser-Kandidaten.'),
}

GENERIC_EXPLANATION = ('Diagramm zur Kontrolle der Datenqualitaet und der Analyse. '
                       'Achsen und Werte folgen den Messdaten; Details stehen im '
                       'Agenten-Bericht darunter.')


@register.filter
def chart_explanation(key, _unused=None):
    """Return the German explanation for a chart key."""
    return CHART_EXPLANATIONS.get(key, GENERIC_EXPLANATION)
