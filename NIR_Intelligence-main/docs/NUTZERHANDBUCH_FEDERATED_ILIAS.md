# NIR Intelligence Platform — Nutzerhandbuch: Federated Learning & ILIAS

Dieses Handbuch beschreibt alle erforderlichen Schritte, Optionen und Settings
für den Betrieb der NIR Intelligence Platform mit Fokus auf:

1. **Flower Server (Superlink) & Flower Client (Supernode)** — föderiertes Training
2. **ILIAS-Container** inklusive OAuth2/REST-API-Aktivierung
3. **ILIAS Course Agent** — kontinuierliche Kursentwicklung im eigenen Container
4. **Föderierte Django-UI & Consent-API**

Gültig ab FL6 (Branch `vibe/fl-deployment-ilias-agent-53a9e6`). Alle Services
laufen vollständig lokal im Docker-Compose-Stack (`nir_network`).

---

## 1. Voraussetzungen

- Docker + Docker Compose auf dem Zielrechner (für superlink/supernode- und
  ILIAS-Betrieb zwingend erforderlich — die Sandbox/CI kann nur offline
  verifizieren)
- `.env` im Projektverzeichnis `NIR_Intelligence-main/` (Vorlage:
  `.env.example`)
- Für echten ILIAS-Sync: OAuth2-Client in ILIAS angelegt (siehe Abschnitt 5)

---

## 2. Environment-Settings (`.env`)

### 2.1 Allgemeine Plattform

| Variable | Default | Bedeutung |
|---|---|---|
| `DEBUG` | `0` | Django-Debug-Modus |
| `SECRET_KEY` | — | Django-Secret (Produktion: neu generieren!) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Erlaubte Hosts |
| `DATABASE_URL` | — | PostgreSQL-URL (`postgres://nir_user:…@postgresql:5432/…`) |
| `POSTGRES_PASSWORD` | `nir_password_change_me` | DB-Passwort (ändern!) |

### 2.2 ILIAS

| Variable | Default | Bedeutung |
|---|---|---|
| `ILIAS_AUTO_SETUP` | `1` | ILIAS-Autokonfiguration beim ersten Start |
| `ILIAS_DB_USER` / `ILIAS_DB_PASSWORD` | `ilias` / `ilias_change_me` | ILIAS-DB-Zugang (ändern!) |
| `ILIAS_DB_NAME` | `ilias_nir` | ILIAS-Datenbank |
| `ILIAS_DB_HOST` | `ilias_db` | MariaDB-Host im Netzwerk |
| `ILIAS_CLIENT_ID` | `nir_ip` | ILIAS-Client-Name |
| `ILIAS_HTTP_PATH` | `http://localhost:8080` | Externe ILIAS-URL |
| `ILIAS_ROOT_USER_LOGIN` / `ILIAS_ROOT_USER_PASSWORD` | `root` / `ilias_root_change_me` | ILIAS-Admin (ändern!) |
| `ILIAS_API_CLIENT_ID` | *(leer)* | **OAuth2-Client-ID für die REST-API (Pflicht für echten Sync)** |
| `ILIAS_API_CLIENT_SECRET` | *(leer)* | **OAuth2-Client-Secret (Pflicht für echten Sync)** |

**Wichtig:** Ohne `ILIAS_API_CLIENT_ID`/`ILIAS_API_CLIENT_SECRET` läuft der
ILIAS Course Agent und alle Syncs im ehrlich degradierten Modus (`degraded` —
kein Fake-Erfolg, keine gestellten Kurse).

### 2.3 Federated Learning (Flower)

**Server (Superlink):**

| Variable | Default | Bedeutung |
|---|---|---|
| `FLOWER_SERVER_HOST` | `0.0.0.0` | Bind-Adresse des Superlink |
| `FLOWER_SUPERLINK_PORT` | `9091` | gRPC-Port ServerAPI (ServerApp) |
| `FLOWER_FLEET_API_PORT` | `9092` | gRPC-Port FleetAPI (Supernodes) |
| `FLOWER_NUM_ROUNDS` | `3` | Anzahl Föderationsrunden |
| `FLOWER_STRATEGY` | `fedavg` | `fedavg` oder `fedprox` |
| `FLOWER_PROXIMAL_MU` | `0.1` | FedProx-Proximal-Term (nur bei `fedprox`) |
| `FLOWER_MODEL_DIM` | `18` | Dimension des Ridge-Parametervektors (S9-Modell) |
| `FLOWER_START_SERVERAPP` | `1` | `0` = nur Superlink starten, keine ServerApp |

