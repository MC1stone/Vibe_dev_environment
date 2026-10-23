# Repository-Abgleich & Entwicklungs-Roadmap (NIR-IP)

Version: 1.0 — Abgleich des Mission Statements (`MISSION_STATEMENT.md`) und des
Agent-Framework-Init-Prompts (`AGENT_FRAMEWORK_INIT_PROMPT.md`) mit dem aktuellen
Repository-Stand. Diese Datei ist vor jedem Entwicklungsbeginn ebenfalls zu lesen,
um zu wissen, wo das Projekt steht und was als Nächstes zu tun ist.

---

## 1. Ist-Aufnahme des Repositories

Das Repository enthält mehrere parallele Projektansätze:

| Verzeichnis | Inhalt | Reifegrad |
|---|---|---|
| `NIR_Intelligence-main/` | Vollständige Multi-Agent-Plattform: 25+ Agenten, Docker-Compose-Stack, Django-Projekt, Ansible, Federated Learning, ILIAS-Integration, Startsequenz-Dateien | **Am ausgereiftesten — führendes Projekt** |
| `nir_platform/` | Django-App (`analysis`, `nir_platform`, Templates), Agents-Ordner, Docker, Skripte | Teilweise, eigener Ansatz |
| `HANDHELD/` | MQTT, napari-App, Node-RED, MCP-Server, Django-Plattform, `MASTER_PLAN.md` | Teilweise, eigener Ansatz |
| `framework/` | Generisches Multi-Agent-Framework (Skeleton; Skills nur zu 2 Dateien implementiert) | Gerüst |
| Repo-Wurzel | Referenzdokumentation (PDFs/MDs zu Spektroskopie, napari, KI/RAG), `AGENT_FRAMEWORK_INIT_PROMPT.md`, `MISSION_STATEMENT.md` | Dokumentation + Steuerdateien |

---

## 2. Abgleich Mission Statement ↔ Repository

### 2.1 Bereits erfüllt (im `NIR_Intelligence-main/`)

- **Startsequenz-Dateien vorhanden:** `NIR_Intelligence-main/TASK.md`,
  `NIR_Intelligence-main/task_definition.yaml`, `NIR_Intelligence-main/system_manifest.json`
  (Manifest mit System-, Container-, KI-, Orchestrierungs- und Qualitäts-Sektionen;
  `task_definition.yaml` enthält bereits die Iterationsstop-Bedingungen
  `ERRORS = 0 / CRITICAL_WARNINGS = 0 / OPEN_CHANGE_REQUESTS = 0` und die Pflicht zur
  parallelen Analyse).
- **Agenten des Mission Statements existieren:** `master_agent`, `data_preparation_agent`,
  `sensor_quality_agent`, `statistical_analysis_agent`, `neural_network_agent`,
  `calibration_agent`, `metadata_agent`, `faiss_agent`, `postgresql_agent`, `django_agent`,
  `mcp_agent`, `quarto_agent`, `flower_agent` (+ weitere: `generic_file_handler_agent`,
  `ilias_agent`, `shift_detector_agent`, `spectral_analysis_agent`, `reporting_agent` …).
- **Docker-Compose-Stack:** Services für Weaviate, t2t-transformers, PostgreSQL, FAISS,
  MCP-Server, Flower-Server, Django-App, Ollama, Redis — containerisiert und lokal.
- **Django + APIs + Benutzerverwaltung** im `django_project/`.
- **Federated Learning:** `flower_server`-Service, `federated-learning.md`, Flower-Agent.
- **ILIAS-Integration:** `ilias_agent`, `ilias-integration.md`, `ILIAS_INTEGRATION_SUMMARY.md`.
- **Quarto-Dokumentation:** `quarto_agent`, Reporting-Agent.

### 2.2 Abweichungen und Lücken (Maßnahmen erforderlich)

| # | Befund | Abweichung zum Mission Statement | Maßnahme |
|---|---|---|---|
| G1 | **Weaviate statt Qdrant im Stack:** `docker-compose.yml` (Service `weaviate`), `requirements.txt` (`weaviate-client`), `agents/weaviate_agent.py` | Mission Statement: Weaviate out of scope, Qdrant ist der Ersatz | Migration Weaviate → Qdrant (Schritt S2) — ✅ erledigt (Commit e07dff4) |
| G2 | **Startsequenz-Dateien nicht in Repo-Wurzel:** Der Init-Prompt nennt `TASK.md` etc. ohne Pfad; die Dateien liegen in `NIR_Intelligence-main/` | „Jeder Agent MUSS vor jeder Ausführung … lesen" | Pfade im Init-Prompt präzisieren bzw. Dateien als führende Steuerdateien konsolidieren (S1) |
| G3 | **Drei parallele Plattform-Ansätze** (`NIR_Intelligence-main`, `nir_platform`, `HANDHELD`) mit Überschneidungen | Mission: eine Plattform | Konsolidierung: `NIR_Intelligence-main` als führendes Projekt deklarieren; Fähigkeiten der anderen (napari, MQTT/Node-RED) integrieren statt duplizieren (S1, S5) |
| G4 | **Formatabhängigkeit prüfen:** `generic_file_handler_agent` vorhanden, aber Abdeckung aller Formate (SPC, JMP, MATLAB, Kamerabilder RAW/JPEG/PNG, herstellerspezifische Exporte) ist nicht nachgewiesen | Master Objective 1: Import unabhängig vom Dateiformat | Erweiterbare Import-/Exportschicht vervollständigen + Testmatrix über alle Formate (S3) — ✅ erledigt (S3, Branch vibe/s3-format-agnostic-import) |
| G5 | **Keine Spektrometer-Abstraktionsschicht:** Geräteintegration nicht über einheitliches Adapter-Muster nachgewiesen | Grundregel: alle Spektrometer | Gerätetreiber-/Adapter-Schicht einführen; bestehende ESP32-S3-Integration als erster Adapter (S4) — ✅ erledigt (S4, Branch vibe/s4-spectrometer-abstraction) |
| G6 | **Chatbot für Ergebnisdiskussion:** Ollama-Service vorhanden, aber kein dedizierter Ergebnis-Chatbot als Feature nachgewiesen | Master Objective 10 | RAG-/Chatbot-Feature auf Ollama/Mistral-Basis mit Qdrant-Anbindung (S6) — ✅ erledigt (S6, Branch vibe/s6-chatbot) |
| G7 | **Selbstoptimierung/Updates:** Selbstoptimierung als Ziel formuliert, aber kein Update-Mechanismus für Open-Source-Komponenten implementiert | Master Objective 15 | Update-Monitoring + Abhängigkeitsprüfung (z. B. CI-Job) definieren (S7) — ✅ erledigt (S7, Branch vibe/s7-update-monitoring) |
| G8 | **`framework/` unvollständig:** Nur Backend-/Frontend-Skills implementiert, Rest ist Skeleton | Init-Prompt referenziert Framework-Dokumentation | Als Referenz-Gerüst deklarieren, nicht als aktive Komponente (S1) — ✅ erledigt: `AGENTS.md` (S1) und diese Roadmap deklarieren `framework/` als reine Referenz; keine aktive Weiterentwicklung, keine Vervollständigung (bewusste Entscheidung: `NIR_Intelligence-main/` ist die vollständige Plattform) |

---

## 3. Planung der nächsten Entwicklungsschritte

Reihenfolge nach Abhängigkeit; jeder Schritt wird gemäß
`AGENT_FRAMEWORK_INIT_PROMPT.md` (inkl. Startsequenz und Iterationsregel) ausgeführt.

### S1 — Konsolidierung & Steuerung (Grundlage, zuerst) — ✅ ERLEDIGT
- [x] `NIR_Intelligence-main/` als führendes Projekt (Single Source of Truth) deklarieren
      (verankert in `AGENTS.md` und Init-Prompt).
- [x] Startsequenz-Dateien (`TASK.md`, `task_definition.yaml`, `system_manifest.json`)
      als führende Steuerdateien bestätigt; Pfade im Init-Prompt verankert.
- [x] `TASK.md` auf die aktuelle Aufgabe (S2 Qdrant-Migration) umgeschrieben.
- [x] Weaviate-Referenzen aus den Steuerdateien entfernt (`task_definition.yaml`,
      `system_manifest.json`); G1 damit in den Steuerdateien vorbereitet.
- [x] Verhältnis zu `nir_platform/`, `HANDHELD/`, `framework/` dokumentiert:
      `AGENTS.md` erklärt `NIR_Intelligence-main` zur Single Source of Truth;
      `nir_platform/` und `HANDHELD/` werden gemäß S4/S5 auf Quellen reduziert
      (MQTT, napari werden integriert, nicht weiterentwickelt);
      `framework/` ist Referenz-Gerüst (G8) und wird nicht aktiv weiterentwickelt.

### S2 — Migration Weaviate → Qdrant (schließt G1) — ✅ ERLEDIGT (Commit e07dff4)
- [x] `docker-compose.yml`: Qdrant-Service (Ports 6333/6334) ersetzt Weaviate und
      t2v-transformers; `docker-compose.prod.yml` inkl. Healthcheck migriert.
- [x] `requirements*.txt`: `qdrant-client>=1.9.0` ersetzt `weaviate-client`.
- [x] `agents/qdrant_agent.py` ersetzt `agents/weaviate_agent.py`; Registry und
      Orchestrator umgestellt.
- [x] Alle Aufrufer umgestellt: Django-Healthcheck, `local_settings.py`, Port-Agent,
      Prometheus, Dockerfile-Env, `.env*`-Dateien.
- [x] Deployment-Schicht migriert: Ansible-Playbooks (Docker-Deploy, Bare-Metal-Deploy,
      Backup), Templates, Inventory, Group-Vars; Start-/Test-/Monitor-Skripte.
- [x] Embedding-Pipeline-Entscheidung: t2v-transformers-Container entfällt; Qdrant speichert
      nur Vektoren — Embedding-Erzeugung erfolgt anwendungsseitig, detaillierte Anbindung
      folgt in S6 (Ergebnis-Chatbot).
      Verifikation: YAML/JSON/py_compile/bash -n grün; kein aktiver Weaviate-Verweis
      im Stack verbleibend (nur historische Doku-Markdowns).

### S3 — Format-agnostischer Datenimport (schließt G4) — ✅ ERLEDIGT
- [x] SPC-Loader (binäres Galactic/Thermo-Format): Header-Parsing, Einheiten-Metadaten;
      SPC läuft nicht mehr über den Text-Loader.
- [x] MATLAB-Loader (`.mat`): benannte Arrays und 2-Spalten-Arrays, scipy.io (bereits
      vorhandene Abhängigkeit, keine neue).
