# Task-Datei: Entwicklung einer selbstoptimierenden NIR-Analyseplattform

**Projektname:** NIR Intelligence Platform (NIR-IP)

**Version:** 1.0

**Ziel:** Entwicklung einer lokalen, containerisierten Softwarelösung zur vollständigen Analyse von Nahinfrarotspektroskopie-Daten (NIR), die mithilfe mehrerer KI-Agenten automatisiert Datenqualität bewertet, Metadaten extrahiert, Kalibrationen optimiert, neuronale Netze trainiert und sämtliche Ergebnisse nachvollziehbar dokumentiert.

---

# 1. Systemarchitektur

## Technologiestack

### Entwicklungsumgebung

- UV Package Manager
- Python ≥ 3.12
- Virtuelle Umgebung (uv venv)

### Containerisierung

- Docker
- Docker Compose

### KI-Komponenten

- Ollama
- mistral:latest
- CrewAI

### Datenbanken

- PostgreSQL (Metadaten)
- Weaviate (Vektordatenbank)
- FAISS (Ähnlichkeitssuche)

### Dokumentation

- Quarto
- Mermaid
- Plotly

### Frontend

- Django
- HTMX
- Bootstrap

---

# 2. Hauptanforderungen

## Funktionale Anforderungen

### Datenimport

Unterstützung für:

- CSV
- XLSX
- ASD
- OPUS
- JCAMP-DX
- SPA
- MAT-Dateien

---

### Automatische Metadatenextraktion

Das System soll selbstständig:

- Instrumenttyp erkennen
- Messdatum extrahieren
- Bediener identifizieren
- Probentyp erkennen
- Kalibrationsinformationen erfassen
- Wellenlängenbereich bestimmen
- Auflösung erkennen

Anschließend erfolgt eine automatische Bewertung:

Metadaten:

erforderlich:

\- Spektraldaten

\- Wellenlängen

\- Gerät

\- Messzeitpunkt

empfohlen:

\- Temperatur

\- Luftfeuchtigkeit

\- Bediener

optional:

\- Standort

\- Bemerkungen

---

# 3. Agentensystem

## Master Orchestrator Agent

Aufgaben:

- Workflowsteuerung
- Qualitätskontrolle
- Konfliktmanagement
- Ergebnisaggregation
- Selbstoptimierung

---

# 4. CrewAI Agenten

## Agent 1: Datenvorbereitung

### Aufgaben

- Einlesen
- Bereinigung
- Missing Values
- Ausreißererkennung
- Normalisierung

### Verfahren

- SNV
- MSC
- Savitzky-Golay
- Baseline Correction
- Detrending

### Ausgabe

{

"qualität": 95,

"fehlende_werte": 0.1,

"ausreisser": 2

}

---

## Agent 2: Sensor- und Qualitätsanalyse

### Aufgaben

Prüfung auf:

- Drift
- Offsetfehler
- Rauschen
- Temperaturfehler
- Feuchtigkeitseinflüsse
- Referenzfehler

### Verfahren

- PCA
- Hotelling T²
- Mahalanobis
- SPC Charts

### Ausgabe

{

"drift": 0.02,

"signal_noise": "gut",

"sensorzustand": "ok"

}

---

## Agent 3: Statistische Analyse

### Aufgaben

- PCA
- PLS
- PCR
- Clusteranalyse
- ANOVA
- Korrelation

### Ausgabe

{

"modell": "PLS",

"r2": 0.97,

"rmsep": 0.13

}

---

## Agent 4: Neuronales Netzwerk

### Pflichtanforderung

Muss immer parallel aktiv sein.

### Verfahren

- MLP
- CNN für Spektren
- Autoencoder
- Transfer Learning

### Aufgaben

- Kalibration
- Regression
- Klassifikation

### Bewertung

{

"modell": "CNN",

"r2": 0.985,

"rmse": 0.08

}

---

## Agent 5: Optimierungsagent

### Aufgaben

Automatische Optimierung von:

- Vorverarbeitung
- Kalibration
- Hyperparametern
- Modellarchitekturen
- Embeddings

### Verfahren

- Bayesian Optimization
- Grid Search
- Evolutionäre Algorithmen

---

# 5. Weaviate Agent

## Aufgaben

Speicherung von:

- Spektren
- Modellen
- Reports
- Embeddings

### Retrieval

Semantic Search

Beispiel:

Finde ähnliche Spektren

mit Feuchtigkeitsgehalt > 10%

---

# 6. FAISS Agent

## Aufgaben

Ähnlichkeitssuche innerhalb der Spektrendatenbank

### Ausgabe

{

"spektrum_id": 123,

"ähnliche_spektren": 45,

"max_similarity": 98.3

}

---

# 7. Wellenlängen-Datenbank

Für jede Analyse:

## Durchführung

