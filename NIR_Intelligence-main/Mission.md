# NIR INTELLIGENCE PLATFORM (NIR-IP)

Version: 1.0

## Mission

Entwickle eine vollständig lokale, containerisierte und selbstoptimierende Softwareplattform zur Auswertung von Nahinfrarotspektroskopie-Daten (NIR).

Die Plattform verwendet:

- UV (virtuelle Python-Umgebung)
- Docker
- Ollama
- Mistral:latest
- CrewAI
- Weaviate
- FAISS
- PostgreSQL
- Django
- MCP Server
- Quarto
- Flower Federated Learning

---

# Master Objective

Die Plattform soll:

 1. Rohdaten importieren.
 2. Metadaten automatisch erkennen.
 3. Relevante und irrelevante Metadaten unterscheiden.
 4. Datenqualität bewerten.
 5. Sensorfehler erkennen.
 6. Statistische Analysen durchführen.
 7. Neuronale Netzwerkanalysen parallel durchführen.
 8. Kalibrationen erstellen.
 9. Kalibrationen optimieren.
10. Ähnliche Spektren identifizieren.
11. Wellenlängen mit Datenbank vergleichen.
12. Ergebnisse dokumentieren.
13. Sich selbst kontinuierlich verbessern.

---

# Verpflichtende Startsequenz

Jeder Agent MUSS vor jeder Ausführung folgende Dateien lesen:

1. [TASK.md](http://TASK.md)
2. task_definition.yaml
3. system_manifest.json

Keine Implementierung darf erfolgen, bevor alle drei Dateien eingelesen wurden.

---

# Agentensystem

## Master Implementation Agent

Verantwortlich für:

- Gesamtplanung
- Agentenorchestrierung
- Qualitätskontrolle
- Konfliktlösung
- Freigabe

---

## Data Preparation Agent

Aufgaben:

- Datenimport
- Datenbereinigung
- Ausreißeranalyse
- Normalisierung

---

## Sensor Quality Agent

Aufgaben:

- Driftanalyse
- Rauschbewertung
- Instrumentenüberwachung
- Fehleridentifikation

---

## Statistical Analysis Agent

Aufgaben:

- PCA
- PLS
- PCR
- ANOVA
- Clusteranalyse

---

## Neural Network Agent

Verpflichtend aktiv.

Aufgaben:

- CNN
- MLP
- Autoencoder
- Ensemble Modelle

Diese Analyse muss immer parallel zur statistischen Analyse ausgeführt werden.

---

## Calibration Agent

Aufgaben:

- PLS Kalibration
- PCR Kalibration
- SVM Kalibration
- Random Forest
- XGBoost
- CNN Kalibration

---

## Metadata Agent

Aufgaben:

- Extraktion
- Bewertung
- Priorisierung
- Datenqualität

---

## Weaviate Agent

Aufgaben:

- Speicherung von Embeddings
- Semantic Search
- Similarity Search

---

## FAISS Agent

Aufgaben:

- Spektrenvergleich
- Peakvergleich
- Nearest Neighbour Suche

---

## PostgreSQL Agent

Aufgaben:

- Metadatenverwaltung
- Relationale Speicherung

---

## Django Agent

Aufgaben:

- UI
- Backend
- APIs
- Benutzerverwaltung

---

## MCP Agent

Aufgaben:

- Tool-Integration
- Externe Schnittstellen

---

## Quarto Agent

Aufgaben:

- Vollständige Dokumentation
- Diagramme
- Reports

---

## Flower Agent

Aufgaben:

- Federated Learning
- Modellaggregation

---

# Iterationsregel

Die Plattform arbeitet iterativ.

Schleife:

Analyse → Evaluation → Optimierung → Reanalyse

bis:

ERRORS = 0 CRITICAL_WARNINGS = 0 OPEN_CHANGE_REQUESTS = 0

---

# Abschlussbericht

Der Report muss enthalten:

- Metadatenanalyse
- Metadatenbewertung
- Sensoranalyse
- Statistische Analyse
- Neuronale Netzwerkanalyse
- Kalibrationsvergleich
- Wellenlängenvergleich
- Similarity Analyse
- Optimierungsprotokoll
- Gesamtergebnis
- Handlungsempfehlungen