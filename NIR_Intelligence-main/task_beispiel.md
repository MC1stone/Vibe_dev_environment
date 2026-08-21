Für ein **NIR-Analysesystem (Near Infrared Spectroscopy)** innerhalb deiner agentischen Codestral/CrewAI/MCP-Architektur könnte ein AI-Task wie folgt definiert werden.

# AI-Task: NIR Spectrum Analysis

## Zweck

Automatische Analyse von NIR-Spektraldaten zur Qualitätskontrolle, Anomalieerkennung und Vorhersage chemischer Eigenschaften.

## Agent

agent: NIRAnalysisAgent

role: Spectroscopy Specialist

goal: Analyse von NIR-Spektren und automatische Qualitätsbewertung

## Task-Definition

task:

name: Analyze_NIR_Spectrum

description: >

Analysiert eingehende NIR-Spektren,

erkennt Ausreißer, bewertet die Datenqualität,

erstellt Vorhersagemodelle und generiert

Verbesserungsvorschläge.

input:

\- spectrum.csv

\- calibration_model.pkl

\- metadata.json

steps:

\- Datenvalidierung

\- Vorverarbeitung

\- Baseline-Korrektur

\- Rauschfilterung

\- PCA Analyse

\- Anomalieerkennung

\- Vorhersage chemischer Parameter

\- Qualitätsbewertung

\- Berichtserstellung

output:

\- quality_score

\- anomaly_report

\- prediction_results

\- recommendations

---

# MCP Integration

Der Agent nutzt mehrere MCP-Server:

mcp_servers:

\- faiss_mcp

\- weaviate_mcp

\- quarto_mcp

\- docker_mcp

### Funktion

**Faiss MCP**

- Ähnliche Spektren finden
- Historische Messungen vergleichen

**Weaviate MCP**

- Wissensdatenbank
- Kalibrierungswissen
- Laborberichte

**Quarto MCP**

- Automatische PDF-Reports
- Dashboards

**Docker MCP**

- Analysecontainer überwachen

---

# Analyse-Workflow

NIR Rohdaten

│

▼

Datenprüfung

│

▼

Vorverarbeitung

│

▼

PCA Analyse

│

▼

Anomalieerkennung

│

▼

Modellvorhersage

│

▼

Qualitätsbewertung

│

▼

Feedback Agent

│

▼

Wissensdatenbank

---

# Beispiel-Output

{

"sample_id": "NIR-2026-001",

"quality_score": 94.2,

"anomaly_detected": false,

"predictions": {

"moisture": 12.4,

"protein": 18.7,

"fat": 6.2

},

"recommendation": "Probe innerhalb der Spezifikation"

}

---

# Feedback-Zyklus

Der Agent erzeugt automatisch:

feedback:

data_quality: excellent

model_confidence: 96%

drift_detected: false

retraining_required: false

Diese Ergebnisse werden anschließend an:

- QA Agent
- Knowledge Agent
- Feedback Agent
- Documentation Agent

weitergegeben.

---

## Erklärung einer NIR-Task-Datei

Falls die Datei beispielsweise `nir_analysis_task.yaml` heißt:

task_name: Analyze_NIR_Spectrum

agent: NIRAnalysisAgent

input_file: spectrum.csv

model: nir_calibration_v3

output_format: json

quality_threshold: 90

Bedeutung:

- **task_name**: Name des Analyseauftrags
- **agent**: Zuständiger Spezialisten-Agent
- **input_file**: Zu analysierende Spektraldaten
- **model**: Verwendetes Kalibrierungsmodell
- **output_format**: Format der Analyseergebnisse
- **quality_threshold**: Mindestqualität für eine erfolgreiche Messung

Wenn du die konkrete Datei hochlädst, kann ich sie Zeile für Zeile analysieren und die gesamte Funktion im NIR-System erläutern.