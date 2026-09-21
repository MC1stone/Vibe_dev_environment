# Lokale Setup- und Test-Anleitung (NIR Intelligence Platform)

Diese Anleitung beschreibt, wie du die NIR-IP nach dem Stand S1–S9 auf deinem
Rechner aktualisierst, startest und lokal testest. Alle Befehle sind gegen die
echten Compose-Services, Ports und Env-Dateien im Repo verifiziert.

---

## 1. Voraussetzungen

| Komponente | Anforderung |
|---|---|
| Git | beliebig, aktueller Stand von `main` |
| Docker Engine | 24+ mit Compose v2 (`docker compose`, nicht `docker-compose`) |
| RAM | ≥ 16 GB empfohlen (Ollama + Mistral + Qdrant + ILIAS parallel) |
| Disk | ~30–50 GB frei (Images + Volumes + Mistral-Modell ~4–8 GB) |
| Ports frei | 8000, 8080, 8081, 8082, 8002, 6333, 6334, 5432, 5555, 5556, 11434, 6379 |

Port-Konflikte prüfen (Linux/macOS):

```bash
ss -tlnp | grep -E ':(8000|8080|8081|8082|8002|6333|6334|5432|5555|5556|11434|6379)'
```

> **Hinweis Windows:** Der Stack läuft nativ unter WSL2 (Docker Desktop mit
> WSL2-Backend). ILIAS und napari sind Linux-Container; PowerShell-Befehle
> funktionieren, empfohlen ist aber die WSL2-Shell.

---

## 2. Repository aktualisieren

```bash
cd <dein-repo-pfad>          # z. B. ~/Development/Vibe_dev_environment
git checkout main
git pull origin main
git log --oneline -3          # Erwartung: Merge PR #10 (S9) an der Spitze
```

Falls du lokal ältere Experimente in `NIR_Intelligence-main/` hattest:
vorher committen oder stashen — der Stack mountet das Verzeichnis als Volume
(`- .:/app`), lokale Änderungen wirken sich direkt auf den Container aus.

---

## 3. Python-Umgebung für die Testmatrizen (optional, empfohlen)

Die Testmatrizen S3–S9 laufen ohne Docker direkt auf dem Host:

```bash
cd NIR_Intelligence-main
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Alle Tests laufen bewusst ohne Netzwerk und ohne laufende Container
(optional fehlende Pakete wie `faiss`, `flwr`, `optuna` werden graceful
übersprungen; ein voller lokaler Test deiner Zielumgebung installiert sie
zusätzlich: `pip install faiss-cpu flwr optuna qdrant-client`).

Testmatrizen ausführen:

```bash
python tests/test_s3_format_loaders.py            # 7/7
python tests/test_s4_spectrometer_adapters.py     # 26/26
python tests/test_s5_spectrum_similarity.py        # 16/16
python tests/test_s6_chatbot.py                   # 17/17
python tests/test_s7_update_monitoring.py          # 27/27
python tests/test_s8_ilias_integration.py          # 26/26
python tests/test_s9_federated_learning.py        # 28/28
```

Erwartung: jede Matrix endet mit `N/N tests passed`, Exit-Code 0.

---

## 4. Docker-Stack starten (dev)

### 4.1 Env-Datei prüfen

Der Stack nutzt `NIR_Intelligence-main/.env.docker`. Prüfe vor dem ersten
Start und passe deine lokalen Werte an (v. a. Passwörter — siehe Abschnitt
Sicherheit):

```bash
cd NIR_Intelligence-main
cat .env.docker
```

Wichtige Variablen (Auswahl):

| Variable | Default im Repo | Bedeutung |
|---|---|---|
| `DJANGO_SECRET_KEY` | `your-production-secret-key-change-me` | **unbedingt ändern** |
| `DJANGO_DEBUG` | `False` | lokal auf `True` setzen |
| `POSTGRES_PASSWORD` / `DJANGO_DB_PASSWORD` | `nir_password_2026` | **ändern** |
| `QDRANT_URL` | `http://qdrant:6333` | Container-Service-Name, nicht ändern |
| `OLLAMA_URL` | `http://ollama:11434` | Container-Service-Name, nicht ändern |
| `FLOWER_SERVER_HOST/PORT` | `0.0.0.0` / `5555` | Flower-Transport |