- [x] JSON-Schema für parallele Arrays (`{wavelength: [...], intensity: [...]}`).
- [x] `.mat`/`.dpt` als Spektralformate registriert (generic_file_handler_agent).
- [x] JMP-Entscheidung (Spektroskopie-Experte + Head of Development): JMP-Exporte sind
      tabellarisch (CSV/XLSX) und laufen über die vorhandenen Tabellen-Loader; kein
      separates proprietäres JMP-Parsing (keine Abhängigkeit von JMP-Format-Interna).
- [x] Testmatrix `tests/test_s3_format_loaders.py`: 7/7 grün (SPC-Roundtrip,
      SPC-Invalid-Magic, MAT benannt/2-spaltig, CSV/TXT/JSON-Regression).
      `.gitignore`: tests/-Verzeichnis wird nicht mehr global ignoriert (vorher wurden
      alle `test_*.py` ausgeschlossen, der tests-Ordner war faktisch leer).
      Verifikation: py_compile + Testmatrix 7/7; Import-Ausnahme graceful (None).
- Offen für spätere Schritte: echte Hersteller-Testdateien (z. B. aus SpectraSuite/
      OPUS) als Regression-Fixtures; SPC-Multi-File-Varianten (TMULTI) aktuell bewusst
      nicht unterstützt (Fehlermeldung verweist auf Layout).

### S4 — Spektrometer-Abstraktionsschicht (schließt G5) — ✅ ERLEDIGT
- [x] Einheitliches Adapter-Muster `devices/base_spectrometer.py`: abstrakter Kontrakt mit
      Messdaten (einheitliches Spektral-Schema aus S3), Metadaten, Kalibrationsparametern,
      Gerätestatus (DeviceStatus-Enum), Capabilities (Wellenlängenbereich, Auflösung, Detektor).
- [x] Registry `devices/registry.py`: MODEL_ID-basierte Registrierung; neue Spektrometer-
      modelle integrieren ohne Änderung des Plattform-Kerns (Grundregel 2 operativ).
- [x] Erster Adapter: DIY-Matchbox (`devices/diy_matchbox.py`, USB-Kamera).
- [x] Zweiter Adapter: ESP32-S3-Kameraspektrometer (`devices/esp32_s3_camera.py`, MQTT,
      Payload-Parsing gemäß `HANDHELD/mqtt/topic-spec.md`).
- [x] Dritter Adapter: SparkFun Triad (`devices/sparkfun_triad.py`, Qwiic/I²C,
      AS7262+AS7263+ML8511, 18 Kanäle 410–940 nm gemäß der Labordaten in
      `data/raw/T4-T5_ALLE_mit_Brix_2.txt`, Spalten A_410–L_940).
- [x] Testmatrix `tests/test_s4_spectrometer_adapters.py`: 26/26 grün (Kontrakt, Registry,
      Capture-Payload → einheitliches Schema, Fehlerbehandlung, Lifecycle,
      Triad-Payload-Varianten).
      Verifikation: py_compile + 26/26 Tests + S3-Regression 7/7 grün.
- Offen für spätere Schritte: kommerzielle Geräte (NIR, UV-Vis, Raman, FTIR) als weitere
      Adapter; echter MQTT-Broker-Worker (Acquisition-Layer) zur Live-Anbindung.

### S5 — Integration napari-Visualisierung & Spektrenvergleich — ✅ ERLEDIGT
- [x] `services/spectrum_similarity.py`: Vergleichs-Engine (Nearest-Neighbour)
      mit FAISS-Backend (falls installiert) und exaktem numpy-Fallback;
      Ein-/Ausgabe ausschließlich im einheitlichen Spektral-Schema aus S3;
      QdrantSimilarityService als optionales Embedding-Backend (operativ mit S6).
- [x] napari-Server aus `HANDHELD/napari_app` integriert als
      `services/napari_server/` (Headless-FastAPI, Port 8002, MQTT `spectral/#`);
      `HANDHELD/` bleibt unangetastet (G3-Regel: integrieren statt duplizieren).
- [x] `docker-compose.yml` + `docker-compose.prod.yml`: `napari_server`-Service
      (Build aus `services/napari_server`, nir_network, MQTT-Env-Variablen).
- [x] FAISS/Qdrant-Agents an die echte Engine angebunden statt Platzhalter-
      Simulation (`agents/faiss_agent.py`, `agents/qdrant_agent.py`, v1.1.0).
- [x] Testmatrix `tests/test_s5_spectrum_similarity.py`: 16/16 grün
      (Selbstmatch ~0, Ranking L2/Kosinus, numpy-Fallback, Edge Cases,
      S4-Adapter-Kompatibilität inkl. SparkFun Triad 18 Kanäle, Qdrant-Graceful,
      Compose-Integration). Verifikation: py_compile + 16/16 Tests +
      S3-Regression 7/7 + S4-Regression 26/26 + YAML-Parse beider Compose-Dateien.
- Offen für S6: Embedding-Pipeline (Ollama/Mistral) und Qdrant-RAG für den
      Ergebnis-Chatbot; Django-Frontend-Anbindung der Visualisierung.

### S6 — Ergebnis-Chatbot (Master Objective 10) — ✅ ERLEDIGT
- [x] `services/chatbot_service.py`: `ChatbotService` auf Ollama/Mistral:latest
      (`/api/chat`, `ollama>=0.1.0` bereits in requirements.txt); System-Prompt mit
      NIR-IP-Identität; RAG-Kontext aus Analyseergebnissen (AgentOutput-Stil) und
      Dokumentation; keine Chatverlauf-Persistenz (Turns werden pro Request
      übergeben — bewusstes Anti-Creep).
- [x] `RagContextBuilder`: Kontext aus Analyseergebnissen + Quarto-Dokumenten;
      Qdrant-Anbindung über `QdrantSimilarityService` (S5), Status-Reporting
      ohne Absturz;_embedding-Pipeline folgt mit laufendem Qdrant.
- [x] Django-Anbindung: `api/chatbot_views.py` (POST message, GET status;
      400 bei fehlender Frage, 503 im Degraded-Fall) + `api/chatbot_urls.py`;
      Route `api/chatbot/` in `nir_web/urls.py` registriert.
- [x] Graceful Degradation: Ollama nicht erreichbar → `degraded=True` + Fehler,
      kein Absturz; Qdrant nicht erreichbar → Chatbot antwortet ohne RAG-Kontext.
- [x] Testmatrix `tests/test_s6_chatbot.py`: 17/17 grün (Prompt-Komposition,
      Antwort-Parsing mit Stub-Client, Degraded-Pfade, URL-Wiring,
      S5-Regressionsspot-Check). Verifikation: py_compile + 17/17 Tests +
      S3 7/7 + S4 26/26 + S5 16/16 Regressionen grün.
- Offen für spätere Schritte: echte Embedding-Indizierung der Quarto-Reports
      in Qdrant (benötigt laufenden Qdrant + Embedding-Modell); Django-Frontend-
      Chat-UI (aktuell API-Endpoint ohne Frontend-Seite).

### S7 — Selbstoptimierung & Update-Monitoring (Master Objective 15) — ✅ ERLEDIGT
- [x] `services/update_monitor.py`: UpdateMonitorService — scannt alle
      `requirements*.txt`-Manifeste und docker-compose-Images; lokale
      installierte Versionen werden erkannt (importlib.metadata, kein Netz);
      Specifier-Verstoß → Flag; `latest`-Tags → Pinning-Empfehlung.
- [x] `scripts/check_updates.py`: CLI für CI-Job/manuelle Läufe
      (`--json`, `--no-report`, `--compose-files`); rendert Quarto-Bericht
      (`.qmd`, Summary + Komponenten-Tabellen + Handlungsempfehlungen).
- [x] `services/calibration_optimization.py`: Optuna-Optimierungsprotokoll
      (`OptimizationProtocol` mit Trials, Best-Params, Best-Score, Methoden
      PLS/PCR/SVM/RandomForest/XGBoost/CNN gemäß Mission Statement);
      Optuna optional — ohne Installation → `deferred`, kein Absturz.
- [x] Kein Auto-Update: Updates bleiben bewusste Deployment-Entscheidungen
      (Bericht + Empfehlungen statt Eingriff).
- [x] Testmatrix `tests/test_s7_update_monitoring.py`: 27/27 grün
      (Manifest-Parsing, Image-Extraktion, Specifier-Semantik, Scan über das
      echte Projekt, Quarto-Rendering, CLI-End-to-End inkl. --json,
      Optuna-Deferral, S5/S6-Regressionsspot-Checks).
      Verifikation: py_compile + 27/27 Tests + S3 7/7 + S4 26/26 + S5 16/16 +
      S6 17/17 Regressionen grün.
- Offen für die Zielumgebung: Anbindung an echte Registry-/PyPI-Indexe
      (benötigt Netz) und ein GitHub-Actions-Workflow als CI-Job (kein CI
      bisher im Repo).

### S8 — ILIAS-Lernszenarien vertiefen — ✅ ERLEDIGT
- [x] **ILIAS läuft in einem eigenen Docker-Container**: Service `ilias`
      (Community-Image `srsolutions/ilias:9-php8.2-apache`, gepinnter Tag;
      Port 8080→80; `ILIAS_AUTO_SETUP`; Env-konfiguriert; Healthcheck in
      prod) in `docker-compose.yml` + `docker-compose.prod.yml`.
- [x] Dedicated MariaDB `ilias_db` (mariadb:10.11, utf8mb4) — ILIAS benötigt
      zwingend MySQL/MariaDB; Volumes `ilias_data`, `ilias_extradata`,
      `ilias_db_data` registriert; beide Dienste im `nir_network`.
- [x] `services/ilias_learning_service.py`: Lernpfad-Modell
      (`LearningPath` → `LearningModule` → `LearningObjective`, Bloom-Level),
      `ILIASCourseBuilder` (ILIAS-Objekttypen `crs`/`lobj`),
      `ILIASLearningService.sync_learning_path` (Kurs + Lernziele, injizierbarer
      Transport, `SyncOutcome`), Verfügbarkeits-Status ohne Absturz.
- [x] Django-API: `api/ilias_views.py` (POST learning-paths/sync: 400/201/502,
      GET status) + `api/ilias_urls.py`; Route `api/ilias/` registriert.
- [x] Testmatrix `tests/test_s8_ilias_integration.py`: 26/26 grün
      (Lernpfad-Modell, Payload-Building, Sync mit Stub-Transport in 4 Varianten,
      Unreachable-Graceful, Django-Wiring, Compose-Topologie dev+prod,
      Image-Pinning, S6-Regressionsspot-Check).
      Verifikation: py_compile + 26/26 Tests + S3–S7-Regressionen grün +
      S7-Update-Monitor erkennt die neuen Images (22 Docker-Komponenten).
