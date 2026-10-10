# Paperless-ngx + Mistral AI — Home-Server Setup (Linux Mint, LAN-only)

Automatische Dokumentenverwaltung mit KI-Verschlagwortung:
- **Paperless-ngx** — Dokumentenmanagement (DMS) mit OCR
- **paperless-ai** — verbindet Paperless mit der Mistral-API, verschlagwortet Dokumente automatisch (Titel, Tags, Korrespondent, Typ)
- **PostgreSQL + Redis** — Datenbank und Message Broker
- **Gotenberg + Tika** — PDF-Verarbeitung und OCR-Unterstützung

## Voraussetzungen

1. **Docker installieren** (falls noch nicht vorhanden):
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose-v2
   sudo usermod -aG docker $USER
   newgrp docker   # oder ausloggen/einloggen
   docker compose version
   ```

2. **Mistral API-Key** besorgen: https://console.mistral.ai → API Keys → Key erzeugen.

## Setup

```bash
cd paperless-mistral-setup

# 1. Passwörter & Secret generieren und in .env eintragen
cp .env.example .env
openssl rand -hex 24   # → PAPERLESS_SECRET_KEY
nano .env              # API-Key + Passwörter eintragen

# 2. Starten
docker compose up -d
docker compose logs -f paperless    # beim ersten Start wird der Superuser angelegt
```

## Erster Login

- Weboberfläche: `http://<server-ip>:8000`
- **paperless-ai Konfiguration** (einmalig): `http://<server-ip>:3000`
  → dort Mistral als Provider (OpenAI-kompatibel) eintragen:
  - Base URL: `https://api.mistral.ai/v1`
  - Model: `mistral-small-latest`
  - API-Key: dein Mistral-Key
  - Paperless URL: `http://paperless:8000`, Token aus der Weboberfläche
    (Paperless → Settings → API Auth → Token erzeugen)
  - danach paperless-ai einmal neu starten (`docker compose restart paperless-ai`),
    damit der RAG-Index aufgebaut wird

## Dokumente einwerfen

- Über die Weboberfläche (Drag & Drop)
- Oder Dateien in den lokalen Ordner `./consume` legen — der Watch-Folder
  wird automatisch in Paperless eingelesen
- Export/Backup landet in `./export`

## Nützliche Befehle

```bash
docker compose ps                  # Status
docker compose logs -f paperless-ai # KI-Verarbeitung beobachten
docker compose down                # Stoppen (Daten bleiben erhalten)
docker compose pull && docker compose up -d   # Update
```

## Backup

```bash
docker compose exec paperless document_exporter /usr/src/paperless/export -d
tar czf paperless-backup-$(date +%F).tar.gz export postgres
```

## Sicherheit

- Dienste lauschen **nur im LAN** (keine Ports nach außen geöffnet, keine Reverse-Proxy-Freigabe).
- Weboberflächen mit starken Passwörtern sichern; ggf. im Router keine Portweiterleitung für Port 8000/3000 einrichten.
- Der Mistral-API-Key wird **nicht** in der Weboberfläche von Paperless gespeichert, sondern nur in der `.env` — diese Datei nie committen.
