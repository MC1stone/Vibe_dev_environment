# Installation von NIR Intelligence Main per Ansible (Debian 13)

Dieses Playbook installiert die Eigenentwicklung **NIR Intelligence Main**
auf einem frisch installierten **Debian 13 (x86_64)** direkt vom
**Ventoy-Stick**. Es ist idempotent — mehrfaches Ausführen führt zum
gleichen Ergebnis.

Diese Anleitung ist die **kanonische Release-Installationsanleitung**.
Die älteren Dokumente (`VENTOY_DEPLOYMENT.md`, `Ansible.md`,
`ansible/ventoy_setup/RUN_ANSIBLE_GUIDE.md`) beschreiben historische
Entwickler-Setups und sind für die Release-Installation nicht erforderlich.

## Was der Installationslauf erledigt

1. Pre-Flight: prüft Stick-Mount und Installationspaket (mit Timeout
   gegen hängende USB-Mounts).
2. Installiert das Paket — `.deb` bevorzugt, sonst Archiv mit
   `install.sh` (beides automatisch erkannt).
3. Aktiviert und startet den systemd-Dienst `nir_intelligence`
   (Django auf `http://127.0.0.1:8000`).
4. **Installiert Docker fehlendermaßen automatisch** (`docker.io`,
   `docker-compose-v2` per apt) — Docker ist Pflicht, nicht optional:
   ohne Docker gibt es keinen Backend-Stack und damit keine
   KI-Analysen.
5. Startet den Host-Backend-Stack (Ollama mit Mistral-Modell, Qdrant,
   Redis) als Docker-Container und zieht fehlende Modelle.
6. **Verifiziert die Installation Ende-zu-Ende**: Django antwortet
   per HTTP, Ollama ist erreichbar **und** das LLM-Modell liegt bereit,
   Qdrant meldet healthz, Redis antwortet auf PING. Erst wenn alle
   Checks grün sind, gilt die Installation als erfolgreich — sonst
   bricht der Lauf mit einer klaren Diagnose ab.

Der Release enthält **bewusst keine OP5-Komponenten** (kein MQTT-Worker,
keine kommerziellen Spektrometer-Adapter, kein MQTT-Broker). Die
Packaging-Skripte prüfen das beim Bauen und brechen bei einem Fund ab.

## Voraussetzungen auf dem Zielsystem

1. Frisch installiertes Debian 13 (mit `sudo`-fähigem Benutzer).
2. Ansible wird automatisch vom Bootstrap-Skript installiert, falls es
   fehlt (apt-Paket `ansible`; Fallback `pipx`):
   ```bash
   sudo bash /mnt/ventoy/ansible/bootstrap_install.sh
   ```
   (Hinweis: bewusst das Vollpaket `ansible`, nicht nur `ansible-core` —
   die `ansible.cfg` nutzt den `yaml`-Stdout-Callback sowie
   `profile_tasks`/`timer` aus `community.general`, die im Core-Paket
   fehlen und den Lauf zum Absturz bringen. Manuell:
   `sudo apt install -y ansible`, alternativ `pipx install --include-deps
   ansible`.)
3. Ventoy-Stick nach `/mnt/ventoy` einhängen:
   ```bash
   sudo mkdir -p /mnt/ventoy
   sudo mount /dev/sdX1 /mnt/ventoy    # sdX1 = Stick-Partition
   ```
4. Die Eigenentwicklung liegt auf dem Stick unter
   `/mnt/ventoy/ansible/` — **eines** von beiden:
   - `nir_intelligence_main.deb` (bevorzugt), oder
   - `nir_intelligence_main.tar.gz` (mit `install.sh` im Wurzelverzeichnis
     des entpackten Ordners)

   **Stick-Inhalt bauen (ein Befehl, auf dem Entwickler-Rechner):**
   ```bash
   ./packaging/build_ventoy_stick.sh /mnt/ventoy
   ```
   Das Skript baut das `.deb` (via `build_deb.sh`) und das `tar.gz`,
   prüft beide auf OP5-Freiheit, und kopiert Playbook,
   `bootstrap_install.sh` und diesen Guide nach
   `dist/ventoy_stick/ansible/` — bei Angabe eines Mountpunkts direkt
   auf den Stick. Der Stick ist danach einsatzbereit.

## Ausführung

**Ein Befehl (empfohlen)** — installiert fehlendes Ansible, installiert
die Plattform inkl. Docker und Backend-Stack und verifiziert alles:

```bash
sudo bash /mnt/ventoy/ansible/bootstrap_install.sh
```

Das Skript ist idempotent: bereits Installiertes wird übersprungen.
Argumente werden durchgereicht (z. B.
`--extra-vars "ventoy_mount=/media/$USER/VENTOY"`).

**Manuell** (wenn Ansible bereits installiert ist):

```bash
cd /pfad/zum/repo/NIR_Intelligence-main/ansible
ansible-playbook -i localhost, -c local install_nir_intelligence.yml \
    --ask-become-pass
```