Für ILIAS gelten zusätzlich (Defaults aus der Compose-Datei, überschreibbar):

```bash
ILIAS_DB_PASSWORD=ilias_change_me        # ändern
ILIAS_MYSQL_ROOT_PASSWORD=ilias_root_change_me   # ändern
```

Empfohlen: `.env.docker` nicht committen (liegt bereits im Repo — trage deine
geänderten Werte dort ein oder überschreibe sie per Shell/`.env.local`).

### 4.2 Stack bauen und starten

```bash
docker compose build
docker compose up -d
docker compose ps
```

Das Build umfasst zwei lokale Images: `django_app` (Dockerfile.django) und
`napari_server` (services/napari_server). Die restlichen Services ziehen
gepinnte bzw. `latest`-Images von Docker Hub (erster Start: Downloads
~5–10 Min.).

### 4.3 Mistral-Modell ziehen (einmalig)

```bash
docker compose exec ollama ollama pull mistral:latest
```

Das lädt ~4–8 GB in das Volume `ollama_data` (einmalig, bleibt über Neustarts hinweg erhalten).

### 4.4 Datenbank initialisieren

`django_app` führt `migrate` automatisch beim Start aus. Falls du später
SQL-Initialisierung (z. B. `scripts/init-db.sql`) manuell einspielen willst:

```bash
docker compose exec postgresql psql -U nir_user -d nir_mistral -f /dev/stdin < scripts/init-db.sql
```

---

## 5. Health-Checks: Ist alles wirklich hoch?

| Service | Check | Erwartung |
|---|---|---|
| Django | `curl -s http://localhost:8000/ -o /dev/null -w "%{http_code}"` | `200` oder `302` |
| Qdrant | `curl -s http://localhost:6333/healthz` | `"ok"` |
| Ollama | `curl -s http://localhost:11434/api/tags` | JSON mit `mistral:latest` |
| FAISS | `curl -s http://localhost:8081/healthz -o /dev/null -w "%{http_code}"` | `200` |
| napari | `curl -s http://localhost:8002/healthz -o /dev/null -w "%{http_code}"` | `200` (oder `/docs`) |
| MCP | `curl -s http://localhost:8082/ -o /dev/null -w "%{http_code}"` | `200` |
| Flower | `nc -z localhost 5555 && echo up` | `up` |
| PostgreSQL | `docker compose exec postgresql pg_isready -U nir_user -d nir_mistral` | `accepting connections` |
| ILIAS | `curl -s http://localhost:8080/ -o /dev/null -w "%{http_code}"` | `200`/`302` (Erststart: Setup, einige Min. Geduld) |
| ILIAS-DB | `docker compose exec ilias_db mysqladmin status -uilias -p"$ILIAS_DB_PASSWORD"` | `Uptime: ...` |

Schnellübersicht aller Services:

```bash
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
```

---

## 6. Erste lokale Analyse durchführen

1. Django-UI öffnen: <http://localhost:8000>
2. Testdaten (falls gewünscht): die Labordaten liegen unter
   `NIR_Intelligence-main/data/raw/` (z. B. `T4-T5_ALLE_mit_Brix_2.txt`,
   SparkFun-Triad-Format 18 Kanäle A_410–L_940).
3. Import läuft über den format-agnostischen Loader (S3): CSV/TXT/JSON/SPC/MAT
   werden automatisch erkannt; Geräteadapter (S4) parsen MQTT-/Qwiic-Payloads
   im einheitlichen Spektral-Schema.
4. Chatbot (S6): `POST http://localhost:8000/api/chatbot/` mit
   `{"message": "Welche Analyseergebnisse liegen vor?"}` — nutzt Ollama/Mistral
   (Container muss das Modell aus 4.3 geladen haben, sonst `degraded`).
5. ILIAS (S8): <http://localhost:8080> — erstmaliges Setup gemäß
   Container-Konsole; danach Lernpfad-Sync über
   `POST http://localhost:8000/api/ilias/` (LearningPath-Payload).
6. Similarity (S5): napari-Server auf Port 8002; API-Doku (falls FastAPI):
   <http://localhost:8002/docs>.

---

## 7. Update-Check (S7) lokal ausführen

