# Material und Methoden

> Vorlage für den Methodenteil eines wissenschaftlichen Papers zur NIR
> Intelligence Platform (NIR-IP). Alle Angaben basieren auf den
> Steuerdateien (`task_definition.yaml`, `system_manifest.json`), der
> Roadmap (`REPOSITORY_ALIGNMENT_AND_ROADMAP.md`) und den
> Abhängigkeitsmanifesten (`requirements*.txt`, `docker-compose*.yml`).
> Versionsnummern sind dem Repository zu entnehmen und vor Einreichung
> auf die tatsächlich eingesetzten Versionen zu prüfen.

## 2.1 Plattformübersicht und Systemarchitektur

Die Datenanalyse wurde mit der **NIR Intelligence Platform (NIR-IP, Version 1.0)**
durchgeführt, einem selbstoptimierenden Multi-Agenten-System zur Auswertung von
Nahinfrarot-Spektraldaten. Das System ist als CrewAI-Orchestrierung
(`crewai >= 0.1.0`) mit einem zentralen Master-Agenten (Orchestrierung,
Qualitätskontrolle, Konfliktlösung, Freigabe) und 30+ spezialisierten
Subagenten implementiert, die in definierten Schnittmengen zusammenarbeiten
(Master-, Data-Preparation-, Sensor-Quality-, Statistical-Analysis-,
Neural-Network-, Calibration-, Metadata-, Qdrant-, FAISS-, PostgreSQL-,
Django-, MCP-, Quarto-, Flower-, Chatbot- und ILIAS-Agent). Jede Agenten-Ausführung
durchläuft eine verpflichtende Startsequenz (Einlesen von `TASK.md`,
`task_definition.yaml` und `system_manifest.json`) sowie eine schriftliche
Selbstprüfung; eine Implementierung ohne erfolgte Startsequenz ist protokollseitig
ausgeschlossen.

## 2.2 Software-Umgebung und Containerisierung

Die Plattform läuft vollständig lokal in einer containerisierten Umgebung
(Tabelle 1). Die Ausführung erfolgt unter **Python 3.12** mit dem Paketmanager
**uv** (virtuelle Umgebung) und **Docker Compose** (Development- und
Produktions-Stack mit Healthchecks).

**Tabelle 1: Software-Komponenten der Ausführungsumgebung**

| Komponente | Version (Manifest) | Funktion |
|---|---|---|
| Python | 3.12 | Laufzeitumgebung |
| Docker / Docker Compose | containerisierte Services | Prozessisolation, Reproduzierbarkeit |
| PostgreSQL | 15 (alpine) | Relationale Metadaten- und Projektspeicherung |
| Qdrant | qdrant/qdrant (Compose-Pin) | Vektor-/Embedding-Speicherung, semantische Suche |
| FAISS | faiss-cpu >= 1.7.4 | Nearest-Neighbour-Spektralvergleich |
| Ollama + Mistral | ollama/ollama, `mistral:latest` | Lokales Large Language Model (Chatbot, RAG) |
| Redis | 7 (alpine) | Nachrichten-/Cache-Backend |
| Django + DRF | django >= 4.2, djangorestframework >= 3.14 | Web-Oberfläche, REST-API, Benutzerverwaltung |
| Flower | Flower-Server (Compose) | Federated-Learning-Koordination |
| ILIAS | srsolutions/ilias:9-php8.2-apache (MariaDB 10.11) | E-Learning-/Lehranbindung |
| Quarto | Reporting-Engine | Automatisierte Berichterstellung |

Wissenschaftliche Kernbibliotheken: `numpy >= 1.24`, `pandas >= 2.0`,
`scipy >= 1.10`, `scikit-learn >= 1.3`, `optuna >= 3.2`, `pybaselines >= 1.0`,
`spectra >= 0.0.11`, `h5py >= 3.9`. Neuronale Netze (CNN) werden bei verfügbarer
TensorFlow-Installation (`tensorflow >= 2.16`) trainiert und andernfalls
protokolliert als `deferred` übersprungen (graceful degradation).

## 2.3 Datenimport und formatunabhängige Datenhaltung

