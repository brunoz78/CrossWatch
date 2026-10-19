# CrossWatch – deutsche Ausgabe

**CrossWatch (CW)** erfasst mit dem Watcher, was du schaust, und gleicht Watchlists, Bewertungen,
Verlauf, Wiedergabe-Fortschritt und Sammlungen zwischen unterstützten Medienservern und Trackern
ab. **Der Watcher braucht weder Plex Pass noch Emby Premiere.**

Richte mehrere Watcher-Routen für deine Server und Benutzer ein und lege Sync-Paare an: zwischen
Medienservern, zwischen Trackern oder von einem Server zu einem Tracker. CW läuft lokal, mit
Weboberfläche und Kommandozeile.

> [!NOTE]
> Dies ist ein **Fork** von [cenodude/CrossWatch](https://github.com/cenodude/CrossWatch) mit
> deutscher Oberfläche, zusätzlicher Absicherung und einer Installation für Proxmox. Er wird jede
> Woche automatisch mit dem Original abgeglichen. Was genau anders ist, steht
> [unten](#was-dieser-fork-anders-macht) und in [FORK.md](../FORK.md).

<p align="center">
  <a href="https://github.com/brunoz78/CrossWatch/releases/latest">
    <img src="https://img.shields.io/github/v/release/brunoz78/CrossWatch?display_name=release&amp;logo=github&amp;label=Aktuelles%20Release&amp;style=for-the-badge" alt="Aktuelles Release">
  </a>
  <a href="https://github.com/brunoz78/CrossWatch/actions/workflows/fork-sync.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/brunoz78/CrossWatch/fork-sync.yml?label=Wochenabgleich&amp;style=for-the-badge&amp;logo=github" alt="Wochenabgleich">
  </a>
  <a href="https://wiki.crosswatch.app/">
    <img alt="Wiki" src="https://img.shields.io/badge/Wiki-wiki.crosswatch.app-B026FF?style=for-the-badge">
  </a>
</p>

<img width="1672" height="941" alt="Übersicht der CrossWatch-Weboberfläche" src="https://github.com/user-attachments/assets/06355278-8cdc-4a13-95ae-89f924fd0975" />

## Was dieser Fork anders macht

| | Original | Dieser Fork |
|---|---|---|
| **Sprache** | nur Englisch | Englisch und **Deutsch**, umschaltbar im Profil unter *Einstellungen → Anzeige → Sprache*. Ohne Auswahl gilt die Browsersprache. |
| **Ersteinrichtung** | wer die Instanz zuerst öffnet, legt das Admin-Konto an | Admin-Konto nur über einen **Einmal-Link** aus dem Installationsskript bzw. Server-Protokoll |
| **Server-Adressen** | werden ungeprüft gespeichert | Adressen auf Cloud-Metadaten oder link-lokale Ziele werden abgelehnt (SSRF-Schutz) |
| **Profilbilder von OIDC** | nur die erste Adresse wird geprüft, Weiterleitungen nicht | nur über öffentliche HTTPS-Adressen, jede Weiterleitung wird geprüft |
| **Massenlöschung** | standardmässig erlaubt, Drop-Guard aus | standardmässig **blockiert**, Drop-Guard an; ein Fehler im Schutz blockiert statt durchzulassen |
| **Abhängigkeiten** | neueste Versionen beim Bau | feste Versionen mit Prüfsummen (`requirements.lock`) im Release |
| **Installation** | Docker-Image | Python-Dienst in einem **Proxmox-LXC** (Debian 13), ohne Docker |
| **Update** | neues Image ziehen | Glocke → **«Jetzt aktualisieren»** oder `update` im Container, mit automatischer Rückkehr zur alten Version |
| **Releases** | von Hand | jeden Montag automatisch: neuestes offizielles Release des Originals einspielen, neue Texte übersetzen, Release `<Version des Originals>.post<Datum>` bauen |

Die Absicherung stammt zum Teil aus [jabrown93/CrossWatch](https://github.com/jabrown93/CrossWatch).
Die Dateien des Originals bleiben fast unverändert; die Übersetzung geschieht beim Anzeigen im
Browser. So fliessen neue Versionen des Originals ohne Konflikte ein.

## Warum CW?

**Der Watcher braucht weder Plex Pass noch Emby Premiere.** Richte mehrere Routen für deine Server
und Benutzer ein und sende die Wiedergabe-Aktivität an die gewünschten Ziele.

Du kannst Medienserver untereinander abgleichen, sie mit Trackern verbinden oder Tracker
untereinander abgleichen. Pro Paar wählst du, was abgeglichen wird: Verlauf, Fortschritt,
Watchlists, Bewertungen oder Sammlungen, je nachdem, was der Anbieter unterstützt. Paare laufen von
Hand oder nach Zeitplan.

Alles an einem Ort: Konten, Watcher-Routen, Abgleiche, laufende Wiedergaben und eine gemeinsame
Watchlist. Profile trennen deine Einrichtung von der deiner Familie und Freunde.

Deine Daten bleiben bei dir, ohne Bindung an einen Tracker. Gleiche sie zwischen deinen Diensten
ab und bewahre lokale Snapshots im CW-Tracker auf.

Für mehr Kontrolle zeigt dir der interaktive Abgleich die Änderungen vor dem Übernehmen. Die Analyse
findet fehlende Elemente, und gespeicherte Zuordnungen korrigieren falsche Treffer, die
Episodennummerierung von Anime sowie geteilte oder kombinierte Episoden für künftige Abgleiche.

## Funktionen

- Watcher mit mehreren Routen für verschiedene Server und Benutzer. **Ohne Plex Pass oder Emby Premiere.**
- Abgleich Server ↔ Server, Server ↔ Tracker und Tracker ↔ Tracker, wo unterstützt.
- Watchlists, Bewertungen, Verlauf, Wiedergabe-Fortschritt und Sammlungen, bei unterstützten Trackern auch wiederholte Sichtungen.
- Mehrere Konten, getrennte Profile und verwaltete Benutzer.
- Interaktiver Abgleich: Hinzufügen, Ändern und Entfernen vor dem Übernehmen prüfen.
- Scrobbeln per Webhook bei unterstützten Anbietern.
- Eigene Zuordnungen für falsche Treffer, Anime-IDs und geteilte oder kombinierte Episoden.
- Ein lokaler CW-Tracker mit Snapshots deiner Server- und Tracker-Daten.
- Optionale KI-Hilfe: CrossWatch mit deinem eigenen KI-Modell um Rat fragen. Auch KI-Apps wie Claude, Codex oder Cursor kannst du Lesezugriff geben. Aus, bis du es einrichtest.

## Unterstützte Dienste

CW arbeitet mit Plex, Jellyfin, Emby, SIMKL, Floppy, FlickList, Trakt, WeTrakr, AniList,
MyAnimeList (MAL), Kitsu, TMDb, MDBList, PublicMetaDB, PunchPlay, BingeBase, Scrob, Tautulli,
Tracearr, Kodi, Nuvio, Stremio und dem eigenen lokalen CW-Tracker.

Nicht jeder Dienst kann alles. Manche gleichen Listen und Verlauf ab, andere melden die Wiedergabe.
Details zur Einrichtung stehen im [Wiki](https://wiki.crosswatch.app/) (englisch).

## Installation auf Proxmox

Auf der Shell des Proxmox-Hosts:

```bash
COMMUNITY_SCRIPTS_URL=https://raw.githubusercontent.com/brunoz78/CrossWatch/main/proxmox bash -c "$(curl -fsSL https://raw.githubusercontent.com/brunoz78/CrossWatch/main/proxmox/ct/crosswatch.sh)"
```

Das Skript legt einen unprivilegierten Debian-13-Container an (2 Kerne, 1 GB RAM, 8 GB Disk) und
installiert das neueste Release. Vorgaben wie Container-ID, Name oder feste IP lassen sich
voranstellen, zum Beispiel `var_ctid=311 var_hostname=crosswatch var_net=192.168.1.50/24
var_gateway=192.168.1.1`.

Am Ende erscheint ein **Einrichtungslink** (`http://<IP>:8787/?setup=…`). Nur über diesen Link
lässt sich das Admin-Konto anlegen. Weitere Details stehen in [proxmox/README.md](../proxmox/README.md).

Die Docker-Images `ghcr.io/cenodude/crosswatch` gehören zum Original und enthalten die Ergänzungen
dieses Forks **nicht**.

### Dein erster Abgleich

Öffne den Einrichtungslink und lege dein Admin-Konto an, danach:

1. Verbinde die Konten, die du nutzen willst.
2. Erstelle ein Sync-Paar: Wähle die Dienste und was abgeglichen wird.
3. Führe das Paar aus und prüfe die Ergebnisse. Mit dem interaktiven Abgleich siehst du die Änderungen vorher.
4. Lege einen Zeitplan an, wenn es automatisch laufen soll.

Die vollständige Anleitung steht im [Wiki](https://wiki.crosswatch.app/getting-started/first-time-setup).

### Aktualisieren

- In CrossWatch: Glocke → «Jetzt aktualisieren» (nur Admins).
- In der Konsole des Containers: `update`.

Startet die neue Version nicht, wird die vorherige automatisch wiederhergestellt. Vor jedem Update
wird `/config` gesichert.

## Scrobbeln

Der **Watcher** meldet Wiedergaben von Plex, Emby, Jellyfin, Kodi und Scrob an unterstützte
Tracker, ohne Plex Pass oder Emby Premiere.

Alternativ gibt es **Webhooks** von Plex, Emby und Jellyfin. Die Anime-ID-Zuordnung steht für
Watcher und Webhooks bei unterstützten Anbietern zur Verfügung.

### Kodi

Das [Add-on «CrossWatch for Kodi»](https://github.com/crosswatch-app/kodi-addon) meldet Wiedergaben
und Zuschauer und kann direkt bewerten. Mit einer Watcher-Route pro Zuschauer hat jeder seinen
eigenen Verlauf, auch bei einem gemeinsamen Kodi-Profil.

## Zuordnungen

Manchmal hat dieselbe Episode bei einem anderen Dienst eine andere Nummer, oder ein Titel wird dem
falschen Film zugeordnet. Du korrigierst Titel, IDs, Staffeln und Episoden und speicherst die
Zuordnung für künftige Abgleiche. Geteilte und kombinierte Episoden werden unterstützt, Zuordnungen
lassen sich importieren und exportieren.

Die Anime-ID-Zuordnung (mit AniBridge und animeApi) unterstützt Paare mit AniList, MyAnimeList,
Kitsu, SIMKL und dem CW-Tracker.

## Werkzeuge

Die **Analyse** hilft, wenn etwas nicht wie erwartet abgeglichen wurde: Snapshots vergleichen,
fehlende Elemente und abweichende Sichtungszeiten finden, falsche Treffer korrigieren, offene
Wiederholungen prüfen und gesperrte Elemente freigeben.

| Werkzeug | Was du damit machst |
| --- | --- |
| Editor | Elemente ansehen, hinzufügen oder sperren, gespeicherte Zuordnungen verwalten, geteilte oder kombinierte Episoden bearbeiten. |
| Topologie | Deine Abgleich-Routen sehen und überlappende Wege erkennen. |
| Wiedergabe-Fortschritt | Unvollendete Wiedergaben über alle Anbieter ansehen und bearbeiten. |
| Import und Export | Tracker-Dateien importieren oder deine Daten exportieren. |
| Ereignisse und Protokolle | Abgleich-Verlauf durchsehen, Probleme untersuchen, Protokolle nach Paar oder Lauf filtern. |
| Erfassungen | Watchlists, Bewertungen und Verlauf bei Anbietern zurücksetzen. |

Dazu kommen eine gemeinsame Watchlist, eine Karte mit der laufenden Wiedergabe und
Benachrichtigungen zum Abgleich-Fortschritt und zu offenen Prüfungen. Zeitpläne können einfach oder
pro Paar eingerichtet werden.

Bei Plex lässt sich der Verlauf entfernter Titel in den CW-Tracker importieren.

## Ohne Weboberfläche

Setze in `/etc/systemd/system/crosswatch.service` zusätzlich `Environment=CW_CLI_ONLY=1` und starte
den Dienst neu (`systemctl daemon-reload && systemctl restart crosswatch`). API, Kommandozeile,
Webhooks und Anmelde-Rückrufe funktionieren weiter.

## Hilfe und Rückmeldungen

- Fehler in der **Übersetzung, der Installation oder beim Update** dieses Forks: bitte in den
  [Issues dieses Forks](https://github.com/brunoz78/CrossWatch/issues) melden.
- Alles andere betrifft das Original: [Issues bei cenodude/CrossWatch](https://github.com/cenodude/CrossWatch/issues),
  Fragen und Diskussion auf [r/CrossWatchApp](https://www.reddit.com/r/CrossWatchApp/). Dort bitte
  auf Englisch und nur, wenn sich der Fehler auch im Original zeigt.

Sicherheitsmeldungen: siehe [SECURITY.md](../SECURITY.md). Lizenz: [AGPL-3.0](../LICENSE), wie das
Original.

## Unterstützung

<p align="center">
  <a href="https://www.buymeacoffee.com/cenodude">
    <img alt="Buy Me a Coffee" src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-ffdd00?style=for-the-badge&amp;logo=buy-me-a-coffee&amp;logoColor=000000">
  </a>
</p>

Spenden über Buy Me a Coffee gehen an den Entwickler des Originals; jeder Rappen fliesst direkt an
die **ALS-Stiftung in den Niederlanden**.