**Client (Supernode):**

| Variable | Default | Bedeutung |
|---|---|---|
| `FLOWER_SUPERLINK_ADDRESS` | `flower_server:9092` | Fleet-API-Adresse des Superlink |
| `FLOWER_CLIENT_GROUP` | `sparkfun_triad` | Gruppen-ID des Supernode (Name der Spektrometergruppe) |
| `FLOWER_CLIENT_DATA` | *(leer)* | **Pfad zu einer `.npz`-Datei mit `x` (Spektren) und `y` (Referenzwerte)** |
| `FLOWER_MODEL_DIM` | `18` | Muss zum Server passen |

**Wichtig:** Ohne `FLOWER_CLIENT_DATA` startet der Supernode mit einem
**synthetischen Platzhalter-Datensatz** und gibt eine Warnung aus — ehrlich,
aber für echtes Training müssen echte Daten vorliegen (Abschnitt 4.2).

---

## 3. Start & Stopp des Stacks

```bash
cd NIR_Intelligence-main

# .env anlegen (einmalig)
cp .env.example .env
# Werte anpassen: Passwörter, ILIAS_API_CLIENT_ID/SECRET, ggf. FLOWER_*

# Kompletter Stack starten (Django, Flower, ILIAS, Course Agent, …)
docker compose up -d

# Nur Federated Learning
docker compose up -d flower_server flower_client

# Nur ILIAS + Course Agent
docker compose up -d ilias ilias_db ilias_course_agent

# Produktion (mit nginx)
docker compose -f docker-compose.prod.yml up -d

# Logs
docker compose logs -f flower_server
docker compose logs -f flower_client
docker compose logs -f ilias_course_agent

# Stopp
docker compose down
```

Erster Start: Der `flower_server` und `flower_client` installieren flwr im
Container-Command (`pip install 'flwr>=1.4.0' numpy`) — der erste Start dauert
deshalb einige Minuten länger.

---

## 4. Flower Server (Superlink) & Client (Supernode)

### 4.1 Architektur

```
flower_client (Supernode, Gruppe z.B. sparkfun_triad)
        │  nur Modell-Parameter-Updates (Privacy-Vertrag!)
        ▼
flower_server (Superlink, Fleet-API :9092, ServerAPI :9091)
        │  startet nach dem Superlink die ServerApp aus services/flower_apps.py
        ▼
FedAvg/FedProx-Aggregation über die Runden (FLOWER_NUM_ROUNDS)
```

Der Supernode nutzt den FL1-`NirFlwrClient`: das lokale Training ist das
S9-Ridge-Update (`FederatedLearningService.client_update`). **Nur
Parameter-Updates verlassen den Client — niemals Rohspektren** (erzwungen im
Code, verifiziert durch die Testmatrizen FL1/FL3/OP25).

### 4.2 Echte Trainingsdaten bereitstellen

1. Spektren als `.npz` mit den Arrays `x` (Form: n_samples × n_wavelengthen,
   Dimension = `FLOWER_MODEL_DIM`) und `y` (n_samples Referenzwerte):

   ```python
   import numpy as np
   np.savez("client_sparkfun.npz", x=spektren, y=referenzwerte)
   ```

2. Datei dem `flower_client` mounten und setzen (docker-compose.yml):

   ```yaml
   flower_client:
     volumes:
       - ./data/client_sparkfun.npz:/app/data/client.npz:ro
     environment:
       - FLOWER_CLIENT_DATA=/app/data/client.npz
   ```

3. `docker compose up -d --force-recreate flower_client`

Fehlt die Datei, erscheint beim Start die Warnung
`using synthetic placeholder data` — Betrieb läuft dann nur als
Verbindungstest, nicht mit echtem Modell.

