# Installation von NIR Intelligence Main per Ansible (Debian 13)

Dieses Playbook installiert die Eigenentwicklung **NIR Intelligence Main**
auf einem frisch installierten **Debian 13 (x86_64)** direkt vom
**Ventoy-Stick**. Es ist idempotent — mehrfaches Ausführen führt zum
gleichen Ergebnis.

## Voraussetzungen auf dem Zielsystem

1. Frisch installiertes Debian 13 (mit `sudo`-fähigem Benutzer)
2. Ansible wird automatisch vom Bootstrap-Skript installiert, falls es
   fehlt (apt-Paket `ansible`; Fallback `pipx`). Die manuelle Installation
   entfällt damit:
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

   **Stick-Inhalt bauen (ein Befehl):**
   ```bash
   ./packaging/build_ventoy_stick.sh /mnt/ventoy
   ```
   Das Skript baut das `.deb` (via `build_deb.sh`) und das `tar.gz`
   (OP26/OP27-Layout), kopiert Playbook, `bootstrap_install.sh` und diesen
   Guide nach `dist/ventoy_stick/ansible/` und — bei Angabe eines
   Mountpunkts — direkt auf den Stick. Der Stick ist danach einsatzbereit.

## Ausführung

**Ein Befehl (empfohlen)** — installiert fehlendes Ansible und startet das
Playbook direkt:

```bash
sudo bash /mnt/ventoy/ansible/bootstrap_install.sh
```

Das Skript ist idempotent: ist `ansible-playbook` bereits vorhanden,
entfällt die Installation; Argumente werden durchgereicht (z. B.
`--extra-vars "ventoy_mount=/media/$USER/VENTOY"`).

**Manuell** (wenn Ansible bereits installiert ist):

```bash
cd /pfad/zum/repo/NIR_Intelligence-main/ansible
ansible-playbook -i localhost, -c local install_nir_intelligence.yml \
    --ask-become-pass
```

Das Playbook:

1. prüft, ob der Stick eingehängt ist und ein `.deb`- oder Archiv-Paket
   vorhanden ist (bricht mit klarer Meldung ab, falls nicht),
2. aktualisiert den Paketindex (`apt update`),
3. installiert die Abhängigkeiten (`python3`, `wget`, `git`, `unzip`),
4. **.deb-Methode**: kopiert das Paket nach `/tmp/` und installiert es mit
   `apt` (inkl. automatischer Abhängigkeitsauflösung),
   **Archiv-Methode** (falls kein `.deb` vorliegt): kopiert das Archiv nach
   `/opt/`, entpackt es nach `/opt/nir_intelligence` und führt
   `/opt/nir_intelligence/install.sh` mit Root-Rechten aus,
5. aktiviert und startet den systemd-Dienst `nir_intelligence`,
   falls vorhanden (Name über die Variable `service_name` anpassbar),
6. verifiziert die Installation (Dienst-Status-Check).

## Variablen (Wartbarkeit)

Alle Pfade und Namen stehen im `vars:`-Block des Playbooks und können
bei Bedarf oder per `--extra-vars` überschrieben werden:

| Variable | Standard | Bedeutung |
|---|---|---|
| `ventoy_mount` | `/mnt/ventoy` | Mountpunkt des Sticks |
| `deb_path` | `…/nir_intelligence_main.deb` | `.deb` auf dem Stick |
| `archive_path` | `…/nir_intelligence_main.tar.gz` | Archiv auf dem Stick |
| `opt_install_dir` | `/opt/nir_intelligence` | Entpackziel (Archiv) |
| `required_packages` | `python3, wget, git, unzip` | Abhängigkeiten |
| `service_name` | `nir_intelligence` | systemd-Dienst |

## Fehlerbehandlung

- Ohne eingehängten Stick bzw. ohne `.deb`/Archiv bricht das Playbook vor
  jeder Änderung mit einer klaren Fehlermeldung ab.
- Hängt der Mount im Kernel (z. B. entfernte/defekte USB-Medien, die noch
  als gemountet registriert sind), blockiert jeder Dateizugriff. Die
  Pre-Flight-`stat`-Checks laufen deshalb mit Timeout (`preflight_timeout`,
  Standard 10 s): Das Playbook bricht nach Ablauf mit einer
  Diagnose-Meldung ab (`mount | grep -i ventoy`,
  `timeout 10 stat /mnt/ventoy`, `lsblk -f`) statt endlos still zu stehen.
  Ein Kernel-D-State lässt sich nicht immer killen - im Zweifel hilft nur
  ein Neustart; danach den Stick neu mounten und erneut ausführen.
- Schlägt die Paketinstallation oder `install.sh` fehl, greift der
  jeweilige `rescue`-Block und meldet Diagnose-Hinweise
  (`dpkg-deb --info …` bzw. `tar -tzf …`).
- Existiert kein systemd-Dienst, wird die Installation trotzdem als
  abgeschlossen gemeldet und die Dienstprüfung übersprungen.

## Idempotenz

- `apt`-Module prüfen den Paketstatus, `copy` vergleicht Prüfsummen.
- `unarchive` nutzt `creates:` gegen `install.sh`, `command` gegen
  `.install_completed` — ein zweiter Lauf führt die Skripte nicht erneut aus.
- Der Dienst wird nur gestartet/aktiviert, wenn er nicht schon läuft.

## Host-Backend-Stack (OP45)

Die systemd-Django-App laeuft auf dem Host (`127.0.0.1:8000`). Die
Analyse-Backends laufen als Docker-Container mit Port-Freigabe an
`127.0.0.1` - nur so erreicht die Host-App Ollama (Mistral), Qdrant
(Aehnlichkeitssuche) und Redis (Cache). Ohne den Stack sind alle
KI-Analysen degraded.

Das Playbook prueft Docker und Docker Compose und startet den Stack dann
automatisch:

    bash /opt/nir_intelligence/packaging/start_backend_stack.sh

Manuell (z. B. nach einem Reboot, falls Docker erst spaeter startet):

    sudo bash /opt/nir_intelligence/packaging/start_backend_stack.sh

Fehlt Docker oder Compose, bricht die Installation nicht ab - das Playbook
meldet einen klaren Hinweis (Installation z. B. per
`apt-get install -y docker.io docker-compose-v2` auf Mint/Debian/Ubuntu)
und die KI-Analysen bleiben bis zum Stack-Start degraded. Das Skript ist
idempotent: Ein erneuter Lauf startet fehlende Container nach und zieht
das Mistral-Modell nur, wenn es fehlt.

Dienste nach dem Start:

| Dienst | Adresse (Host) |
|---|---|
| Django (systemd) | `http://127.0.0.1:8000` |
| Ollama | `http://127.0.0.1:11434` |
| Qdrant | `http://127.0.0.1:6333` |
| Redis | `redis://127.0.0.1:6379` |

Diagnose: `docker logs nir_ollama`, `docker logs nir_qdrant`,
`docker compose -f /opt/nir_intelligence/packaging/docker-compose.host-backend.yml ps`.
