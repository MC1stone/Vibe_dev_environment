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
| G5 | **Keine Spektrometer-Abstraktionsschicht:** Geräteintegration nicht über einheitliches Adapter-Muster nachgewiesen | Grundregel: alle Spektrometer | Gerätetreiber-/Adapter-Schicht einführen; bestehende ESP32-S3-Integration als erster Adapter (S4) |
| G6 | **Chatbot für Ergebnisdiskussion:** Ollama-Service vorhanden, aber kein dedizierter Ergebnis-Chatbot als Feature nachgewiesen | Master Objective 10 | RAG-/Chatbot-Feature auf Ollama/Mistral-Basis mit Qdrant-Anbindung (S6) |
| G7 | **Selbstoptimierung/Updates:** Selbstoptimierung als Ziel formuliert, aber kein Update-Mechanismus für Open-Source-Komponenten implementiert | Master Objective 15 | Update-Monitoring + Abhängigkeitsprüfung (z. B. CI-Job) definieren (S7) |
| G8 | **`framework/` unvollständig:** Nur Backend-/Frontend-Skills implementiert, Rest ist Skeleton | Init-Prompt referenziert Framework-Dokumentation | Entweder vervollständigen oder als Referenz deklarieren und nicht als aktive Komponente (S1) |

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

### S4 — Spektrometer-Abstraktionsschicht (schließt G5)
- Einheitliches Adapter-Muster (Device-Driver-Interface): Messdaten, Metadaten,
  Kalibrationsparameter, Gerätestatus.
- Erste Adapter: DIY-Matchbox, ESP32-S3-Kameraspektrometer (MQTT-Anbindung aus `HANDHELD/mqtt` übernehmen).
- Danach kommerzielle Geräte (NIR, UV-Vis, Raman, FTIR) als weitere Adapter.

### S5 — Integration napari-Visualisierung & Spektrenvergleich
- napari-App aus `HANDHELD/napari_app` in die Plattform integrieren (Visualisierung,
  Vergleich neuer Spektren mit vorhandenen; Master Objectives 11, 13, 14).
- FAISS (Nearest-Neighbour/Spektrumvergleich) und Qdrant (Embedding-Ähnlichkeit) anbinden.

### S6 — Ergebnis-Chatbot (Master Objective 10)
- Chatbot auf Ollama/Mistral:latest mit Qdrant-RAG über Analyseergebnisse und
  Dokumentation; Anbindung im Django-Frontend.

### S7 — Selbstoptimierung & Update-Monitoring (Master Objective 15)
- CI-Job/Skript: Prüfung genutzter Open-Source-Komponenten (Docker-Images, pip-Pakete)
  auf Updates; Bericht als Quarto-Dokument.
- Optimierungsprotokoll für Kalibrationen (Optuna ist bereits in `requirements.txt`).

### S8 — ILIAS-Lernszenarien vertiefen
- Lernpfade/Lernziele für das NIR-Labor als ILIAS-Kurse; Synchronisation mit Django-Plattform.

### S9 — Federated Learning ausbauen
- Flower-Clients für verteilte Spektrometer-Setups; Datenschutzprüfung
  (nur Modellaktualisierungen, keine Rohdaten) und non-IID-Strategie.

---

## 4. Abgleichs-Regel (bindend)

Vor jedem Entwicklungsschritt gilt:

1. `AGENT_FRAMEWORK_INIT_PROMPT.md` → `MISSION_STATEMENT.md` → Startsequenz-Dateien lesen.
2. Prüfen: Ist der geplante Schritt in dieser Roadmap enthalten? Wenn nicht: zuerst
   Head-of-Development-Freigabe und Roadmap-Update, dann Umsetzung.
3. Nach Abschluss eines Schritts: die zugehörige Lücken-Nummer (G1–G8) und
   den Roadmap-Schritt (S1–S9) in dieser Datei als erledigt markieren (inkl. Datum und Verweis
   auf Commit/PR).
