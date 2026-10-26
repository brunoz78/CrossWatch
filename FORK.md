# CrossWatch – Fork brunoz78

Dieser Fork von [cenodude/CrossWatch](https://github.com/cenodude/CrossWatch) ergänzt das
Original, ohne es umzubauen. Er wird jede Woche automatisch mit dem Original abgeglichen.
Lizenz wie das Original: AGPL-3.0. Geändert ab Oktober 2026.

## Was anders ist

**Deutsche Oberfläche, umschaltbar**
- Die Sprache stellst du im Profil unter *Einstellungen → Anzeige → Sprache* um (Englisch oder
  Deutsch). Sie gilt pro Browser. Ohne Auswahl richtet sie sich nach `CW_UI_LANG`, sonst nach
  der Browsersprache.
- Technik: `assets/i18n/i18n.js` ersetzt die englischen Texte beim Anzeigen anhand von
  `assets/i18n/de.js`. Die Originaldateien bleiben unverändert. Neue Texte aus dem Original
  findet `tools/i18n/extract.py`, `tools/i18n/translate.py` übersetzt sie über die Claude-API.

**Sicherheit** (zum Teil aus [jabrown93/CrossWatch](https://github.com/jabrown93/CrossWatch) übernommen)
- Einmal-Link für die Ersteinrichtung (`setup_guard.py`): Das erste Admin-Konto kann nur
  anlegen, wer den Link aus dem Server-Protokoll bzw. vom Installationsskript hat.
- SSRF-Schutz (`cw_platform/url_validation.py`): Server-Adressen, die auf Cloud-Metadaten oder
  link-lokale Adressen zeigen, werden beim Speichern abgelehnt. Profilbilder von OIDC-Anbietern
  werden nur über öffentliche HTTPS-Adressen geladen, jede Weiterleitung wird geprüft.
- Schutz vor Massenlöschung und Drop-Guard sind standardmässig an. Ein Fehler im Schutz
  blockiert die Löschung, statt sie durchzulassen.
- Release-Pakete enthalten eine `requirements.lock` mit Prüfsummen; installiert wird nur genau
  diese Version jeder Abhängigkeit.

**Proxmox-Installation mit Update-Knopf** (`proxmox/`, `fork_update.py`)
- Installation als Python-Dienst in einem Debian-13-LXC, ohne Docker.
- Updates über die Glocke in der Oberfläche («Jetzt aktualisieren») oder `update` in der
  Konsole. Startet die neue Version nicht, wird die alte automatisch zurückgeholt.

## Ablauf der Aktualisierung

Der Workflow `.github/workflows/fork-sync.yml` läuft jeden Samstag um 01:00 UTC (Nacht von Freitag auf Samstag):

1. Das neueste **offizielle Release** des Originals einspielen (nie den Entwicklungszweig). Bei
   einem Konflikt wird ein Issue erstellt.
2. Neue Texte ermitteln und mit der Claude-API übersetzen (Secret `ANTHROPIC_API_KEY`). Ohne
   Schlüssel entsteht ein Issue mit der Liste.
3. Kurzer Starttest, dann Release `v<Version des Originals>.post<Datum>` mit Archiv und Prüfsumme.

Optionales Secret `SYNC_TOKEN`: ein Token mit Recht auf *Contents* und *Workflows* für dieses
Repo. Nur nötig, wenn das Original seine eigenen Workflow-Dateien ändert.

## Dateien des Forks

| Datei | Zweck |
|---|---|
| `fork_addons.py` | einziger Einhängepunkt in `crosswatch.py` |
| `i18n_frontend.py`, `assets/i18n/` | Übersetzung |
| `tools/i18n/` | Texte finden und übersetzen |
| `setup_guard.py` | Einmal-Link für die Ersteinrichtung |
| `cw_platform/url_validation.py` | SSRF-Schutz |
| `fork_update.py`, `assets/fork/update.js` | Update-Knopf |
| `proxmox/` | Installations- und Update-Skripte |
