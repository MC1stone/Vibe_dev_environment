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

### OP3a — Echter flwr-Client-Server-Betrieb (S9) — OFFEN
- FederatedLearningService-Kern an den Flower-Transport
  (`services/flower_server.py`) gegen laufende Container anbinden.

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

### OP5 — MQTT-Worker + kommerzielle Spektrometer-Adapter (S4) — OFFEN
- Echter MQTT-Broker-Worker (Acquisition-Layer); weitere Geräte-Adapter
  (NIR, UV-Vis, Raman, FTIR) nach Laborente.

---

## 4. Abgleichs-Regel (bindend)

Vor jedem Entwicklungsschritt gilt:

1. `AGENT_FRAMEWORK_INIT_PROMPT.md` → `MISSION_STATEMENT.md` → Startsequenz-Dateien lesen.
2. Prüfen: Ist der geplante Schritt in dieser Roadmap enthalten? Wenn nicht: zuerst
   Head-of-Development-Freigabe und Roadmap-Update, dann Umsetzung.
3. Nach Abschluss eines Schritts: die zugehörige Lücken-Nummer (G1–G8) und
   den Roadmap-Schritt (S1–S9) in dieser Datei als erledigt markieren (inkl. Datum und Verweis
   auf Commit/PR).