```bash
cd NIR_Intelligence-main
python scripts/check_updates.py                 # Quarto-Report (.qmd) + Konsole
python scripts/check_updates.py --json         # maschinenlesbar
```

Der Monitor scannt `requirements*.txt` + Compose-Images gegen lokal
installierte Versionen (kein Netz nötig). Für Online-Lookups gegen PyPI/Docker
Hub ist Netz erforderlich — das ist einer der dokumentierten Zielumgebungs-
Offenpunkte.

---

## 8. Produktions-Profil (optional, lokal gegenchecken)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Das prod-Profil ergänzt celery worker/beat, nginx, prometheus, grafana,
quarto. Für lokale Experimente reicht das dev-Profil (Abschnitt 4).

---

## 9. Herunterfahren & Reset

```bash
docker compose down                # Container stoppen, Volumes bleiben
docker compose down -v             # ACHTUNG: löscht auch alle Daten/Volumes
docker compose build --no-cache    # kompletter Rebuild bei Verdacht auf Cache-Probleme
```

Mistral-Modell bleibt bei `down` erhalten (Volume `ollama_data`); erst
`down -v` entfernt es.

---

## 10. Fehler-Behebung (die häufigsten Fälle)

| Symptom | Ursache/Lösung |
|---|---|
| `django_app` startet nicht / DB-Fehler | `postgresql` noch nicht bereit → `docker compose logs django_app`, Container startet migrate automatisch neu; ggf. `docker compose restart django_app` |
| Chatbot antwortet `degraded` / 503 | Mistral-Modell fehlt → Abschnitt 4.3 (`ollama pull mistral:latest`); prüfen: `curl localhost:11434/api/tags` |
| ILIAS zeigt 500/leere Seite | Erststart braucht mehrere Minuten (`ILIAS_AUTO_SETUP=1`); Logs: `docker compose logs -f ilias`; DB-Check wie Abschnitt 5 |
| Port schon belegt | Abschnitt 1 (`ss -tlnp`) — alten Stack down fahren oder Port-Mapping in `docker-compose.yml` ändern |
| Qdrant Healthcheck schlägt fehl | `docker compose logs qdrant`; Volumen-Konflikt nach Versionwechsel → `docker volume ls`, ggf. altes `qdrant_data` entfernen |
| napari/FAISS-Container exit sofort | `docker compose logs napari_server faiss`; Build-Kontext prüfen (Abschnitt 4.2) |
| Tests S3–S9 schlagen fehl | In der venv des Hosts laufen (Abschnitt 3), nicht im Container; Fehlende Optional-Pakete nachinstallieren |

---

## 11. Sicherheitshinweise (lokal)

- **Passwörter/Secrets vor jedem echten Einsatz rotieren:**
  `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`/`DJANGO_DB_PASSWORD`,
  `ILIAS_DB_PASSWORD`, `ILIAS_MYSQL_ROOT_PASSWORD` (die Repo-Defaults sind bekannte Platzhalter -
  dokumentierter Zielumgebungs-Offenpunkt, siehe S8).
- Stack nur lokal betreiben; keine Ports ins Internet exponieren (default:
  alle Bindings sind Host-Bindings auf `localhost` der Docker-Maschine).
- `.env.docker` mit persönlichen Passwörtern nicht committen.

---

## 12. Was lokal getestet ist — und was nicht

**In der Sandbox verifiziert (S1–S9):** Alle Testmatrizen (7+26+16+17+27+26+28
= 157 Tests), YAML/JSON-Validierung der Compose-Dateien, py_compile aller
neuen Module. Die Module nutzen bewusst injizierbare Transports/Stubs — kein
Netzwerk nötig.

**Erst lokal auf deinem Rechner testbar:** Echter Container-Betrieb mit
laufendem Ollama (Mistral-Inferenz), Qdrant-Embedding-Pipeline (S5/S6-Offen-
punkt), ILIAS-Erstsetup gegen `ilias_db`, echter Flower-Client-Server-Betrieb
(S9-Offenpunkt), Docker-Builds von `django_app` und `napari_server`.

Diese Offenpunkte sind in der Roadmap (`REPOSITORY_ALIGNMENT_AND_ROADMAP.md`,
Abschnitte S5–S9 „Offen für die Zielumgebung") dokumentiert — genau das ist der
nächste Entwicklungsschritt, sobald dein lokaler Stack grün ist.