- Offen für die Zielumgebung: echter ILIAS-API-Token-Flow (OAuth2 im
      `ilias_integration_agent.py` vorhanden, benötigt laufenden ILIAS);
      Kurssynchronisation der Django-Benutzer (users sync, saml); didaktische
      Lerninhalte (Sache des E-Learning-Spezialisten, nicht der Plattform).

### S9 — Federated Learning ausbauen — ✅ ERLEDIGT
- [x] `services/federated_learning_service.py`: framework-unabhängiger
      Federated-Learning-Kern für verteilte Spektrometer-Setups —
      Clients trainieren lokal (Ridge-Update) und teilen **ausschließlich
      Modellaktualisierungen** (`ModelUpdate`: Parameter, Anzahl Beispiele,
      Gruppe, Metriken — keine Rohdaten; `PrivacyAuditor` prüft den Vertrag
      pro Runde).
- [x] `NonIIDSharder`: Spektren werden pro Spektrometer-/Probengruppe
      geshardet (z. B. sparkfun_triad, esp32_s3_camera, diy_matchbox) —
      jeder Client erhält nur seine eigene Gruppe = realistisches
      non-IID-Szenario des NIR-Labors.
- [x] `FedAvgAggregator`: FedAvg (beispielgewichtet) und FedProx
      (Proximal-Term mit μ, globalen Parameter-Blend) auf numpy-Basis;
      flwr bleibt der Produktions-Transport (`services/flower_server.py`,
      `agents/flower_agent.py`, Compose-Service flower_server, flwr>=1.4.0).
- [x] `FederatedLearningService`: Runden-Orchestrierung (Lokaltraining →
      Aggregation → Privacy-Audit), Runden-Historie, Konvergenz über mehrere
      Runden nachgewiesen (Distanz zum gepoolten Optimum sinkt).
- [x] Testmatrix `tests/test_s9_federated_learning.py`: 28/28 grün
      (Sharding, Privacy-Vertrag, FedAvg/FedProx-Semantik, Multi-Runden-
      Konvergenz, Fehlerfälle, Compose/Requirements-Integration,
      S4/S5/S8-Regressionsspot-Checks).
      Verifikation: py_compile + 28/28 Tests + S3–S8-Regressionen grün.
- Offen für die Zielumgebung: echter flwr-Client-Server-Betrieb über den
      Compose-Service (benötigt laufende Container); Anbindung des Kerns an
      echte Kalibrationsmodelle (S7-Optimierungsprotokoll).

---

## 5. Zielumgebungs-Offenpunkte (nach lokaler Verifikation)

Die lokale Verifikation auf dem Zielrechner (Debian) ist abgeschlossen:
alle Services laufen, Mistral geladen, ILIAS installiert. Dabei entstanden
die Fixes PR #12 (requirements-Pins), #13/#14 (ILIAS utf8 + strict mode),
#15 (Ollama-Healthcheck). Verbleibende Offenpunkte nach Priorität:

### OP1 — Qdrant-Embedding-Pipeline (S5/S6) — ✅ ERLEDIGT
- [x] `services/embedding_service.py`: Ollama-Embeddings (`/api/embeddings`,
      `nomic-embed-text:latest`) + `QdrantEmbeddingStore` (Collection-anlegen
      mit Dimensionserkennung, Upsert, top-k-Suche über `query_points`),
      `EmbeddingService`-Pipeline (index_texts / index_analysis_results /
      search_texts), `InMemoryEmbeddingStore` für Tests/Offline-Demos.
- [x] `RagContextBuilder` (S6) an die Pipeline angebunden: injizierbarer
      `embedding_service` — liefert echtes Qdrant-RAG als Chat-Kontext
      (`qdrant_rag`-Quelle), bei Ausfall graceful ohne Absturz.
- [x] Testmatrix `tests/test_op1_embedding_pipeline.py`: 29/29 grün;
      Regressionen S3–S9 grün (186 Tests insgesamt).
- Offen (Zielumgebung): `ollama pull nomic-embed-text` auf dem Rechner,
      Indizierung echter Quarto-Reports im Betrieb.

### OP2 — ILIAS-API-Token-Flow (S8) — ✅ ERLEDIGT- Neue `services/ilias_api_service.py`: `IliasTokenClient`
  (OAuth2-Token-Fetch via `POST /oauth2/token`, konfigurierbarer Grant
  — `client_credentials` (Default), `authorization_code`, `refresh_token` —,
  Expiry-Tracking, Refresh) und `IliasApiClient` (authentisierter
  Transport mit `Authorization: Bearer`, 401-Retry mit Token-Refresh,
  Kurs-Lookup `find_course_ref_id_by_title` für echte Kurs-IDs).- `ILIASLearningService` (S8) erweitert: `sync_learning_path(..., course_ref_id=...)`
  synced Module in bestehende Kurse (echte Kurs-IDs), keine Neuanlage;
  `create_authenticated_ilias_service()` verkabelt Learning-Service mit
  dem authentifizierten API-Transport. Unauthentisierter S8-Pfad
  unverändert (rückwärtskompatibel).- Testmatrix `tests/test_op2_ilias_token_flow.py`: 31/31 grün;
  Regressionen S3–S9 + OP1 grün (207 Tests insgesamt).- Offen (Zielumgebung): OAuth2-Client + REST-API in ILIAS-Installation
  aktivieren (Admin → Web Services / OAuth2), Client-Credentials in Env
  setzen (`ILIAS_API_CLIENT_ID/SECRET`), Sync gegen echte Kurs-IDs testen.
- Der echte ILIAS-Container muss OAuth2/REST erst aktiviert haben; bis
  dahin bleibt der unauthentisierte S8-Stub-Flow funktionsfähig.

### OP3 — Plattform-UI: Upload, Chatbot, ILIAS (G3/G4) — ✅ ERLEDIGT
- **Upload repariert:** `files.html` — `uploadFiles()` poste via FormData an
  `POST /api/files/upload/` (CSRF via Cookie), `loadFiles()` lade Statistiken+
  Galerie+Tabelle via `GET /api/files/`; Analyze (single/multiple), Delete
  (single/multiple), Download ans Backend gebunden. Kaputtes
  `upload_files.html` (defekte Template-Tags, ungeroutet) entfernt;
  `upload_view` leitet auf `/files/` weiter.
- **Chatbot-UI (S6):** neues `chatbot.html` (Chat-Verlauf, Eingabe,
  degraded-Handling, `qdrant_rag`-Quellen-Anzeige) → `POST
  /api/chatbot/message/` mit `question`-Feld; Status-Panel via `GET
  /api/chatbot/status/`; Route `/chatbot/` + Nav-Eintrag.
- **ILIAS-UI (S8):** neues `ilias.html` (Lernpfad-Sync-Formular → `POST
  /api/ilias/learning-paths/sync/`, Status → `GET /api/ilias/status/`,
  Link zum ILIAS-Container); Route `/ilias/` + Nav-Eintrag.
- Testmatrix `tests/test_op3_platform_ui.py`: 40/40 grün (echte
  Django-Template-Engine-Kompilierung + Routing-/Contract-Checks);
  `manage.py check` ohne Befunde; Regressionen S3–S9 + OP1–OP2 grün
  (287 Tests insgesamt).
- Offen (Zielumgebung): End-to-End-Klick im Browser nach `git pull`
  (Upload einer CSV → Auto-Analyse → Chatbot-Frage).

### FL6 — Superlink/Supernode-Deployment + ILIAS Course Agent im eigenen Container — ✅ ERLEDIGT

- FL1-Offenpunkt (Zielumgebung) adressiert: das Compose-Deployment ist jetzt
  gegen laufende Container verkabelt und testbar —
  `scripts/flower_superlink_entry.py` (NEU) startet den echten
  flower-superlink (flwr 1.38: `flower_superlink --insecure` mit
  Fleet-API-Adresse) und bootstrappt danach die ServerApp aus
  `services/flower_apps.py` (FedAvg/FedProx, Runden/Strategie über
  FLOWER_*-Env konfigurierbar, Neustart des ServerApp-Subprozesses bei Exit).
  `scripts/flower_supernode_entry.py` (NEU) verbindet einen Supernode über
  `flwr_clientapp --superlink` mit dem FL1-`NirFlwrClient` (S9-Ridge-Semantik,
  nur Parameter-Updates im Payload — Rohspektren bleiben lokal);
  Trainingsdaten aus FLOWER_CLIENT_DATA (.npz), fehlt die Datei ehrlich:
  synthetischer Platzhalter mit Warnhinweis (kein Fake-Betrieb).
- `docker-compose.yml` + `docker-compose.prod.yml` (ANGEPASST): flower_server
  startet den Superlink-Entry (flwr wird im Command gepinnt), neuer Service
  flower_client (Supernode, FLOWER_SUPERLINK_ADDRESS=flower_server:9092,
  FLOWER_CLIENT_GROUP=sparkfun_triad, depends_on flower_server), Ports
  5555/5556/9091/9092 gemappt.
- ILIAS-Kursentwicklung im eigenen Container:
  `agents/ilias_course_agent.py` (NEU) — `IliasCourseAgent` mit
  Curriculum-Katalog aus echten Plattform-Fähigkeiten (Datenimport,
  Metadaten, Sensorik, Chemometrie, Föderiertes Lernen), Lernziele mit
  Bloom-Leveln, `sync_curriculum` (Kurs-Wiederverwendung per OP2-Lookup,
  Sync als Lernpfad über die S8-`ILIASLearningService`-Schnittstelle),
  Operationen develop/sync/status; jede ILIAS-Störung degradiert ehrlich.
  `scripts/ilias_course_agent_runner.py` (NEU): kontinuierlicher Runner
  (--interval/--once), State in output/ilias_course_agent_state.json.
  Neuer Compose-Service ilias_course_agent (Dockerfile.django,
  PYTHONPATH=/app:/app/agents, ILIAS_URL=http://ilias:80,
  depends_on ilias, restart unless-stopped) in beiden Compose-Dateien.
- Verifikation: `tests/test_fl6_deployment_ilias_agent.py` 35/35 grün
  (Compose-Wiring beider Dateien, Entry-Skript-Verträge, Katalog- und
  Sync-Contract mit Stub-Transport, Runner-Smoketest gegen unerreichbares
  ILIAS mit ehrlichem degraded-Abschluss, exit 0). Regressionen: FL1 21/21,
  FL2 20/20, FL3 25/25, FL4 20/20, FL5 16/16, S9 28/28, S8 26/26,
  OP2 31/31, OP3 45/45 grün.