1. Peaks identifizieren
2. Datenbankvergleich
3. Vergleich ähnlicher Spektren
4. Zuordnung chemischer Gruppen

### Ergebnis

{

"peak": 1450,

"ähnliche_funde": 842,

"mittelwert_abstand": 1.4,

"wahrscheinliche_gruppe": "OH"

}

---

# 8. Kalibrationsmodul

## Automatische Kalibrationen

### Verfahren

- PLS
- PCR
- SVM
- Random Forest
- XGBoost
- CNN
- Ensemble Learning

### Vergleich

Ausgabe:

PLS:

R2: 0.95

PCR:

R2: 0.92

CNN:

R2: 0.98

Ensemble:

R2: 0.99

---

# 9. Selbstoptimierung

## Zyklus

Import

↓

Analyse

↓

Kalibration

↓

Evaluation

↓

Optimierung

↓

Neue Analyse

↓

Vergleich

↓

Dokumentation

Wiederholen bis:

Verbesserung < 0.1%

---

# 10. Bewertungsschema

## Datenqualität

| Kriterium         | Gewicht |
|-------------------|---------|
| Vollständigkeit   | 20 %    |
| Signalqualität    | 20 %    |
| Rauschverhältnis  | 20 %    |
| Metadatenqualität | 20 %    |
| Sensorzustand     | 20 %    |

---

## Modellqualität

| Kriterium          | Gewicht |
|--------------------|---------|
| R²                 | 30 %    |
| RMSE               | 20 %    |
| Stabilität         | 20 %    |
| Generalisierung    | 20 %    |
| Reproduzierbarkeit | 10 %    |

---

## Gesamtscore

90-100 = Exzellent

80-89 = Sehr gut

70-79 = Gut

60-69 = Ausreichend

<60 = Kritisch

---

# 11. Benutzerbericht

Nach jeder Analyse erhält der Benutzer:

## Metadatenbewertung

Metadaten:

Vollständigkeit: 92%

Bewertung: Sehr gut

Fehlend:

\- Umgebungsfeuchtigkeit

\- Probentemperatur

Empfehlung:

Beide Felder künftig erfassen.

---

## Analysevergleich

PLS:

Score: 92

PCR:

Score: 88

CNN:

Score: 97

Ensemble:

Score: 99

---

## KI-Begründung

Beispiel:

> Das Ensemblemodell wurde als Bestmodell gewählt, da es den höchsten R²-Wert besitzt, die geringste Vorhersageabweichung zeigt und bei Kreuzvalidierung die stabilsten Ergebnisse liefert.

---

## Verbesserungsvorschläge

Empfehlungen:

\- Mehr Referenzproben erfassen

\- Temperatur protokollieren

\- Wellenlängenbereich erweitern

\- Regelmäßige Dunkelreferenzmessung durchführen

---

# 12. Automatische Quarto-Dokumentation

Das System erzeugt für jede Analyse automatisch:

report.qmd

Enthalten sind:

- Projektbeschreibung
- Messdatenbeschreibung
- Metadatenbewertung
- Datenqualitätsbewertung
- Vorverarbeitungsschritte
- Driftanalyse
- Statistische Analyse
- Neuronale Netzwerkanalyse
- Kalibrationsvergleich
- Optimierungshistorie
- Wellenlängenvergleich
- Ähnlichkeitssuche
- Diagramme
- Python-Code
- Fazit

---

# 13. Abschlussreport

Der Abschlussreport muss mindestens enthalten:

### Metadaten

- Erkannte Metadaten
- Relevanzbewertung
- Fehlende Informationen

### Qualitätsbewertung

- Datenqualität
- Sensorqualität
- Modellqualität

### Beste Analyse

- Gewinner-Modell
- R²
- RMSE
- Begründung

### Neuronale Netzwerkanalyse

- Architektur
- Hyperparameter
- Leistung

### Wellenlängenvergleich

- Anzahl ähnlicher Peaks
- Peak-Abstände
- Ähnliche Messobjekte
- Häufigkeit des Auftretens

### Datenbankvergleich

- Weaviate Similarity Score
- FAISS Similarity Score
- Anzahl ähnlicher Spektren

### Optimierungsprotokoll

- Anzahl Iterationen
- Verbesserungen pro Iteration
- Finaler Performance-Gewinn

### Executive Summary

- Datenqualität
- Messsicherheit
- Kalibrationsqualität
- Anwendbarkeit des Modells
- Handlungsempfehlungen für den Anwender

**Abnahmekriterium:** Das System gilt als erfolgreich, wenn alle Agenten fehlerfrei abgeschlossen haben, mindestens ein statistisches Modell und ein neuronales Netzwerk parallel bewertet wurden, sämtliche Optimierungen dokumentiert sind und ein vollständiger Quarto-Report erzeugt wurde.