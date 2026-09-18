# NIR Intelligence Platform — Installation Guide

This guide installs the **NIR Intelligence Platform (NIR-IP)** as a fully
local, self-contained setup. Federated Learning (Flower) and the Ilias
learning platform are **out of scope** for this version.

## 1. Prerequisites

| Component        | Version          | Notes                                                |
|-----------------|------------------|------------------------------------------------------|
| Python          | 3.13 (3.10+ ok)  | Use a virtual environment (`uv` or `venv`)           |
| Docker + Compose| any recent       | Runs PostgreSQL, Qdrant, Ollama                      |
| Quarto CLI      | ≥ 1.4            | Renders the HTML analysis reports                    |
| Ollama          | latest           | Local LLM backend; pulls `mistral:latest`            |
| Git             | any              | Clone the repo                                       |

> Python 3.13 is the reference version used in development. The code is
> compatible with 3.10+; `requirements.txt` pins a 3.8-compatible floor.

## 2. Clone the repository

```bash
git clone https://github.com/MC1stone/Vibe_dev_environment.git
cd Vibe_dev_environment
```

The Django application lives under `nir_platform/django_app/`. The
specialist agents live under `nir_platform/agents/`.

## 3. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows PowerShell
```

## 4. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r nir_platform/requirements.txt
```

This installs Django, numpy/pandas/scipy/scikit-learn, matplotlib,
`qdrant-client`, `nbformat`+`jupyter` (so Quarto's native render path
works), `crewai`, `ollama`, FastAPI/uvicorn (MCP server), and the test
tooling.

## 5. Start the data infrastructure (Docker)

The platform needs three services running locally. Use the provided
Docker Compose file:

```bash
cd nir_platform/docker
docker compose up -d postgres qdrant ollama
```

This starts:

| Service   | Container      | Port | Purpose                          |
|-----------|----------------|------|----------------------------------|
| PostgreSQL| `nir_postgres` | 5432 | Relational metadata + analyses    |
| Qdrant    | `nir_qdrant`   | 6333 | Spectral fingerprint vector index|
| Ollama    | `nir_ollama`   | 11435| Local LLM (Mistral) backend       |

> The dev server (`dev-run.sh`) starts these automatically. Running them
> manually here lets you control them independently.

Verify they are up:

```bash
docker compose ps
curl -s http://localhost:6333/collections        # Qdrant
curl -s http://localhost:11435/api/tags          # Ollama
```

## 6. Pull the local LLM model

Ollama must have a model available for the agents' AI replies:

```bash
ollama pull mistral:latest
```

The agents read the model name from the env var `NIR_OLLAMA_MODEL`
(default `mistral`). Set it if you use a different model:

```bash
export NIR_OLLAMA_MODEL=mistral
```

## 7. Install the Quarto CLI

Quarto renders the `.qmd` analysis documents to HTML for the in-app
report viewer. Install from <https://quarto.org> or your package manager.

Verify:

```bash
quarto --version
```

The platform pins the Quarto Python kernel to the **venv Python** via the
`QUARTO_PYTHON` env var at render time, so the kernel can import
`nbformat`, `jupyter`, and `matplotlib` from the same environment as the
app. You do not need to set this manually — the reporting agent sets it.

## 8. Configure environment variables

The app reads these (all optional; defaults shown):

```bash
export DJANGO_SETTINGS_MODULE=nir_platform.settings
export DB_HOST=localhost
export DB_PORT=5432
export NIR_OLLAMA_MODEL=mistral
# Optional overrides:
# export OLLAMA_URL=http://localhost:11435
# export QDRANT_URL=http://localhost:6333
```

The Ollama port is **11435** in the dev container, not the library
default 11434. This is configured in `settings.AGENT_CONFIG['ollama_url']`
and passed to the agents at startup.

## 9. Apply database migrations

```bash
cd nir_platform/django_app
python manage.py migrate
```

This creates the `SpectralData`, `Report`, `AnalysisProject`, and other
tables in PostgreSQL.

## 10. Start the development server

The easiest path is the provided script, which starts the Docker
infrastructure, pulls the branch, and launches Django with the correct
host DB config:

```bash
cd nir_platform
./dev-run.sh
```

Options:

```bash
./dev-run.sh --reset            # hard reset to origin/<branch>
./dev-run.sh --branch <branch>  # use a different branch
./dev-run.sh --no-pull          # skip git pull
```

Or run Django directly:

```bash
cd nir_platform/django_app
python manage.py runserver 0.0.0.0:8000
```

> Note: the dev server is **threaded by default**. Do **not** pass a
> `--threading` flag — it is unrecognized and causes a startup error.

## 11. Open the platform

Browse to **http://localhost:8000**.

If port 8000 is busy, the Port Management Agent
(`agents/port_management_agent.py`) automatically selects an alternative
(8001, 8002, 8080, 8888). The console banner prints the chosen URL.

## 12. (Optional) Run the MCP server

The MCP server (`agents/mcp_server.py`) exposes the agent tools over an
HTTP API. It is not required for the web UI but is used by the CrewAI
orchestration layer:

```bash
cd nir_platform
python -m agents.mcp_server
# default port 8000; change via --port
```

## 13. Run the tests

```bash
cd nir_platform/django_app
pytest
```

## Troubleshooting

| Symptom                                   | Cause / Fix                                              |
|-------------------------------------------|---------------------------------------------------------|
| `Ollama unavailable, using local fallback`| Ollama not on 11435, or model not pulled. `docker compose up -d ollama` + `ollama pull mistral` |
| `nbformat: No module named 'nbformat'`    | `pip install -r nir_platform/requirements.txt` (it lists `nbformat`+`jupyter`) |
| Quarto render `rc=1`                       | Ensure Quarto CLI installed and on `$PATH`; the app falls back to an in-process HTML renderer if unavailable |
| `psycopg2 ... module` error                | PostgreSQL container down; `docker compose up -d postgres` |
| Qdrant `PUT /points` flood on `/analysis/`| Already fixed — indexed analyses are skipped on page load |
| `--threading` flag error                   | Do not pass `--threading`; runserver is threaded by default |

## Service ports summary

| Service    | Port  | Configured in                       |
|------------|-------|-------------------------------------|
| Django     | 8000  | `manage.py runserver` / `dev-run.sh` |
| PostgreSQL | 5432  | `settings.DATABASES`                |
| Qdrant     | 6333  | `settings.AGENT_CONFIG['qdrant_url']`|
| Ollama     | 11435 | `settings.AGENT_CONFIG['ollama_url']`|
| MCP server | 8000  | `agents/mcp_server.py`               |
