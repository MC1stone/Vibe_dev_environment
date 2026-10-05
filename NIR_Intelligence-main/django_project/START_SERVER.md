# NIR Intelligence Platform - Quick Start (OP51)

## EIN Weg: der Docker-Stack

Die Plattform laeuft ausschliesslich als Docker-Stack. Parallele Host-Django-
Server (zweite Instanz auf anderem Port) sind mit OP51 entfallen - sie waren
die Ursache von Doppel-Instanzen (z. B. Auswertung auf 8001, Upload auf 8000).

### Start

```bash
cd NIR_Intelligence-main
docker compose up -d
# oder ueber das Delegations-Skript:
./django_project/start.sh
```

### Erreichbarkeit

| Dienst | URL |
|---|---|
| Web-UI / Upload | http://localhost:8000/ |
| Admin | http://localhost:8000/admin/ |
| Health | http://localhost:8000/health/ |
| Chatbot-Seite | http://localhost:8000/chatbot/ |
| ILIAS | http://localhost:8080/ (Erststart: Setup dauert einige Minuten) |
| Ollama API | http://localhost:11434/ |

### Erster Start (einmalig)

```bash
docker compose up -d --build
# ollama_init zieht automatisch mistral + nomic-embed-text (mehrere GB)
docker compose logs -f ollama_init
```

### Status / Stop

```bash
./django_project/check_server.sh     # docker compose ps + Health-Hinweis
./django_project/stop_server.sh      # docker compose down
```

### Historie (OP51)

- `start.sh` startete Django direkt auf dem Host (inkl. `kill -9` aller
  manage.py-Prozesse und optionalem Zweit-Port) - jetzt Docker-Delegation.
- `start_server.sh`, `start_clean.sh`, `dev_server.sh` (hartkodierter
  Privatpfad), `start_server_venv.sh`: entfernt.
- `stop_server.sh` / `check_server.sh`: Docker-Delegation.