- Offen (Zielumgebung): live superlink/supernode-Föderationsrunde gegen
  laufende Container (Container-Runtime auf dem Zielrechner noetig); echter
  Kurs-Sync gegen ILIAS mit aktivierter OAuth2/REST-API.

### FL5 — ILIAS-Koordination föderierter Gruppen — ✅ ERLEDIGT
- `services/federated_ilias_service.py` (NEU): föderierte Gruppen-Sessions
  als ILIAS-Kurs-Kontext — `create_session_context` (Kurs-Wiederverwendung
  per OP2-Titel-Lookup statt Duplikat-Anlage), `sync_round_status` (pro Runde
  metadata-only Status in den Kurs-Kontext: Runde, Gruppen, aggregierte
  Qualitätswerte — Privacy-Vertrag im Code erzwungen: Payloads mit
  `params`/`spectra`/Rohdaten werden verworfen).
- Baut auf dem OP2-API-Client (`IliasApiClient`/`IliasTokenClient`) auf,
  Transport injizierbar; jede ILIAS-Störung degradiert ehrlich (die
  föderierte Session selbst bleibt davon unberührt — FL1-FL4 laufen
  local-only weiter).
- Verifikation: `tests/test_fl5_federated_ilias.py` 16/16 grün (Stub-
  Transport: Kontext-Wiederverwendung, Anlage, Runden-Sync,
  Privacy-Rejects, Degradationspfade, HTTP-Fehler ehrlich gemeldet).
  OP2-Regression 31/31, S8-Regression 26/26 grün.
- Offen (Zielumgebung): Sync gegen echte ILIAS-Kurse mit aktivierter
  OAuth2/REST-API (OP2-Offenpunkt gilt entsprechend).

### FL4 — Föderierte Sessions: Django-API + Consent-UI — ✅ ERLEDIGT
- `django_project/api/federated_views.py` (NEU): Consent-gesteuerte API —
  `POST /api/federated/consent/` (explizites Opt-in, Default `local_only`
  gemäß WORKFLOW_INTEGRATION.md), `GET /api/federated/status/` (Session-,
  Runtime- und SecAgg-Status), `POST /api/federated/rounds/` (föderierte
  Kalibrationsrunde über FL2; 403 ohne Consent, 400 bei invalidem Payload,
  503 bei sklearn-Deferral — Kern `run_federated_round` von DRF entkoppelt),
  `GET /api/federated/privacy/` (DP-Accountant + SecAgg + Privacy-Vertrag).
- `federated.html` (NEU) + Nav-Eintrag `Föderiert`: Consent-Panel
  (erteilen/widerrufen mit ehrlichem local_only-Hinweis), Session-Status-
  und Privacy-Box; Route `/federated/` registriert.
- Verifikation: `tests/test_fl4_federated_ui.py` 20/20 grün (echte
  Django-Template-Kompilierung, URL-Wiring, Consent-Gate funktional
  am Kern, Runde über echte non-IID-Shards); `manage.py check` ohne
  Befunde; OP3-Regression 45/45, OP25-Regression 65/65 grün.

### FL3 — Differential Privacy + Secure Aggregation — ✅ ERLEDIGT
- `services/federated_privacy.py` (NEU): echtes Differential Privacy statt
  FlowerAgent-Simulation — L2-Clipping des Parameter-Updates als
  Sensitivitätsschranke, Gauß-Mechanismus mit sigma aus (ε, δ)
  (`sigma >= sqrt(2*ln(1.25/delta))/epsilon`), `PrivacyAccountant` mit
  ehrlicher Kompositions-Obere-Schranke über die Runden (Gesamt-ε/-δ,
  Budget-Erschöpfung) und `dp_utility_cost` als ehrliche Utility-Messung
  (L2-Distanz clean vs. privatisiert).
- `secure_aggregation_available()`: ehrliche Verfügbarkeitsprüfung gegen das
  installierte flwr — verifiziert: flwr 1.38 liefert echtes
  `SecAggPlusWorkflow` (serverseitige blinde Aggregation); kein flwr bzw.
  kein SecAgg → ehrliches `unavailable` mit Begründung (OP14/OP18-Regel,
  nichts simuliert).
- Verifikation: `tests/test_fl3_federated_privacy.py` 25/25 grün — Mechanik
  (Clipping, Rauschen empirisch gegen sigma, Budget-Komposition),
  Integration mit dem echten FL2-PLS-Update, Privacy-Level-Mapping im
  FlowerAgent. Regressionen: S9 28/28, FL1 21/21, FL2 20/20 grün.

### FL2 — Föderierte Kalibrationsmodelle (PLS) — ✅ ERLEDIGT
- `services/federated_calibration.py` (NEU): föderierte PLS-Kalibration
  auf scikit-learn-Basis (bereits Plattform-Abhängigkeit, task_definition-
  Kalibrationsmethode `pls`) — Clients trainieren eine lokale PLS-Kalibration
  auf ihrem non-IID-Shard und teilen ausschließlich Hyperplatten-Parameter
  (Koeffizienten + Intercept, beispielgewichtet aggregiert); Rohspektren
  bleiben lokal (Privacy-Audit im Service verdrahtet).
- Sharding über die OP15-Provenanz-Dimensionen (`instrument_type` /
  `sample_type`): `shard_spectra_database()` übernimmt SpectrumRecord-artige
  Dikte; Records ohne Referenzwert werden ehrlich übersprungen.
- Verifikation: `tests/test_fl2_federated_calibration.py` 20/20 grün —
  echtes PLS-Fit, FedAvg-Hyperplatten-Aggregation, föderiertes Modell schlägt
  local-only auf gepoolten Daten (1.77 < 2.39 RMSE) und nähert sich dem
  gepoolten Optimum (1.689); sklearn-optional (ehrlicher Skip in CI).
  Regressionen: S9 28/28, FL1 21/21 grün.

### OP3a — Echter flwr-Client-Server-Betrieb (S9) — ✅ ERLEDIGT (FL1)
- `services/flower_apps.py` (NEU): Flower-App-Paar auf flwr-1.x-API —
  `make_server_app` (ServerApp mit FedAvg/FedProx-Strategie, Runden-Konfiguration),
  `NirFlwrClient` (NumPyClient, dessen lokales Training identisch zum
  S9-Ridge-Update aus `FederatedLearningService.client_update` ist — nur
  Parameter-Updates im Payload, Rohspektren bleiben lokal),
  `make_client_fn` (Client-Fabrik über non-IID-Shards: ein SuperNode je
  Spektrometergruppe), `run_federated_training` (Läuft über die
  flwr-Simulation-Engine mit dem identischen App-Code, der im Deployment
  über flower-superlink/flower-supernode läuft — Compose-Service
  flower_server bleibt der Produktionstransport im nir_network).
- Verifikation: `tests/test_fl1_flwr_runtime.py` 21/21 grün — Offline-
  Verträge (S9-Ridge-Semantik, Privacy-Payload, Gruppen-Metriken) laufen
  ohne flwr; echte Föderationsläufe (FedAvg + FedProx, 1–3 Runden über
  non-IID-Spektrometer-Shards) über die flwr-Simulation verifiziert
  (flwr 1.38); CI ohne flwr degradiert ehrlich auf die Offline-Verträge.
  S9-Regression 28/28 grün.
- Offen (Zielumgebung): Compose-Deployment-Test superlink/supernode gegen
  laufende Container (benötigt Container-Runtime auf dem Zielrechner).

### OP7 — Upload → Crew-Analyse → Quarto-Bericht (PR-#1-Ziel im Leading-Projekt) — ✅ ERLEDIGT
- **Kontext:** PR #1 fixte die Pipeline im eingefrorenen Legacy-Ansatz
  `nir_platform/` (S1/G3-Verstoß). Das eigentliche Ziel — funktionierende
  Upload→Analyse→Bericht-Kette — wurde als OP7 ins Leading-Projekt
  `NIR_Intelligence-main/` portiert und mit den OP6-CrewAI-Agenten
  umgesetzt.
- **Gefundene und gefixte Pipeline-Bugs (Leading-Projekt):**
  `SpectrometerIssue.INVALID` fehlte als Enum-Member (spectral agent
  crashte im Quality-Assessment), Crew übergab `sample_id` nicht im
  spectral-Contract (Validierung schlug fehl).
- **Bridge:** `FileCrewAnalysisView` (`api/file_views.py`) + Route
  `files/<uuid:file_id>/crew-analysis/` — lädt die hochgeladene Datei
  über den S3-formatagnostischen Loader (`EnhancedDataPreparationAgent`),
  überführt das einheitliche Spektral-Schema in den Crew-Contract und
  führt `NIRAnalysisCrew.analyze_sample` inkl. Comprehensive-Quarto-
  Bericht aus; Ergebnisse werden auf dem GenericFile-Record persistiert.
- **UI:** `files.html` — Crew-Analysis-Button pro Datei (neben Quick-Analyze).
- Testmatrix `tests/test_op7_crew_pipeline_bridge.py`: 23/23 grün
  (S3-Loader→Crew, Berichtserzeugung, Enum-/Contract-Regressionen,
  Django-Wiring, UI, OP6-Fabrik). Vollregression: S3–S9, OP1–OP6 grün
  (355 Tests insgesamt); `manage.py check` ohne Befunde. CI um OP7 erweitert.
- PR #1 (Legacy-`nir_platform/`-Ansatz) bleibt davon unberührt offen;
  Entscheidung über Schließen/Merge liegt beim Head of Development.
### OP4 — Online-Update-Lookups + CI (S7) — ✅ ERLEDIGT
- `services/update_lookup.py`: `UpdateLookupService` — PyPI-Lookups
  (`/pypi/{name}/json`, yanked/Pre-Release-Filterung) und Docker-Hub-Tag-
  Lookups (stabile semver-Tags, Registry-Normalisierung inkl. private
  Registries/localhost); HTTP-Transport injizierbar (OP2-Pattern), jede
  Netzstörung degradiert graceful auf das Offline-Verhalten (S7-Garantie).
- `services/update_monitor.py`: `ComponentEntry.available` (Upstream-Version)
  in Dataclass, `to_dict` und Quarto-Bericht; Spaltenreihenfolge
  rückwärtskompatibel zum S7-Kontrakt.
- `scripts/check_updates.py`: `--online`-Flag — reichert den Report um
  PyPI/Docker-Hub-Lookups an; offline weiterhin Exit 0.
- GitHub-Actions-CI: `.github/workflows/ci.yml` (push/PR auf main, alle 12
  Testmatrizen + `manage.py check`) und `.github/workflows/update-monitor.yml`
  (wöchentlicher Schedule + `workflow_dispatch`, Online-Report als Artifact).
