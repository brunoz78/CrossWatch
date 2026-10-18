# CrossWatch auf Proxmox

Installiert CrossWatch (dieser Fork, mit deutscher Oberfläche) als Python-Dienst in einem
unprivilegierten Debian-13-Container. Die Skripte folgen dem Aufbau von community-scripts.

## Installation

Auf der Shell des Proxmox-Hosts:

```bash
COMMUNITY_SCRIPTS_URL=https://raw.githubusercontent.com/brunoz78/ProxmoxVED/main bash -c "$(curl -fsSL https://raw.githubusercontent.com/brunoz78/ProxmoxVED/main/ct/crosswatch.sh)"
```

Am Ende erscheint ein **Einrichtungslink** (`http://<IP>:8787/?setup=…`). Nur über diesen Link
lässt sich das Admin-Konto anlegen. Der Code steht auch in `/var/lib/crosswatch/.setup_token`.

## Aufbau im Container

| Pfad | Inhalt |
|---|---|
| `/opt/crosswatch` | Programm mit eigener Python-Umgebung (`.venv`) |
| `/opt/crosswatch.old` | vorherige Version, für die automatische Rückkehr |
| `/var/lib/crosswatch` | Daten: `config.json`, Datenbanken, Snapshots |
| `/var/backups/crosswatch` | Datensicherung vor jedem Update (die letzten 5) |
| `/usr/local/bin/crosswatch-update` | Installation und Update |

Dienste: `crosswatch.service` (die App) und `crosswatch-update.path` (startet ein Update, wenn
die App darum bittet). Protokoll: `journalctl -u crosswatch -f`.

## Update

- In CrossWatch: Glocke → «Jetzt aktualisieren» (nur Admins).
- In der Container-Konsole: `update` oder direkt `crosswatch-update`.

Beide nutzen dasselbe Skript: neues Release laden, Prüfsumme prüfen, Abhängigkeiten aus der
`requirements.lock` installieren, umschalten, Start prüfen. Antwortet die neue Version nicht,
wird die alte wiederhergestellt.

## Einstellungen

In `/etc/systemd/system/crosswatch.service` (danach `systemctl daemon-reload && systemctl
restart crosswatch`):

- `CW_UI_LANG=de`: Grundsprache, solange im Profil nichts gewählt ist.
- `TZ=Europe/Zurich`: Zeitzone.