### 4.3 Mehrere Gruppen (weitere Supernodes)

Pro Spektrometergruppe ein Service-Klon in der `docker-compose.yml`:

```yaml
  flower_client_lab2:
    image: python:3.12-slim
    command: sh -c "pip install --no-cache-dir 'flwr>=1.4.0' numpy > /dev/null 2>&1; python scripts/flower_supernode_entry.py"
    volumes:
      - ./services:/app/services
      - ./agents:/app/agents
      - ./scripts:/app/scripts
      - ./data/client_lab2.npz:/app/data/client.npz:ro
    working_dir: /app
    environment:
      - FLOWER_SUPERLINK_ADDRESS=flower_server:9092
      - FLOWER_CLIENT_GROUP=lab2_instrument
      - FLOWER_CLIENT_DATA=/app/data/client.npz
    depends_on:
      - flower_server
    networks:
      - nir_network
```

### 4.4 Deployment-Livetest (Zielumgebung)

```bash
docker compose up -d flower_server flower_client
docker compose logs flower_server   # Superlink gestartet + ServerApp-Runden
docker compose logs flower_client   # Supernode verbindet sich, fit/evaluate-Runden
```

Erwartete Ausgaben: ServerApp berichtet pro Runde Aggregations-Status und
Verluste; der Supernode meldet `fit`-Teilnahme mit Samples. Schlägt die
Verbindung fehl, wiederholt der Supernode die Verbindung zum Superlink.

### 4.5 Strategie umschalten (FedAvg → FedProx)

```yaml
  flower_server:
    environment:
      - FLOWER_STRATEGY=fedprox
      - FLOWER_PROXIMAL_MU=0.1
      - FLOWER_NUM_ROUNDS=5
```

FedProx stabilisiert non-IID-Verteilungen zwischen den Spektrometergruppen
über den Proximal-Term `mu`.

---

## 5. ILIAS-Handling

### 5.1 ILIAS-Container

- Image: `srsolutions/ilias:9-php8.2-apache`, Port **8080 → 80**
- Eigene MariaDB `ilias_db` (ILIAS benötigt MySQL/MariaDB)
- Volumes: `ilias_data` (Webroot), `ilias_extradata` (ILIAS-Daten)
- Erster Start mit `ILIAS_AUTO_SETUP=1` konfiguriert ILIAS automatisch;
  anschließend Login unter `http://localhost:8080` mit
  `ILIAS_ROOT_USER_LOGIN`/`ILIAS_ROOT_USER_PASSWORD`

### 5.2 OAuth2/REST-API für die Plattform aktivieren (Pflicht für Sync)

1. Als Root in ILIAS einloggen → **Administration → REST API** (bzw. das
   OAuth2-Plugin des Images) 
2. Neuen OAuth2-Client anlegen (Redirect auf die Django-App erlaubt)
3. Client-ID und Client-Secret in `.env` eintragen:

   ```env
   ILIAS_API_CLIENT_ID=<client-id>
   ILIAS_API_CLIENT_SECRET=<client-secret>
   ```

4. `docker compose up -d --force-recreate ilias_course_agent django_app`

Danach liefern `GET /api/ilias/status/` und der Course Agent echte
Verbindungsdaten statt `degraded`.

### 5.3 ILIAS-Sync über die Django-UI

- **UI:** `http://localhost:8000/ilias/` — Lernpfad-Sync-Formular
  (`POST /api/ilias/learning-paths/sync/`), Status-Panel
  (`GET /api/ilias/status/`)
- **Kurs-Wiederverwendung:** Plattform und Course Agent suchen Kurse zuerst per
  OP2-Titel-Lookup — es werden keine Duplikate angelegt
- **Föderierte Runden-Sync (FL5):** Runden-Status (Runde, Gruppen,
  aggregierte Qualitätsmetriken — **nur Metadaten, nie Parameter oder
  Rohspektren**) landen im Session-Kurs-Kontext

---

## 6. ILIAS Course Agent (eigener Container)

### 6.1 Was der Agent tut