- Testmatrix `tests/test_op4_update_lookups.py`: 34/34 grün; Regressionen
  S3–S9, OP1–OP3, OP6 grün (332 Tests insgesamt).

### OP6 — CrewAI-Agenten: Implementierung + Hintergrundbetrieb — ✅ ERLEDIGT
- Die neun Stub-Agenten (sensor_quality, statistical_analysis,
  neural_network, calibration, metadata, postgresql, django, mcp, ilias)
  sind real implementiert: echte Berechnungen (numpy/scipy/sklearn) und
  echte Schnittstellen-Calls mit dokumentiertem Degraded-Status statt
  simulierter Werte.
- `NIRAnalysisCrew` registriert alle 16 Missions-Agenten als CrewAI-Agents
  mit Tool-Bindings (`_agent_tool`-Factory, JSON-Kontrakt); ohne
  installiertes crewai-Paket läuft die Crew im Standalone-Modus weiter.
- `scripts/background_crew_runner.py` + docker-compose-Service
  `background_crew`: die Agenten bedienen die Plattform-Schnittstellen
  (Django, PostgreSQL, Qdrant, ILIAS, MCP) im Hintergrund in Runden
  (Standard-Intervall 300s, Status in `output/crew_background_state.json`).
- Verifikation: `tests/test_op6_crewai_agents.py` 51/51 grün;
  Regressionen S3–S9, OP1–OP3 grün, `manage.py check` ohne Befunde.

### OP8 — CrewAI-Agenten-Resultate im Web sichtbar machen (MO 5/6/7/14) — ✅ ERLEDIGT
- **Kontext (Befund):** Die OP6-Agenten (Sensor Quality, Statistical Analysis,
  Neural Network) waren real implementiert, wurden aber von
  `NIRAnalysisCrew.analyze_sample` nie ausgeführt; ihre Ergebnisse landeten in
  keiner API-Antwort, und die Analysis-UI zeigte Demo-Daten (Zufalls-Spektrum,
  '~2.5s'-Platzhalter) — die Plattform-Fortschritte waren im Web nicht sichtbar.
- `agents/nir_analysis_crew.py`: `analyze_sample` führt jetzt Sensor-Qualität,
  Statistik und Neuronale Netze aus (Mission-Regel: NN immer parallel zur
  Statistik; Eingang ausschließlich über das S3-einheitliche Spektral-Schema —
  format-/geräteagnostisch, Grundregeln erfüllt); Referenzwerte (z. B. Brix)
  werden aus den Metadaten extrahiert, sodass PLS/PCR/MLP echtes
  Kalibrationstraining fahren können; `AnalysisResult` + `get_analysis_summary` +
  `get_analysis_history` führen die drei Resultatblöcke; `_json_safe` ersetzt
  NaN/Infinity durch null (strikte JSON-Serialisierbarkeit für den Browser).
- `django_project/api/crewai_views.py`: `start_analysis` und der Status-Endpunkt
  liefern `sensor_quality` / `statistical_analysis` / `neural_network` +
  `spectral_data`; `get_crew_status` meldet das volle Agenten-Roster (16
  Missions-Agenten statt 5) inkl. CrewAI-Agentenzahl.
- `django_project/templates/analysis.html` + `static/js/analysis.js`: drei
  Agent-Resultat-Panels im Ergebnis-Modal; Chart zeigt das echte Spektrum;
  Demo-Datenquellen entfernt (`generateSampleSpectralData`, Math.random-Chart,
  Platzhalter-Durchschnittszeit); History-Filter zeigt Crew-Analysen korrekt;
  View-Report öffnet den echten Report (report_id statt request_id).
- Verifikation: `tests/test_op8_crew_results_ui.py` 31/31 grün (Crew-Ausführung,
  striktes JSON, API-Payload-Formen, UI-Panels, keine Demo-Daten, OP6/OP7-
  Regressionen); Vollregression S3–S9, OP1–OP4, OP6, OP7 grün;
  `manage.py check` ohne Befunde; CI um OP8 erweitert.
- Offen (Zielumgebung): End-to-End-Klick im Browser gegen laufende Container
  (Upload → Crew-Analyse → Ergebnis-Panels + Quarto-Report).

### OP48 — EU-Mehrsprachigkeit (i18n) — ABGESCHLOSSEN
- **Plan:** `MULTILINGUAL_I18N_IMPLEMENTATIONPLAN.md` (Freigabe erteilt);
  6 Phasen: Infrastruktur → Templates → Frontend-JS → Backend-Meldungen →
  Übersetzungscontent → Tests/CI. Alle 24 EU-Amtssprachen als Django-Kataloge,
  aktiv vollständig: de/en; fehlende Übersetzungen ehrlich als `untranslated`.
- [x] OP48a Infrastruktur: `settings.py` (24 EU-Sprachen als `LANGUAGES`,
  `LOCALE_PATHS`, `LocaleMiddleware`, `LANGUAGE_CODE='de'`), `nir_web/urls.py`
  (`i18n_patterns` nur für UI-Seiten, `prefix_default_language=False`,
  API-Routen ohne Sprachpräfix, `/i18n/setlang/`), locale-Kataloge de/en
  angelegt; `.gitignore`: `*.mo` als Build-Artefakt.
- [x] Testmatrix `tests/test_op48_i18n.py`: 22/22 grün (Settings-Vertrag,
  Katalog-Header, URL-Wiring inkl. Rückwärtskompatibilität unpräfixierter
  Default-Routen, set_language-Cookie, compilemessages); CI um OP48-Matrix
  + compilemessages erweitert. Regressionen OP3/OP7/OP8 grün;
  `manage.py check` ohne Befunde.
- [x] OP48b Kern-Templates + Sprachumschalter: base.html (Navigation,
  Login/Register, Footer, 24-Sprachen-Umschalter via set_language, html
  lang-Attribut, i18n-Context-Processor), index/login/chatbot/ilias/federated
  auf `{% trans %}`/`{% blocktrans %}` umgestellt (deutsche FL4-Strings als
  msgids normalisiert); login/register/logout in i18n_patterns aufgenommen;
  Maltesisch via EXTRA_LANG_INFO registriert (Django kennt mt nicht);
  Kataloge de/en vollständig gefüllt (94 msgids, keine Lücken — auch
  core/admin.py-Strings); Testmatrix auf 36 Checks erweitert (T4b
  Katalog-Vollständigkeit, T5 lokalisiertes Rendering aller umgestellten
  Seiten in de+en, T5b Umschalter, T5c/d html-lang).
  Verifikation: 36/36 grün; Regressionen OP3 (angepasst: trans-Tag-Library +
  msgid "Projects"), OP7, OP8, FL4 grün; manage.py check ohne Befunde.
