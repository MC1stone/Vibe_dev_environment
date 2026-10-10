# Paperless-ngx + Mistral (lokal via Ollama) — Home-Server Setup (Linux Mint, LAN-only)

Automatische Dokumentenverwaltung mit **vollständig lokaler** KI-Verschlagwortung:
- **Paperless-ngx** — Dokumentenmanagement (DMS) mit OCR (deutsch)
- **paperless-ai** — verschlagwortet Dokumente automatisch (Titel, Tags, Korrespondent, Datum, Sprache)
- **Ollama + Mistral** — LLM läuft **lokal** auf deinem Server, keine Cloud-API, keine Kosten, keine Daten verlassen dein Netz
- **PostgreSQL + Redis** — Datenbank und Message Broker
- **Gotenberg + Tika** — PDF-Verarbeitung und OCR-Unterstützung

> **Hardware-Hinweis:** Mistral (7B) braucht als Docker-Container mind. ~8 GB RAM; mit GPU (NVIDIA) deutlich schneller. Wer wenig RAM hat, kann in `docker-compose.yml` bei `OLLAMA_MODEL` ein kleineres Modell wie `llama3.2:3b` oder `qwen2.5:3b` eintragen.

## Voraussetzungen

1. **Docker installieren** (falls noch nicht vorhanden):
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose-v2
   sudo usermod -aG docker $USER
   newgrp docker   # oder ausloggen/einloggen
   docker compose version
   ```

2. **Mistral-Modell einmalig laden** (ca. 4–5 GB Download):
   ```bash
   docker compose up -d ollama
   docker compose exec ollama ollama pull mistral
   docker compose exec ollama ollama ls   # Kontrolle
   ```

## Setup

```bash
cd paperless-mistral-setup

# 1. Passwörter & Secret generieren und in .env eintragen
cp .env.example .env
openssl rand -hex 24   # → PAPERLESS_SECRET_KEY
nano .env              # Passwörter eintragen

# 2. Starten
docker compose up -d
docker compose logs -f paperless    # beim ersten Start wird der Superuser angelegt
```

## Erster Login

- **Paperless-Weboberfläche:** `http://<server-ip>:8000`
- **paperless-ai Weboberfläche:** `http://<server-ip>:3000`
  - Die Konfiguration ist bereits über die Umgebungsvariablen gesetzt
    (Provider: Ollama, Modell: `mistral`, URL: `http://ollama:11434`).
  - Du musst nur den **Paperless-API-Token** eintragen: In Paperless
    → Einstellungen → API Auth → Token erzeugen, dann entweder in der
    paperless-ai-Weboberfläche eintragen oder in der `.env` bei
    `PAPERLESS_API_TOKEN` setzen und `docker compose up -d` erneut ausführen.
  - Danach paperless-ai einmal neu starten (`docker compose restart paperless-ai`),
    damit der RAG-Index aufgebaut wird.

## Dokumente einwerfen

- Über die Weboberfläche (Drag & Drop)
- Oder Dateien in den lokalen Ordner `./consume` legen — der Watch-Folder
  wird automatisch in Paperless eingelesen
- Per **ESP32-CAM**: Dokument unter die Kamera legen, Button drücken — das Foto
  fließt direkt über die REST-API in Paperless und wird automatisch verarbeitet.
  Details, Arduino-Sketch und Auslöser-Varianten: [esp32-cam/README.md](esp32-cam/README.md)
- Export/Backup landet in `./export`

## Nützliche Befehle

```bash
docker compose ps                    # Status
docker compose logs -f paperless-ai # KI-Verarbeitung beobachten
docker compose exec ollama ollama ps   # laufende Modelle anzeigen
docker compose down                 # Stoppen (Daten bleiben erhalten)
docker compose pull && docker compose up -d   # Update
```

## Backup

```bash
docker compose exec paperless document_exporter /usr/src/paperless/export -d
tar czf paperless-backup-$(date +%F).tar.gz export postgres ollama
```

## Sicherheit

- Dienste lauschen **nur im LAN** (keine Ports nach außen geöffnet, keine Reverse-Proxy-Freigabe).
- Weboberflächen mit starken Passwörtern sichern; im Router keine Portweiterleitung für Port 8000/3000 einrichten.
- Alle Daten — Dokumente **und** KI-Verarbeitung — bleiben auf deinem Server; es fließen keine Daten zu einem Cloud-Anbieter.
