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
- Qdrant
- FAISS
- PostgreSQL
- Django
- MCP Server
- Quarto
- Ilias e learning platform
- Flower Federated Learning

---

# Master Objective

Die Plattform soll:

 1. Rohdaten importieren unabhängig von dem File Format.
 2. Metadaten automatisch erkennen.
 3. Relevante und irrelevante Metadaten unterscheiden.
 4. Datenqualität bewerten.
 5. Sensorfehler erkennen.
 6. Statistische Analysen durchführen.
 7. Neuronale Netzwerkanalysen parallel durchführen.
 8. Kalibrationen erstellen.
 9. Kalibrationen optimieren.
10. Einen Chatbot bereitstellen zum diskutieren der Ergebnisse.
11. Ähnliche Spektren identifizieren.
12. Wellenlängen mit Datenbank vergleichen.
13. Ergebnisse dokumentieren.
14. Die Spektren in der Software visualisieren und neu eingehende Daten mit vorhandenen Spektren vergleichen.
15. Sich selbst kontinuierlich verbessern und updaten in Abhängigkeit der genutzten OpenSource Software.

---

# Verpflichtende Startsequenz

Jeder Agent MUSS vor jeder Ausführung folgende Dateien lesen:

1. `TASK.md`
2. `task_definition.yaml`
3. `system_manifest.json`

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

## Qdrant Agent

Aufgaben:

- Speicherung von Embeddings
- Semantic Search
- Similarity Search

**Hinweis:** Weaviate ist out of scope; Qdrant ist der Ersatz für Vektor- und Embedding-Speicherung.

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

ERRORS = 0
CRITICAL_WARNINGS = 0
OPEN_CHANGE_REQUESTS = 0

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