- [x] OP48c JS-Strings: `/js-i18n/`-Endpunkt (verhandelter Katalog als JS-Bootstrap, `?format=json` für Tests; Bugfix: LocaleMiddleware erzwingt bei präfix-losen URLs LANGUAGE_CODE — Cookie/Accept-Language-Verhandlung daher im View selbst), `i18n.js` (nirGettext/nirInterpolate, ehrlicher msgid-Fallback), base.html lädt Katalog+Helper vor main.js; alle benutzersichtbaren JS-Meldungen in files/agents/analysis/jobs/spectra.js auf nirGettext umgestellt (82 msgids, Kataloge de/en ergänzt); Testmatrix 46/46 grün, Regressionen OP3/OP25/OP15/FL4 grün; `node --check` sauber.
- [x] OP48d Backend-Meldungen: alle statischen API-Strings ('error'/'message') in api/*_views.py auf gettext umgestellt (106 msgids, Kataloge de/en ergänzt; 'status'-Werte als API-Vertrags-Keys bewusst unübersetzt); federated_views mit gettext_lazy (Offline-Kernfunktion); neue ApiLanguageMiddleware aktiviert Cookie/Accept-Language-Verhandlung auf unpräfigierten /api/- und /js-i18n/-Routen; Testmatrix 53/53 grün; Regressionen OP1/OP3/OP8/OP11/OP13/OP15/OP24/OP25/OP28/S6/FL4 grün.
- [x] OP48e Übersetzungscontent: 22 zusätzliche EU-Kataloge als ehrlich leere .po-Dateien (Übersetzung durch native Speaker/Fachlehrkräfte, kein Fake — fr fällt ehrlich auf Default zurück); Chatbot-System-Prompt sprachabhängig (Antwort-Sprache = Anfrage-Sprache); Quarto-Berichtssprache pro Aufruf konfigurierbar (QuartoConfig.lang, Default de, lang-Platzhalter in allen 7 qmd-Templates); ILIAS-Sync trägt die aktive Sprache des initiierenden Nutzers im Payload. Testmatrix 62/62 grün; Regressionen S6/FL4/FL5/OP24/OP11/OP23/OP3/OP25 grün.
- [x] OP48f Rest-Templates: alle 19 verbleibenden UI-Templates (dashboard, analysis, files, agents, spectra, jobs, settings, documentation, projects, register, workflow_list, workflow_results, sensor_list, sensor_detail, spectrum_database, spectrum_detail, crew_report, project_report, dashboard_colorful) auf `{% trans %}` umgestellt; präexistente Defekte in workflow_list/workflow_results repariert (verstümmelte `{%`-Präfixe, `|format` → `floatformat:2`, `|sum(attribute=…)` → `|length`); 706 Template-msgids in die Kataloge gepflegt (de: 513 neue Übersetzungen inkl. aller Fließtexte; en: 611 identity + 33 deutsche msgids rückübersetzt); msgfmt clean, render_check ALL OK; OP48-Testmatrix 62/62 grün; Regressionen OP3 (45/45), OP25 (65/65), OP8 (77/77), OP8-Crew (38/38), OP15 (44/44) grün. OP48 damit abgeschlossen.

### OP49 — Sensor-Websearch (Opt-in) + DIY-Spektrometer-Übersicht — ABGESCHLOSSEN
- [x] Opt-in Sensor-Websearch: `services/sensor_websearch.py` fragt bei
  unbekannten Sensoren das lokale Ollama ab (`NIR_SENSOR_WEBSEARCH=1`,
  Default off; `NIR_SENSOR_WEBSEARCH_URL`/`NIR_SENSOR_WEBSEARCH_MODEL`
  konfigurierbar); Ergebnisse als extern/unverifiziert markiert
  (Ehrlichkeitsregel); SensorAgent (`collect`) liefert die websearch-Sektion
  nur bei aktivem Opt-in — Offline-/CI-Verhalten unverändert.
- [x] DIY-Spektrometer-Übersicht: `/api/projects/sensors/diy/`
  (DiySpectrometerView + sensor_diy.html) mit 5 kuratierten Projekten
  (OpenSpectrometer, DIY Spectroscope Thingiverse, Public Lab Desktop
  Spectrometer, Smartphone-CD-Spektrometer, SpecPhone/DualSpec), 7
  Bauanleitungs-/Tutorial-Links und Opt-in-Ollama-Suche auf der Seite;
  verlinkt von der Sensor-Übersicht; Route vor sensor-detail registriert;
  21 neue msgids in de/en-Katalogen (i18n-konform, OP48-Muster).
- [x] Verifikation: Testmatrix `tests/test_op49_sensor_diy.py` 23/23 grün;
  Regressionen OP29 (53/53), OP48 (62/62) grün; `manage.py check` ohne
  Befunde; CI um OP49-Matrix erweitert.
- Offen (Zielumgebung): Ollama dort starten und `NIR_SENSOR_WEBSEARCH=1`
  setzen, dann Sensor-Suche mit einem realen unbekannten Sensor testen.

### OP50 — Release-Fix: Robuster Ollama-Start (LLM-first) — ERLEDIGT
Zentraler Probe services/ollama_health.py (Retry/Backoff/Cache), alle
KI-Gates umgestellt; background_crew OLLAMA_URL nachgeruestet; Compose
(dev/prod/host-backend) wartet auf ollama service_healthy, Healthcheck
10s/12x/start_period 60s, OLLAMA_KEEP_ALIVE=24h. Testmatrix
test_op50_ollama_startup.py 19/19 gruen, in CI aufgenommen.

### OP51 — Startskript-Konsolidierung: EIN Startweg (Docker) — ERLEDIGT
Legacy-Host-Starter im django_project/ (start.sh mit kill -9 + beliebiger
Port, dev_server.sh mit Privatpfad u. a.) erzeugten parallele
Django-Instanzen (8000/8001). start/stop/check sind jetzt Docker-
Delegatoren, vier Alt-Starter entfernt, START_SERVER.md Docker-only.
Testmatrix test_op51_start_scripts.py 20/20.

### OP52 — Menue-Umbau + Kalibrierungs-Uebersicht — ERLEDIGT
Hauptmenue neu geordnet (Projekte -> Sensoren -> Kalibrieren -> Lernen mit
Kursen, Workflow als Startseite zuletzt), Spektren-Datenbank als Unterpunkt
unter Projekte, ILIAS-Kurse als Unterpunkt unter Lernen. Neue Seite
/calibration/ listet die PLS/PCR-Kalibrationen aller analysierten Projekte
aus den Crew-Ergebnissen. i18n de/en ergaenzt. Testmatrix
test_op52_nav_menu.py 40/40.

### OP53 — Sensor-Seiten (KI), Dokumenten-Datenbank, Referenz-Check — ERLEDIGT
Eine Plattform-Seite pro Sensor sammelt alle Informationen (Adapter,
Nutzung, Einstellungen, Vorschlaege, hochgeladene Dokumente) plus
KI-Ueberblick (lokal, live, ehrlicher Fallback). Dokumenten-Upload pro
Sensor (Datenblatt, Handbuch, Kalibrierung, Foto, Software,
Publikation, Sonstiges) erweitert die Sensor-Datenbank; beim
Projekt-Anlegen wird automatisch geprueft, ob der genutzte Sensor
referenziert ist (inkl. Link zur Sensorseite). Testmatrix
test_op53_sensor_pages.py 37/37.

### OP56 — Release-Fixes: Bericht-Chatbot, Metadaten-Speichern, Sensor-Vorschlaege — ERLEDIGT
- Abschlussbericht-Chatbot: POST ohne X-CSRFToken lief auf DRF-403 und fiel
  still auf die Offline-Wissensbasis ("Ollama offline" obwohl verfuegbar);
  Widget sendet jetzt Token + Session-Credentials.
- Metadaten-Editor: Detail-View setzt jetzt ensure_csrf_cookie, Formular
  traegt Hidden-Token - Speichern funktioniert zuverlaessig.
- Sensor-Einstellungen (z. B. SparkFun Triad) aus Katalog + Datenbank werden
  beim Projekt-Anlegen als Ein-Klick-Vorschlaege fuer leere Metadaten-Felder
  angeboten.
- Aufbereitungs-Banner zeigt verstrichene Zeit + Datensatz-Anzahl.
- Testmatrix tests/test_op56_report_fixes.py 18/18; CI registriert.

### OP57 — Analyse asynchron: Crew-Lauf im Hintergrund — ERLEDIGT
- Release startet die 15-Agenten-Analyse in einem Background-Thread
  (wie OP55 fuer die Aufbereitung); Antwort sofort mit analyzing:true.
- Neuer Status-Endpoint /api/projects/<id>/crew-status/; Zwischenstaende
  werden pro Datensatz persistiert -> sichtbarer Fortschritt.
- Testmatrix tests/test_op57_async_crew.py 16/16; CI registriert.

### OP59 — Release: Perfekte Ansible-Installationsroutine — ERLEDIGT
- Playbook installiert Docker automatisch nach (docker.io,
  docker-compose-v2; Pflicht statt optional - ohne Docker keine
  KI-Analysen), sichert den Daemon (started/enabled) und bricht bei
  fehlgeschlagenem Backend-Stack-Start hart ab statt nur einen Hinweis
  zu drucken.
- Verifikation Ende-zu-Ende: Django-HTTP, Ollama inkl.
  LLM-Modell-Check (kein stiller Fallback-Betrieb), Qdrant /healthz,
  Redis PING; Verifikationsbericht mit Abbruch bei fehlgeschlagenem
  Check.
- Packaging prueft den Payload auf OP5/MQTT-Lecks und bricht bei Fund
  ab (OP5 bleibt vom Release ausgeschlossen).
- INSTALL_NIR_INTELLIGENCE.md ist die kanonische Release-Anleitung.
- Testmatrix tests/test_op59_release_install.py 40/40; CI registriert.

### OP58 — Federated-Optionen verstaendlich — ERLEDIGT
- Federated-Seite: Intro (Parameter-only-Vertrag, 3-Schritt-Flow), je
  Lernmodus/Strategie/Privacy-Stufe eine Erklaerung mit Wirkung und
  Preis; Status/Privacy als lesbare Definition-Liste statt JSON-Dump.
- Testmatrix tests/test_op58_federated_options.py 20/20; CI registriert.

### OP5 — MQTT-Worker + kommerzielle Spektrometer-Adapter (S4) — OFFEN
- Echter MQTT-Broker-Worker (Acquisition-Layer); weitere Geräte-Adapter
  (NIR, UV-Vis, Raman, FTIR) nach Laborente.

### OP89 — Change-Impact Test Gate (Tester Agent 2.0) — ✅ ERLEDIGT (2026-10-23, PR #231 gemerged 25bd96a)

### OP90 — Test-Matrizen OP63/OP79: Thread-sichere Test-DB (Temp-Datei statt `:memory:`) — ✅ ERLEDIGT (2026-10-23, PR #234 gemerged f154568)
Befund aus Verifikation PR #229/#230 (pre-existing seit OP63): OP63/OP79
setzten SQLite `:memory:`; `execute_fusion` startet `build_preparation_report`
in einem Daemon-Thread -> Thread sah leere DB -> `OperationalError: no such
table: core_analysisproject` im Log (nach RESULT, Exit 0, kosmetisch).
Fix (nur Test-Setup): `:memory:` -> Temp-Datei-DB (`tempfile.mkdtemp`),
nach `migrate` `connections.close_all()`, Cleanup via `atexit`.
`services/project_fusion.py` unangetastet. Verifiziert: OP63 45/45,
OP79 56/56, beide ohne Traceback; Regression OP80/OP55/OP63_st3 grün.

### OP91 — Health-Check ehrlich: flower-URL-Bug + agents_loaded (Registry statt toter DB-Tabelle) — ✅ ERLEDIGT (2026-10-23, Commit 146bab1)
Befund aus lokalem Systemtest nach Merge #231/#234/#237 (2026-10-23):
`GET /health/` meldet `status: healthy`, aber zwei Werte luegen.

1. **flower-URL-Parsing-Bug** (`django_project/api/views.py:311-312`):
   `flower_url = 'http://flower_server:5556'` +
   `_check_service_health(flower_url, 'Flower')` baut die URL
   `'http://flower_server:5556Flower'` (health_path ohne fuehrendes `/`)
   -> `Failed to parse: ... is not a valid host or port`. Alle anderen
   Dienste nutzen Pfade MIT `/` (`/healthz`, `/api/tags`, `/health`).
   Flower-Server selbst: `services/flower_server.py` FlowerHTTPHandler
   antwortet auf `GET /health` (Zeile 173-177) mit 200
   `{'status': 'healthy', ...}` — aber der flwr-SuperLink-Entrypoint
   (`scripts/flower_superlink_entry.py`, Ports 9091/9092) hat KEINEN
   HTTP-Health-Endpunkt; der Dev-Compose startet SuperLink, nicht
   `flower_server.py`. Ehrlicher Check: TCP-Connect auf 9091 (Runtime-API-
   Port laut Entrypoint) ODER HTTP-GET gegen `flower_server:5556/health`
   wenn der Legacy-Server laeuft. Entscheidung: TCP-Connect auf den
   SuperLink-Runtime-API-Port (9091) — das ist der Dienst, der im
   Dev-Compose tatsaechlich gestartet wird.
2. **agents_loaded: 0** (`views.py:279`): zaehlt `Agent.objects.count()`
   — die Legacy-DB-Tabelle `core_agent`, die NIEMAND befuellt (kein
   Management-Command, kein `Agent.objects.create` in Produktion).
   Die echten Agenten laufen ueber `agents/AGENT_REGISTRY` (34 Eintraege
   seit OP88). → `agents_loaded = len(AGENT_REGISTRY)` (Import-versuch,
   Fallback 0 bei Importfehler — nie crash).

### Umfang
- `django_project/api/views.py` (HealthCheckView):
  (a) flower-Check: TCP-Connect auf `flower_server:9091` (SuperLink
      Runtime-API-Port, siehe `scripts/flower_superlink_entry.py`),
      Timeout 2s; `healthy` bei erfolgreichem Connect, sonst
      `unhealthy: <grund>`.
  (b) `agents_loaded`: `len(AGENT_REGISTRY)` statt `Agent.objects.count()`;
      ImportError -> 0 (ehrlich, kein Crash).
- Neue Matrix `tests/test_op91_health_check_honest.py`:
  (a) flower-URL wird nicht mehr als `host:port+path` ohne `/` gebaut
      (Source-Check + Unit-Test der URL-Konstruktion);
  (b) TCP-Connect-Logik gegen lokalen Listener (loopback) testbar;
  (c) `agents_loaded` spiegelt `AGENT_REGISTRY` (34) wider — live via
      Django-Testclient gegen `/health/`;
  (d) Health-Response-Vertrag: `agents_loaded` int >= 0,
      `docker_services.flower` ist String ohne 'Failed to parse'.

### Out of Scope
- Kein Flower-Server-Health-Endpunkt implementieren (SuperLink ist
  externes flwr-Paket; TCP-Connect ist der ehrliche verfuegbare Check).
- Keine Aenderung an `services/flower_server.py` (Legacy-HTTP-Handler
  bleibt; `/health` dort ist unberuehrt).
- Kein Befuellen der Legacy-`core_agent`-Tabelle (toter Indikator wird
  ersetzt, nicht gerettet).
- faiss-Dev-Setup (kein Server im Container) bleibt — wird separat als
  Dev-Doku-Thema behandelt, nicht in diesem OP.

### Success Criteria
- `GET /health/` lokal (Docker-Stack): `agents_loaded` = 34,
  `docker_services.flower` ohne 'Failed to parse' (healthy oder
  ehrliches unhealthy mit Verbindungsgrund).
  ✅ OP91-Matrix T4b/T4d/T4e: agents_loaded == len(AGENT_REGISTRY),
     flower-Status ohne 'Failed to parse'.
- Neue Matrix `tests/test_op91_health_check_honest.py` **27/27** grün.
- Regression: OP89-Smoke 15/15 (3 aufeinanderfolgende Läufe),
  OP88 48/48, OP76 21/21, OP89 47/47, api.views-Matrizen
  (fa1_password 12/12, fa1_settings 9/9, mui_scientific 6/6) grün;
  `manage.py check` 0 issues.
- Anti-Code-Creep: nur `views.py` (+28/−5) + neue Testmatrix + Doku.
- `covers:`-Tag in OP91-Matrix: `api.views` wird vom OP89-Gate korrekt
  zugeordnet (Impact-Map rebuild; Gate GREEN gegen origin/main).

### Notiz: Smoke-Test-Flake (nicht OP91-caused)
Ein einzelner Smoke-Lauf zeigte 403/302 auf crew-status/delete — Baseline
(stash, ohne OP91-Code) war 15/15 grün, 3 Folge-Runs mit OP91 ebenfalls
15/15. Ursache: Projekt- ohne Dateien -> release 422 -> Crew-Status
403/302-Race (bekanntes OP57/OP55-Verhalten, nicht durch OP91 berührt).

### Selbstprüfung (§7, 11 Fragen) — beantwortet vor Umsetzung
1. Mission Statement gelesen? Ja (Session-Start + heute erneut).
2. AGENTS.md + AGENT_FRAMEWORK_INIT_PROMPT gelesen? Ja.
3. Roadmap-Eintrag vor Umsetzung? Ja — dieser Abschnitt.
4. Kleinste korrekte Lösung? Ja — 2 Stellen in views.py, keine neuen Deps.
5. Keine neuen Abhängigkeiten? Ja — stdlib `socket`.
6. Alle Datei-Formate/Spektrometer? N/A (Health-Check, kein Spektrum-Code).
7. Weaviate out of scope? Ja — Qdrant bleibt, unverändert.
8. paperless-mistral-setup/ frozen? Ja — unberührt.
9. Lizenz-Compliance? Keine neuen Deps.
10. Ehrlichkeits-Regel? Kern des OPs — Health-Werte werden wahr.
11. Iterations-Regel? Ziel: ERRORS=0, CRITICAL_WARNINGS=0 nach Abschluss.

### OP92 — Reingest-Spinner 3h + LLM-Timeout-Bugs (env-leer, timeout=None, Stale-Detection) — ✅ ERLEDIGT (2026-10-23, Branch vibe/op92-reingest-spinner-timeouts-e1efba)
Befund aus Nutzer-Feedback (2026-10-23, nach Merge #238/OP91): Drei
aufeinanderhaengende Bugs, die zusammen den endlosen Spinner erklaeren.

1. **`NIR_LLM_TIMEOUT=''`-Crash** (sichtbar im Log: `Internal Server Error:
   /api/chatbot/message/` + `ValueError: invalid literal for int() with base
   10: ''` in `services/metadata_llm.py:104` und `chatbot_service.py:71`):
   `docker-compose.yml:204` reicht `NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT:-}`
   — bei unset ein LEEKER STRING in den Container. `int('')` crasht.
2. **`chatbot_service.py:75` `self.timeout = timeout`** — ueberschreibt den
   env-Default mit `None` (wenn `timeout=None` uebergeben) ->
   `requests.post(timeout=None)` -> KEIN Timeout, ewiger Hang.
3. **Reingest-Spinner laeuft 3h** trotz fertigem/gestorbenem Hintergrund-
   Thread: OP78-Reingest startet `Thread(daemon=True)`. Ein Container-
   Restart (`docker compose up -d` nach git pull) KILLT den daemon-Thread.
   Der Report bleibt geleert (`{'user_options': ...}`) -> Status-Endpunkt
   liefert `ready=False, error=None` -> JS pollt ENDLOS (kein Timeout,
   keine Stale-Detection). Log zeigt zwar `Preparation report for project
   28c290b7: 3/3 usable datasets` — aber der User-Report-Dump crashte am
   Platzhalter `<Projektname>` (DoesNotExist), die echte Projekt-ID ist
   unbekannt; der Mechanismus (Thread killed by restart -> leerer Report
   -> endloser Poll) ist strukturell begruendet.

### Umfang
- `docker-compose.yml:204`: `NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT:-}` ->
  `${NIR_LLM_TIMEOUT:-120}` (Default statt leer; 120 s = OP83-Default).
- `services/metadata_llm.py` (`OllamaMetadataClient.__init__`):
  `int(os.environ.get("NIR_LLM_TIMEOUT", "300"))` und
  `int(os.environ.get("NIR_LLM_ATTEMPTS", "1"))` robuster Parse —
  leer/ungueltig -> jeweiliger Default (300 bzw. 1), nie ValueError.
- `services/chatbot_service.py` (`OllamaChatClient.__init__`): gleicher
  robuster Parse; Bug `self.timeout = timeout` (zeile 75, ueberschreibt
  env-Default mit None) entfernen — `self.timeout` nur setzen wenn
  `timeout is not None`.
- `django_project/api/project_views.py` (`ProjectPrepareStatusView.get`):
  Stale-Detection — wenn `not ready and not error` und
  `progress.last_update` parsebar und aelter als 10 Minuten ->
  `'stale': True` + `'error'` mit ehrlichem Hinweis (deutsch:
  "Aufbereitung seit ueber X Minuten ohne Lebenszeichen — bitte Seite
  neu laden oder erneut ausfuehren.").
- `django_project/templates/project_report.html` (Preparing-Poll-JS):
  (a) `data.stale` wie `data.error` behandeln (roter Alert, kein Reload);
  (b) harter Poll-Cap: nach 30 Minuten ohne ready/error -> Alert
  "Aufbereitung dauert ungewoehnlich lange" + Polling stoppen.

### CI-Fix (im selben PR, pre-existing Bug)
- `change-impact`-Job: `compilemessages`-Step fehlte (nur Vollmatrix-Job
  hatte ihn). OP49 crashte in CI mit `FileNotFoundError: No translation
  file found for domain: 'django'` — lokal nicht sichtbar, weil die
  `.mo`-Files in der Sandbox kompiliert sind. OP91-CI (#238) selektierte
  OP49 nicht (nur 5 Matrizen), deshalb erst bei OP92 aufgefallen (43
  Matrizen via `services.metadata_llm`/`chatbot_service`-Impact).
- Fix: `pip install polib` + glob-compile aller 24 `locale/*/LC_MESSAGES/
  django.po` -> `.mo` VOR dem Gate-Run. polib ist abhaengigkeitsfrei
  (kein gettext/msgfmt noetig, kein apt-get in diesem Job).
- Verifiziert: OP49 ohne .mo crasht lokal mit EXAKT dem CI-Fehler;
  mit polib-Compile 23/23 gruen.

### Out of Scope
- Kein Wechsel von daemon-Thread auf Celery/Worker (keine neue Abhaengigkeit,
  Anti-Code-Creep); Stale-Detection macht den Tod des Threads sichtbar.
- Kein automatischer Re-Run der Aufbereitung nach Container-Restart
  (zu invasiv; ehrlicher Fehler + manueller Reingest genuegt).
- Kein Fix der `ilias`-Container-Restarting-Beobachtung (separates Thema).
- Kein Wechsel des Vollmatrix-Jobs auf polib (der hat bereits
  compilemessages mit gettext — unveraendert).

### Success Criteria
- ✅ Neue Matrix `tests/test_op92_reingest_spinner_timeouts.py` **36/36** gruen:
  (a) compose: `NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT:-120}` (kein `:-}`);
  (b) `metadata_llm`/`chatbot_service`: `NIR_LLM_TIMEOUT=''` -> OP83-Default
     120, nie ValueError; unset -> 120; ungueltig -> Fallback 300;
     chatbot `self.timeout` nie None (Bug `self.timeout = timeout` entfernt);
  (c) Status-Endpunkt: stale nach 10 min ohne last_update -> stale+error
     (Live-Testclient: 5 Cases — fresh/stale/live/ready/error);
  (d) Template-JS: `data.stale` behandelt wie error, Poll-Cap 30 min;
  (e) py_compile aller geaenderten Dateien;
  (f) **CI-Fix verifiziert**: change-impact-Job polib-Compile-Step +
     OP49-Reproduktion (ohne .mo crasht mit exakt dem CI-Fehler,
     mit .mo 23/23 gruen).
- ✅ Regression: OP55 14/14, OP78 35/35, OP83 21/21, OP50 35/35,
  OP49 23/23, OP89 47/47, Smoke 15/15, `manage.py check` 0 issues.
- ✅ **CI-Fix (pre-existing Bug, nicht OP92-caused):** Der `change-impact`-
  Job hatte KEINEN compilemessages-Step (nur der Vollmatrix-Job). OP49
  crashte in CI mit `FileNotFoundError: No translation file found`.
  Lokal auf main gruen (weil .mo hier kompiliert sind), in CI rot.
  OP91-CI (#238) selektierte OP49 nicht (nur 5 Matrizen) -> nicht
  aufgefallen. Fix: polib-basierter Compile-Step im change-impact-Job
  (`pip install polib` + glob-compile aller 24 locale-Kataloge, VOR dem
  Gate-Run). polib ist abhaengigkeitsfrei, kein gettext/msgfmt noetig.
- ✅ Anti-Code-Creep: 4 kleine Code-Stellen + 1 Compose-Zeile + neue Matrix
  + Doku; keine neuen Abhaengigkeiten.
- OP89-Gate gegen origin/main GREEN (covers: api/project_views.py).

### Selbstpruefung (§7, 11 Fragen) — beantwortet vor Umsetzung
1. Was gefordert? 3h-Spinner nach Reingest fixen + env-Crash-Bugs
   (Nutzer-Feedback 2026-10-23 mit docker logs).
2. Master Objectives? Zuverlaessige Plattform + Ehrlichkeits-Regel
   (Spinner darf nicht ewig luegen; Health/Status ehrlich).
3. Agenten betroffen? Tester Agent (neue Matrix); keine Agent-Aenderung.
4. Tests? Neue Matrix OP92 (a-e) + Regression OP55/OP78/OP83/OP50/Smoke.
5. Wiederverwendung? `_PrepTrace.progress.last_update` (OP78),
   OP83-Env-Guards, OP55-Status-Endpunkt, OP91-TCP-Helper-Muster.
6. Code Creep? 4 kleine Stellen + 1 Compose-Zeile; keine neuen Deps.
7. Alle Datei-Formate/Spektrometer? N/A (kein Spektrum-Code betroffen).
8. CrewAI-Agentennetzwerk? Unberuehrt.
9. Software-Stufe? Bugfix; Stufe bleibt.
10. Workflow-Einbindung? Status-Endpunkt + Template direkt im
    Reingest-Flow erreichbar.
11. UI? Spinner stoppt ehrlich mit Fehlermeldung statt endlos zu laufen.

### OP89 — Change-Impact Test Gate (Tester Agent 2.0) — IN ARBEIT (PO-Freigabe 2026-10-22)
Nutzer-Befund: Zu viel manuelle Zeit für einfache Tests — pro OP wird eine
Testmatrix von Hand geschrieben, in CI als einzelner `python tests/...`-Aufruf
eingetragen, und die Auswahl der relevanten Tests erfolgt manuell. Ziel: Der
Tester Agent wird so weiterentwickelt, dass er jeden zum Merge vorgeschlagenen
Code-Change vollständig testet — Funktionen, Gesamtworkflow und interagierende
Teile — ohne manuelle Testauswahl.

### Umfang
- `scripts/build_test_impact_map.py` (neu): Baut eine statische Impact-Map
  (Source → abhängige Module via Import-Graph für `agents/`, `services/`,
  `django_project/`; JS-Module via `static/js/`-Abhängigkeiten) und ordnet
  jede Testmatrix (`tests/test_*.py`) den von ihr abgedeckten Source-Modulen
  zu (Tag-Konvention `# covers:` + heuristischer Import-Scan). Ausgabe:
  `tests/.impact_map.json` (generiert, gitignored, bei Bedarf rebuild).