Der Datenimport erfolgt formatagnostisch über einen generischen
File-Handler-Agenten. Unterstützt werden textbasierte Tabellenformate (CSV, TXT),
JSON (parallele Arrays für Wellenlänge und Intensität), MATLAB-Dateien (`.mat`,
via `scipy.io`; benannte Arrays und 2-Spalten-Arrays) sowie das binäre
Galactic/Thermo-SPC-Format (Header-Parsing einschließlich Einheiten-Metadaten).
JMP-Exporte werden als tabellarische Formate über die Tabellen-Loader verarbeitet.
Alle Importpfade sind durch eine Testmatrix (`tests/test_s3_format_loaders.py`,
7 Tests) abgesichert; alle Daten werden in ein **einheitliches Spektral-Schema**
(Wellenlänge, Intensität, Einheiten, Metadaten) überführt, das als Kontrakt für
alle nachfolgenden Analyse- und Vergleichsschritte dient.

## 2.4 Geräteanbindung

Spektrometer werden über eine abstrakte Adapter-Schicht
(`devices/base_spectrometer.py`) integriert: ein einheitlicher Kontrakt für
Messdaten (einheitliches Spektral-Schema), Metadaten, Kalibrationsparameter,
Gerätestatus (Enum) und Capabilities (Wellenlängenbereich, Auflösung, Detektor).
Eine modellbasierte Registry erlaubt die Integration neuer Geräte ohne Änderung
des Plattform-Kerns. Implementierte Adapter: (i) DIY-Matchbox (USB-Kamera),
(ii) ESP32-S3-Kameraspektrometer (MQTT-Payload-Parsing), (iii) SparkFun Triad
(Qwiic/I²C; AS7262 + AS7263 + ML8511, 18 Kanäle, 410–940 nm). Die
Adapter-Konformität ist durch 26 automatisierte Tests
(`tests/test_s4_spectrometer_adapters.py`) verifiziert.

## 2.5 Datenvorverarbeitung

Die Vorverarbeitung ist konfigurierbar und umfasst Standard-Normal-Variante
(SNV), Multiplicative Scatter Correction (MSC), Savitzky-Golay-Filterung,
Baseline-Korrektur (pybaselines) und Detrending. Die Methodenauswahl wird
protokolliert, sodass jede Analyse reproduzierbar ist.

## 2.6 Metadaten-Extraktion und Datenqualität

Metadaten werden automatisiert extrahiert und klassifiziert. Obligate Kategorien:
Spektrum, Wellenlänge, Instrument, Aufnahmezeitpunkt; empfohlen: Operator,
Luftfeuchte, Temperatur; optional: Notizen, Ort. Die Datenqualität wird vor
Analysebeginn bewertet; irrelevante bzw. unvollständige Metadaten werden
gekennzeichnet und im Bericht ausgewiesen.

## 2.7 Sensor- und Qualitätsanalyse

Vor der eigentlichen Auswertung durchläuft jeder Datensatz eine
Sensorqualitätsprüfung mit den Kriterien Drift, Offset, Rauschen,
Referenzvalidität und Umwelteinfluss (Temperatur, Feuchte). Auffällige Sensoren
bzw. Messungen werden identifiziert und von der Analyse ausgeschlossen bzw.
markiert (Sensor-Quality-Agent, Shift-Detector-Agent).

## 2.8 Statistische Analyse

Die statistische Auswertung (Statistical-Analysis-Agent) umfasst Hauptkomponentenanalyse
(PCA), PLS-Regression (PLS), Hauptkomponentenregression (PCR), Varianzanalyse
(ANOVA) und Clusteranalyse. Implementierung auf Basis von `scikit-learn >= 1.3`;
Visualisierungen mit matplotlib/seaborn/plotly.

## 2.9 Neuronale Netzwerkanalyse

Parallel zur statistischen Analyse (protokollpflichtig, `mandatory_parallel_analysis`)
erfolgt eine neuronale Netzwerkanalyse (Neural-Network-Agent) mit
Convolutional Neural Networks (CNN), Multi-Layer-Perceptrons (MLP),
Autoencodern und Ensemble-Modellen. Beide Analysesäulen werden im
Abschlussbericht vergleichend gegenübergestellt.

## 2.10 Kalibration und Modelloptimierung