Der `ilias_course_agent`-Container läuft mit
`scripts/ilias_course_agent_runner.py` und dem `IliasCourseAgent`
(`agents/ilias_course_agent.py`):

- **Entwickelt** kontinuierlich NIR-Curricula aus echten Plattform-Fähigkeiten:
  Datenimport, Metadaten, Sensorik, Chemometrie, Föderiertes Lernen — jedes
  Curriculum mit Lernzielen inkl. Bloom-Leveln
- **Synct** jeden Lehrplan als ILIAS-Lernpfad über die S8-Schnittstelle
  (`ILIASLearningService.sync_learning_path`), mit Kurs-Wiederverwendung per
  OP2-Lookup
- **Degradiert ehrlich**: Ist ILIAS (noch) nicht erreichbar oder OAuth2 nicht
  konfiguriert, läuft die Runde mit Status `degraded` weiter — kein Absturz,
  kein Fake-Erfolg

### 6.2 Runner-Optionen

| Option | Default | Bedeutung |
|---|---|---|
| `--interval` | `300` | Sekunden zwischen den Runden (Standard alle 5 Minuten) |
| `--once` | — | Nur eine Runde ausführen und beenden (z. B. für Tests) |
| `--ilias-url` | `http://ilias:80` | ILIAS-Basis-URL (im Container-Netzwerk) |
| `--client-id` / `--client-secret` | *(leer)* | OAuth2-Credentials (überschreiben die Env) |
| `--state-file` | `output/ilias_course_agent_state.json` | Persistenter Runden-State |

State-Datei einsehen:

```bash
docker compose exec ilias_course_agent cat output/ilias_course_agent_state.json
```

### 6.3 Kommandozeilen-Operationen (Ad-hoc)

```bash
# Status des Kurs-Katalogs abfragen
docker compose exec ilias_course_agent \
  python -c "from agents.ilias_course_agent import IliasCourseAgent; \
  import json; print(json.dumps(IliasCourseAgent().execute('status'), indent=2))"

# Eine Runde sofort erzwingen
docker compose exec ilias_course_agent \
  python scripts/ilias_course_agent_runner.py --once

# Intervall ändern (z. B. stündlich) — compose environment ergänzen:
#   command: python scripts/ilias_course_agent_runner.py --interval 3600
```

### 6.4 Kurs-Katalog (Fähigkeiten)

| Curriculum | Thema | Beispiel-Lernziele (Bloom) |
|---|---|---|
| `datenimport` | Formatunabhängiger Import (CSV, SPC, JMP, …) | Importpfade anwenden (Anwenden) |
| `metadaten` | Provenanz-Dimensionen, Metadaten-Qualität | Metadaten-Qualität bewerten (Bewerten) |
| `sensorik` | Spektrometer-Adapter, Sensor-Kalibration | Adapter-Schicht analysieren (Analysieren) |
| `chemometrie` | PLS/Ridge-Kalibration, Modellgüte | Kalibrationen vergleichen (Bewerten) |
| `federated` | Föderiertes Lernen, DP & SecAgg, Consent | Föderationsrunden gestalten (Erschaffen) |

Der Katalog erfindet keine Fähigkeiten, die die Plattform nicht hat
(Curriculum-Sequenz ist im Agenten kodiert).

---

## 7. Föderierte Django-UI & Consent-Workflow

- **UI:** `http://localhost:8000/federated/` (Nav: „Föderiert“)
- **Consent ist Pflicht:** ohne explizites Opt-in bleibt alles `local_only`
  (Default gemäß WORKFLOW_INTEGRATION.md). Consent erteilen/widerrufen über
  `POST /api/federated/consent/`

| Endpunkt | Methode | Funktion |
|---|---|---|
| `/api/federated/consent/` | POST | Opt-in erteilen/widerrufen |
| `/api/federated/status/` | GET | Session-, Runtime- und SecAgg-Status |
| `/api/federated/rounds/` | POST | Föderierte Kalibrationsrunde (FL2) — 403 ohne Consent, 503 bei sklearn-Deferral |
| `/api/federated/privacy/` | GET | DP-Accountant (ε/δ-Budget), SecAgg-Status, Privacy-Vertrag |