- `tests/test_workflow_smoke.py` (neu): Gesamtworkflow-Smoke als ein
  Durchlauf — Projekt anlegen → Upload → Ingest/Aufbereitung → Analyse-Trigger
  → Report → Chatbot-Kontext — gegen Django-Testclient (loopback, keine
  externen Dienste), mit ehrlichem Degraded-Handling (fehlendes Ollama/Qdrant
  wird als solcher Status gemeldet, nie als grüner Test). Deckt die
  interagierenden Teile ab, die einzelne OP-Matrizen nicht sehen.
- `scripts/run_change_tests.py` (neu): Das eigentliche Gate. `git diff`
  (Basis: `--base` Branch/Commit, Default `origin/main...HEAD` bzw.
  `main...HEAD`) → betroffene Source-Dateien → Impact-Map → betroffene
  Matrizen + immer `test_workflow_smoke.py` + `manage.py check` +
  `node --check` auf geänderte JS-Dateien. Ein Prozess für alle Matrizen
  (kein 85-facher Python-Startup), Exit-Code 0/1, klare Ausgabe welche
  Matrizen warum laufen. `--full` für die komplette Matrix (CI auf main).
- `dev_framework/cli.py`: `test --impact [--base REF]` angebunden.
- CI: zusätzlicher Job `change-impact` (nur bei `pull_request`), der das
  Gate gegen `origin/main...HEAD` laufen lässt; der bestehende Job
  `test-matrices` (Vollmatrix auf push/PR) bleibt unverändert.