Kalibrationsmodelle werden für PLS, PCR, Support Vector Machines (SVM),
Random Forest, XGBoost und CNN erstellt. Die Hyperparameteroptimierung erfolgt
mittels Bayesscher Optimierung und Grid Search (`optuna >= 3.2`); das
Optimierungsprotokoll (Trials, Best-Parameter, Best-Score je Methode) wird
vollständig dokumentiert. Gütemaße: R², RMSE, RMSEP und MAE.

## 2.11 Spektralvergleich und Ähnlichkeitssuche

Die Ähnlichkeitssuche (`services/spectrum_similarity.py`) implementiert
Nearest-Neighbour-Suche mit FAISS-Backend (L2- und Kosinus-Distanz) und exaktem
numpy-Fallback; Ein- und Ausgabe erfolgen ausschließlich im einheitlichen
Spektral-Schema. Embeddings werden anwendungsseitig erzeugt und in Qdrant
gespeichert (semantische Suche über Analyseergebnisse und Dokumentation).
Neu eingehende Spektren werden automatisch mit vorhandenen Referenzspektren
abgeglichen. Absicherung durch 16 Tests (`tests/test_s5_spectrum_similarity.py`).

## 2.12 Ergebnisdialog (LLM-Chatbot)

Zur Ergebnisdiskussion steht ein Chatbot auf Basis von Ollama mit
`mistral:latest` bereit, der vollständig lokal läuft. Der Kontext wird per
Retrieval-Augmented Generation (RAG) aus den Analyseergebnissen und den
Quarto-Dokumenten aufgebaut (Qdrant-Anbindung mit Status-Reporting).
Bei Nichterreichbarkeit von Modell oder Vektordatenbank degradiert das System
kontrolliert (`degraded`-Status) ohne Absturz (17 Tests,
`tests/test_s6_chatbot.py`).

## 2.13 Federated Learning

Für verteiltes, datenschutzfreundliches Modelltraining wird Federated Learning
über Flower eingesetzt (Flower-Server-Service, `federated_learning_service.py`):
Modellaggregation ohne Austausch von Rohdaten zwischen Standorten.

## 2.14 Berichterstellung

Alle Analysen werden automatisch in einem strukturierten Abschlussbericht
(Quarto) dokumentiert. Pflichtsektionen: Metadatenanalyse und -bewertung,
Datenqualität, Sensoranalyse, statistische Analyse, neuronale Netzwerkanalyse,
Kalibrationsvergleich, Similarity-Analyse, Optimierungsprotokoll, Gesamtergebnis
und Handlungsempfehlungen. Diagramme werden versioniert aus den
Analyseergebnissen generiert.

## 2.15 Qualitätssicherung und Iterationsprotokoll

Das System arbeitet iterativ nach dem Zyklus *Analyse → Evaluation →
Optimierung → Reanalyse* mit vorgegebenen Abbruchkriterien:
`ERRORS = 0`, `CRITICAL_WARNINGS = 0`, `OPEN_CHANGE_REQUESTS = 0` (maximal
100 Iterationen). Ergänzend sind verpflichtend: versionsgeprüfte Ausführung
(`mandatory_version_check`), Kreuzbegutachtung zwischen Agenten
(`mandatory_cross_review`) und Selbstoptimierung (`mandatory_self_optimization`).
Ein Update-Monitor scannt alle Abhängigkeitsmanifeste und Container-Images auf
Versionsspezifikationsverstöße und unpinnte `latest`-Tags; Updates sind
bewusste Deployment-Entscheidungen mit Bericht, kein automatischer Eingriff.

Die Software-Qualität ist durch eine pytest-Testsuite von 332 automatisierten
Tests (Einheiten-, Integrations- und End-to-End-Tests über die Schritte S3–S9
und OP1–OP7 der Projektfahrplan) sowie `mypy`-Typprüfung abgesichert. Das
Deployment ist über Docker Compose (Development/Produktion) und
Ansible-Playbooks (Docker- und Bare-Metal-Deploy, Backup) reproduzierbar.

## 2.16 Datenverfügbarkeit und Reproduzierbarkeit

Sämtlicher Quellcode, die Containerdefinitionen, die Konfiguration sowie die
Testmatrizen sind im Repository versioniert. Die vollständige Pipeline ist
durch Angabe von Commit-Hash, Manifest-Versionen (`requirements*.txt`,
`docker-compose.yml`) und Modell-Kennung (`mistral:latest`) reproduzierbar.