Am Ende des Laufs steht der Verifikationsbericht — alle fünf Checks
(`django_service`, `django_http`, `ollama`, `qdrant`, `redis`) müssen
`true` sein:

```
verify_checks:
  django_service: true
  django_http: true
  ollama: true
  qdrant: true
  redis: true
```

## Dienste nach der Installation

| Dienst | Adresse (Host) |
|---|---|
| Django (systemd) | `http://127.0.0.1:8000` |
| Ollama (Mistral) | `http://127.0.0.1:11434` |
| Qdrant | `http://127.0.0.1:6333` |
| Redis | `redis://127.0.0.1:6379` |

## Variablen (Wartbarkeit)

Alle Pfade und Namen stehen im `vars:`-Block des Playbooks und können
bei Bedarf oder per `--extra-vars` überschrieben werden:

| Variable | Standard | Bedeutung |
|---|---|---|
| `ventoy_mount` | `/mnt/ventoy` | Mountpunkt des Sticks |
| `deb_path` | `…/nir_intelligence_main.deb` | `.deb` auf dem Stick |
| `archive_path` | `…/nir_intelligence_main.tar.gz` | Archiv auf dem Stick |
| `opt_install_dir` | `/opt/nir_intelligence` | Installationsziel |
| `required_packages` | `python3, wget, git, unzip` | Abhängigkeiten |
| `docker_packages` | `docker.io, docker-compose-v2` | Docker (OP59a, Pflicht) |
| `service_name` | `nir_intelligence` | systemd-Dienst |
| `llm_model` | `mistral:latest` | Modell-Check der Verifikation (OP59b) |
| `app_wait_timeout` | `60` | Sekunden Wartezeit auf die Django-App |
| `docker_wait_timeout` | `60` | Sekunden Wartezeit auf den Docker-Daemon |

## Fehlerbehandlung

- Ohne eingehängten Stick bzw. ohne `.deb`/Archiv bricht das Playbook vor
  jeder Änderung mit einer klaren Fehlermeldung ab.
- Hängt der Mount im Kernel (z. B. entfernte/defekte USB-Medien, die noch
  als gemountet registriert sind), blockiert jeder Dateizugriff. Die
  Pre-Flight-`stat`-Checks laufen deshalb mit Timeout (`preflight_timeout`,
  Standard 10 s): das Playbook bricht nach Ablauf mit einer
  Diagnose-Meldung ab (`mount | grep -i ventoy`, `timeout 10 stat
  /mnt/ventoy`, `lsblk -f`) statt endlos still zu stehen. Ein
  Kernel-D-State lässt sich nicht immer killen — im Zweifel hilft nur ein
  Neustart; danach den Stick neu mounten und erneut ausführen.
- Schlagen die Paketinstallation oder `install.sh` fehl, greift der
  jeweilige `rescue`-Block und meldet Diagnose-Hinweise
  (`dpkg-deb --info …` bzw. `tar -tzf …`).
- Fehlt Docker, wird es automatisch per apt installiert; schlägt das
  fehl oder antwortet der Daemon nicht, bricht der Lauf mit
  Diagnose-Hinweisen ab (`systemctl status docker`,
  `journalctl -u docker -n 50`) — kein stiller degraded-Zustand.
- Fehlt das LLM-Modell in Ollama, bricht die Verifikation ab und nennt
  den Nachlade-Befehl
  (`docker exec nir_ollama ollama pull mistral:latest`).
- Fällt ein Ende-zu-Ende-Check fehl, nennt der Abbruch die konkreten
  Checks und Diagnose-Befehle (`systemctl status nir_intelligence -l`,
  `docker ps`, `docker logs nir_ollama`, `curl http://127.0.0.1:8000/`).

## Idempotenz

- `apt`-Module prüfen den Paketstatus, `copy` vergleicht Prüfsummen.
- Docker wird nur installiert, wenn `docker --version` es nicht meldet.
- `unarchive` nutzt `creates:` gegen `install.sh`, `command` gegen
  `.install_completed` — ein zweiter Lauf führt die Skripte nicht erneut aus.
- Der Dienst wird nur gestartet/aktiviert, wenn er nicht schon läuft.
- `start_backend_stack.sh` ist idempotent: fehlende Container werden
  nachgestartet, das Modell nur gezogen, wenn es fehlt.

## Nach einem Reboot

Der systemd-Dienst startet automatisch. Der Backend-Stack kommt über
`restart: unless-stopped` der Container ebenfalls automatisch hoch.
Falls Docker erst später startet, genügt:

```bash
sudo bash /opt/nir_intelligence/packaging/start_backend_stack.sh
```

Diagnose: `docker logs nir_ollama`, `docker logs nir_qdrant`,
`docker compose -f /opt/nir_intelligence/packaging/docker-compose.host-backend.yml ps`.