### Out of Scope
- Keine Änderung an bestehenden OP-Matrizen (Rückwärtskompatibilität: sie
  laufen weiter einzeln via `python tests/test_opXX_*.py`).
- Keine neuen Abhängigkeiten (stdlib + git + bestehende Test-Deps).
- Kein Ersatz der CI-Vollmatrix auf main — das Gate ist die schnelle
  PR-Schleife, die Vollmatrix bleibt das Merge-Backstop.

### Success Criteria
- `python scripts/run_change_tests.py --base <ref>` wählt selbstständig die
  betroffenen Matrizen + Smoke-Test; lokal gegen echten Diff verifiziert.
- `tests/test_workflow_smoke.py` läuft offline grün (ehrliches Degraded bei
  fehlenden externen Dienste, kein Fake-Erfolg).
- Neue Matrix `tests/test_op89_change_impact_gate.py` grün; CI-Job
  `change-impact` in `ci.yml` registriert.
- Selbstprüfung §7 beantwortet; Anti-Code-Creep: kleinste korrekte Lösung,
  bestehende Matrizen unberührt.

### OP88 — Review & Optimierung der übrigen Development-Framework-Agenten — ERLEDIGT (2026-10-22, PR folgt)
Alle 6 Befunde umgesetzt; zusaetzlich zwei Nebenbefunde aus dem Live-Test
gefixed (CLI test --agent default + Parser-Robustheit gegen verschachtelte
Ausgabe). Verifikation: Matrix 48/48, Regressionen OP89/OP63/OP12/OP89-Smoke
gruen, manage.py check 0 issues, dev_framework validate/quality/test/docs/info
live ohne Crash.
Nutzer-Auftrag nach OP89: 'Bitte ueberpruefe die anderen Agenten ebenso und
verbessere/optimiere wo moeglich.' Review der dev_framework-Agenten
(tester, quality, validator, generator, docs, server, cli) + agents-Registry
mit laufendem Framework. Sechs Befunde, kleinste korrekte Fixes:

1. **Registry unvollstaendig** (`agents/__init__.py`): `chatbot_agent`,
   `ilias_course_agent`, `sensor_agent` fehlen — obwohl produktiv genutzt
   (project_views, dashboard_views, report_chatbot, ilias_course_agent_runner).
   → In AGENT_REGISTRY aufnehmen (Import + Key), verifizieren.
2. **Tester meldet silent success** (`dev_framework/tester.py`):
   `python -m dev_framework test` liefert 'Tests passed! 0 passed, 0 failed'
   und exit 0 — die erwartete tests/unit|integration|e2e-Struktur existiert
   nicht, die reale flache OP-Matrix (tests/test_*.py) wird nicht gefunden.
   → Ehrlicher Fallback: flache Matrix erkennen + als ein Lauf melden;
   `time`/`re` von Datei-Ende an den Anfang (PEP 8); kein Fake-Erfolg.
3. **Validator: toter + false-positiver Check** (`dev_framework/validator.py`):
   (a) `_validate_agent_mandatory_files` prueft `agents/<snake>.py` statt
   `agents/<snake>_agent.py` — laeuft ins Leere, nie ein echter Befund.
   (b) PY_007 meldet 'Recommended attribute not set' obwohl BaseAgent die
   Attribute via super().__init__ setzt (99 false positives).
   → (a) Pfad korrigieren, (b) Check gegen BaseAgent-Vererbung pruefen.
4. **Quality: fehlende Tools = 692 Errors + falscher Exit-Code**
   (`dev_framework/quality.py`): black/flake8/isort/mypy nicht installiert →
   pro Datei 4 'not installed'-Errors; `quality --all --check` loggt
   'failed with 692 issues', exit aber 0 (Bug in run_quality: `return 1`
   im else-Zweig nach logger.error ist toter Code — siehe Handler).
   → Fehlende Tools als 'skipped' (info, nicht error) melden; Exit-Code
   ehrlich setzen (1 bei echten Issues, 0 bei skipped-only).
5. **Docs: relative_to-Crash + toter CLI-Alias** (`dev_framework/docs.py`,
   `cli.py`): `docs_file.relative_to(self.project_root)` crasht wenn
   docs_dir nicht unter project_root (z. B. Tests mit tmp_path);
   `python -m dev_framework docs` existiert nicht (nur `generate docs`),
   obwohl __init__.py und cli-Epilog es suggerieren.
   → relative_to mit Fallback auf absoluten Pfad; CLI-Alias `docs` als
   eigener Subcommand (delegiert an generate docs).
6. **Doc-Drift PRODUCTION_READINESS.md**: '31 agents total', aber 34
   Agent-Dateien existieren; 3 fehlen in der Registry (siehe 1).
   → Nachtrag mit aktuellem Stand (34 Dateien, 34 Registry-Eintraege).

### Out of Scope
- Kein Redesign des Frameworks; keine neuen Abhaengigkeiten.
- Keine Aenderung an produktiven Agent-Implementierungen (nur Registry-Wiring).
- Keine neuen JSON-Configs fuer Agenten ohne JSON (Validator-Warnung
  AGENT_002 bleibt bewusst — Doku-Entscheidung, kein Code-Fix).

### Success Criteria
- `from agents import AGENT_REGISTRY` enthaelt chatbot/ilias_course/sensor.
- `python -m dev_framework test` findet die flache OP-Matrix (oder meldet
  ehrlich 'no tests found', exit 1 — nie silent 0/0 success).
- `python -m dev_framework validate` ohne die 99 PY_007-False-Positives und
  ohne toten Mandatory-File-Check.
- `python -m dev_framework quality --all --check` ohne installierte Tools:
  skipped-Meldung, exit 0 (degraded ehrlich, kein Fake-Fehler).
- `python -m dev_framework docs --all` und `generate docs --all` beides OK.
- Neue Matrix tests/test_op88_dev_framework_review.py gruen; CI registriert.

---

## 4. Abgleichs-Regel (bindend)

Vor jedem Entwicklungsschritt gilt:

1. `AGENT_FRAMEWORK_INIT_PROMPT.md` → `MISSION_STATEMENT.md` → Startsequenz-Dateien lesen.
2. Prüfen: Ist der geplante Schritt in dieser Roadmap enthalten? Wenn nicht: zuerst
   Head-of-Development-Freigabe und Roadmap-Update, dann Umsetzung.
3. Nach Abschluss eines Schritts: die zugehörige Lücken-Nummer (G1–G8) und
   den Roadmap-Schritt (S1–S9) in dieser Datei als erledigt markieren (inkl. Datum und Verweis
   auf Commit/PR).
