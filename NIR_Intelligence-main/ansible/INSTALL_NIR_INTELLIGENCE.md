# Installation von NIR Intelligence Main per Ansible (Debian 13)

Dieses Playbook installiert die Eigenentwicklung **NIR Intelligence Main**
auf einem frisch installierten **Debian 13 (x86_64)** direkt vom
**Ventoy-Stick**. Es ist idempotent — mehrfaches Ausführen führt zum
gleichen Ergebnis.

## Voraussetzungen auf dem Zielsystem

1. Frisch installiertes Debian 13 (mit `sudo`-fähigem Benutzer)
2. Ansible installiert (auf dem Zielsystem selbst, da `localhost`):
   ```bash
   sudo apt update
   sudo apt install -y ansible
   ```
   (Alternativ genügt `pipx install ansible-core`, falls Debian das Paket
   `ansible` nicht führen sollte.)
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

## Ausführung

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
