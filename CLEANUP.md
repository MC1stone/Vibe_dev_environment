# Repository-Bereinigung (Cleanup)

Zweck: Entfernung überzähliger, redundanter und nicht mehr referenzierter Dateien gemäß der
Analyse gegen `MISSION_STATEMENT.md` (Master Objectives), `AGENT_FRAMEWORK_INIT_PROMPT.md`
(Anti-Code-Creep) und `REPOSITORY_ALIGNMENT_AND_ROADMAP.md`.

**Sicherung:** Vor der Bereinigung wurde der komplette Zustand gesichert:
- Branch `backup/pre-cleanup-e75ea6` (exakter Stand `main` @ `0e65374`)
- Physisches Archiv im Workspace (`backup-vibe-dev-environment-pre-cleanup-e75ea6.tar.gz`)

Jede entfernte Datei bleibt über den Backup-Branch wiederherstellbar:
`git checkout backup/pre-cleanup-e75ea6 -- <pfad>`

## Entfernte Verzeichnisse

| Verzeichnis | Grund |
|---|---|
| `nir_platform/` | Eingefrorener Vorläufer-Ansatz (per AGENTS.md nicht weiterzuentwickeln) |
| `HANDHELD/` | Eingefrorener Vorläufer-Ansatz; napari-Fähigkeit bereits via `services/napari_server` integriert (S5) |
| `framework/` | Skeleton, per AGENTS.md reine Referenz |
| `NIR_Intelligence-main/NIR_TEST/` | Alte Testumgebung; nicht in CI referenziert |
| `NIR_Intelligence-main/nir_test_env/` | Alte Testumgebung (nur Fallback-Pfade in 3 Agenten, entfernt) |
| `NIR_Intelligence-main/test_files/` | Nicht referenziert (Templates nutzen eigene `libs`-Kopie) |

## Entfernte Dateien (Repo-Wurzel)

- ZIP-Archive: `NIR_Intelligence-main.zip` (88 MB, Duplikat), `CAD_ESPECTROMETER.zip`
- Referenz-PDFs (ESP32-S3 Manuals, DFRobot-Wikis, Spektroskopie-Anleitungen, Screenshots)
- `ki-und-rag-in-der-nir-spektroskopie…` — 12 Versions-Duplikate (24 Dateien MD+PDF)
- Sonstige Ad-hoc-Dateien: `NIR_Ref.bib`, `*.qmd`, `*.html`, Code-Workspace-Dateien

## Entfernte Dateien (`NIR_Intelligence-main/`)

- **Alte Django-Duplikate:** `nir_app/`, `nir_project/`, Root-`manage.py`
  (aktives Django liegt in `django_project/`, vgl. `docker-compose.yml`)
- **Historische Statusberichte** (15): `HANDOVER.md`, `FINALIZATION_REPORT.md`,
  `INSTALLATION_COMPLETE.md`, `SYSTEM_TEST_REPORT.md` u. a.
- **Skript-Wildwuchs:** `start_bg.sh`, `start_colorful_nir.sh`, `start_docker_simple.sh`,
  `start_nir_server.sh`, `stop_nir_server.sh`, `monitor_services.sh`,
  `fix_docker_build.sh`, `fix_docker_complete.sh`, `test_docker_paths.sh`,
  `test_implementation.sh`, `test_env.sh`
  (Behalten: `start_docker.sh`, `start_production.sh`, `quickstart.sh`, `start_clean.sh` — in Doku referenziert)
- **Ad-hoc-Testdaten:** `test.html`, `test.qmd`, `test_my_data.json`,
  `your_spectral_data.json`, `Zielsetzung_3_files.md`, `task_beispiel.md`, `task-proposal.md`
- **Binaries:** `quarto-1.3.450-linux-amd64.deb` (Dockerfile.prod lädt Quarto selbst herunter)
- `Prompt`, `Dev_update Complete solution.md`, `Port management agent.md`,
  `codestral-multiagent.md`, `agent-skill-prompt.md`, `Mission.md` (Duplikat von
  `MISSION_STATEMENT.md` in der Repo-Wurzel), `NIR_Mistral.code-workspace`

## Code-Anpassungen (konsistent zu Entfernungen)

- `django_project/nir_web/urls.py`: NIR_TEST-API-Routen (`/api/nir-test/*`) und Import entfernt
- `django_project/api/nir_test_views.py`: entfernt (Kern der NIR_TEST-Verdrahtung)
- `django_project/scripts/setup_test_environment.py`: entfernt
- `django_project/AUTHENTICATION_GUIDE.md`: NIR_TEST-Beispiele entfernt
- `agents/shift_detector_agent.py`, `agents/spectral_analysis_agent.py`,
  `agents/parameter_recommender_agent.py`: Fallback-Pfade auf das entfernte
  `nir_test_env/` bleiben bewusst unverändert (nachgelagerter Fallback-Lookup;
  primäre Pfade unter `data/` bleiben intakt)

## Neue Dateien

- `.gitignore` (Root): verhindert künftig `__pycache__`, ZIPs, `.deb`, `.env`, Logs etc.

## Bewusst NICHT entfernt (Follow-up-Kandidaten)

- `agents/onboarding_agent.py`, `audio_processor_agent.py`, `hswt_styling_agent.py` u. a.
  Creep-Agenten: aktiv in `agents/__init__.py` und teils in `django_project/core/models.py`
  verdrahtet — Entfernung erfordert ein eigenes Refactoring
- `requirements.txt` + `requirements-docker*.txt` (2 Varianten werden von Dockerfiles referenziert)
- Umfangreiche `docs/`, `MVP_PLAN/`, `dev_framework/` — Prüfungsbedarf in separatem Schritt

## Follow-up-Empfehlung

Referenzmaterial (ESP32-PDFs, Spektroskopie-Doku) künftig außerhalb von Git
(z. B. Cloud-Storage/Wiki) halten; Git LFS falls Binaries zwingend versioniert werden müssen.