**Privacy-Level-Regeln:**
- `LOCAL_ONLY` (Default): keine Updates verlassen die Plattform
- `PARAMETERS_ONLY`: nur Clipping+DP-gefilterte Parameter-Updates
- Rohspektren verlassen die Plattform **niemals** — Payloads mit
  `params`/`spectra`/Rohdaten werden auf Code-Ebene verworfen (OP25
  PrivacyAuditor + FL5/FL6-Verträge)

---

## 8. Fehlerbehebung (Troubleshooting)

| Symptom | Ursache | Lösung |
|---|---|---|
| Supernode-Logs: `Failed to resolve 'flower_server'` | Client vor Server gestartet | `docker compose up -d flower_server` zuerst; `restart` holt den Client nach |
| `using synthetic placeholder data` | `FLOWER_CLIENT_DATA` nicht gesetzt / Datei fehlt | `.npz` mounten + Env setzen (Abschnitt 4.2) |
| ServerApp startet nicht, Superlink läuft | `FLOWER_START_SERVERAPP=0` gesetzt | Env entfernen oder auf `1` setzen |
| `flower_client` verbindet sich nicht | Fleet-API-Port falsch | `FLOWER_SUPERLINK_ADDRESS=flower_server:9092` (Fleet-API, nicht ServerAPI 9091) |
| Course Agent: `ILIAS token endpoint unreachable` | ILIAS-Container nicht ready oder OAuth2 fehlt | `docker compose logs ilias` prüfen; OAuth2-Credentials setzen (Abschnitt 5.2) |
| Course Agent-State zeigt `degraded` | Absicht (ehrliches Reporting) | Ursache in `status.details` nachlesen — kein Fehler im Agent |
| ILIAS-Setup-Seite trotz `ILIAS_AUTO_SETUP=1` | Volume `ilias_data` von altem Versuch | `docker compose down -v` (Achtung: löscht ILIAS-Daten) und neu starten |
| Runde endet ohne Clients | kein Supernode in der Gruppe | `flower_client`-Logs prüfen; Gruppe via `FLOWER_CLIENT_GROUP` gesetzt? |
| Runden laufen, RMSE verbessert sich nicht | FedAvg auf stark non-IID-Shards | `FLOWER_STRATEGY=fedprox` + `FLOWER_PROXIMAL_MU` erhöhen |

---

## 9. Verifikation & Tests

Offline (ohne Container, CI-tauglich):

```bash
python tests/test_fl1_flwr_runtime.py            # 21 Checks (S9-Semantik, Privacy)
python tests/test_fl2_federated_calibration.py   # 20 Checks (föd. PLS)
python tests/test_fl3_federated_privacy.py       # 25 Checks (DP + SecAgg)
python tests/test_fl4_federated_ui.py            # 20 Checks (Consent-API)
python tests/test_fl5_federated_ilias.py         # 16 Checks (ILIAS-Kopplung)
python tests/test_fl6_deployment_ilias_agent.py   # 35 Checks (Deployment + Course Agent)
```

Live (Zielumgebung, Container-Runtime): Abschnitt 4.4 (superlink/supernode)
und 5.2 (echter ILIAS-Kurs-Sync).

---

## 10. Checkliste für den ersten Betrieb

1. [ ] `.env` angelegt, Passwörter geändert
2. [ ] `docker compose up -d` — Stack läuft
3. [ ] Django-UI erreichbar: `http://localhost:8000/`
4. [ ] ILIAS erreichbar: `http://localhost:8080/`, Root-Login geändert
5. [ ] OAuth2-Client in ILIAS angelegt, `ILIAS_API_CLIENT_ID/SECRET` gesetzt
6. [ ] `docker compose up -d --force-recreate ilias_course_agent` — State zeigt `success` statt `degraded`
7. [ ] `FLOWER_CLIENT_DATA` mit echten `.npz`-Daten gesetzt
8. [ ] `docker compose logs flower_server flower_client` — Föderationsrunden laufen
9. [ ] Consent in `/federated/` erteilt, Runde erfolgreich
10. [ ] Kurse erscheinen in ILIAS (Wiederverwendung: kein Duplikat)
