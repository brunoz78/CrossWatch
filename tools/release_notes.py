#!/usr/bin/env python3
"""Write German release notes for a fork release.

Takes the release notes of the merged original release and the fork commits. The
German part comes from release-notes/de/<version>.md when that file exists (hand
translations, kept for rebuilds of the same version), otherwise from the Claude API
when ANTHROPIC_API_KEY is set. Without either the original notes are kept in English.
Used by the weekly sync workflow.

Usage:
    python tools/release_notes.py v0.14.2 upstream.md fork.txt > notes.md
    python tools/release_notes.py --missing v0.14.2   # prints "yes" without a German text
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MODEL = "claude-opus-5-5"
STORE = Path(__file__).resolve().parents[1] / "release-notes" / "de"


def stored(tag: str) -> str:
    """Hand-made German notes for a version, starting with its own "## Neu in …" headings."""
    p = STORE / f"{tag}.md"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""

SYSTEM = """You translate the release notes of CrossWatch, a self-hosted tool that syncs watch
history, watchlists, ratings and playback progress between Plex, Jellyfin, Emby, Trakt and
other services, from English into German for Switzerland.

Rules:
- Swiss spelling: never use "ß", always "ss". Address the reader with "du".
- Keep the Markdown structure, links, code spans and version numbers.
- Drop the top-level "# CrossWatch vX" heading. Use "### Highlights" and
  "### Korrekturen und Verbesserungen" as section headings, and translate the prefixes
  Added/Changed/Fixed/Improved/Updated/Removed as Neu/Geändert/Behoben/Verbessert/Aktualisiert/Entfernt.
- Turn a "Updated Wiki" section into one line: "Wiki (englisch): " followed by the links, separated by " · ".
- Keep product and service names unchanged. Use these terms: sync = Abgleich, sync pair = Sync-Paar,
  history = Verlauf, ratings = Bewertungen, progress = Fortschritt, collection = Sammlung,
  watchlist = Merkliste, provider = Anbieter, mapping = Zuordnung, settings = Einstellungen.
- Leave out jokes and personal remarks of the author; keep every functional change.
- Answer with the translated Markdown only."""


def translate(text: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium"},
        system=SYSTEM,
        messages=[{"role": "user", "content": text}],
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"translation stopped: {response.stop_reason}")
    return next(b.text for b in response.content if b.type == "text").strip()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "--missing":
        print("" if stored(sys.argv[2]) else "yes")
        return 0
    tag, upstream_file, fork_file = sys.argv[1:4]
    upstream = Path(upstream_file).read_text(encoding="utf-8").strip()
    if upstream.startswith("# "):  # the own "# CrossWatch vX" title, replaced by our heading
        upstream = upstream.partition("\n")[2].strip()
    fork = [line for line in Path(fork_file).read_text(encoding="utf-8").splitlines() if line.strip()]

    body, heading = upstream, f"## Neu in CrossWatch {tag} (englisch)"
    if stored(tag):
        # the stored text carries its own headings, e.g. for 0.14.4 and 0.14.3
        body, heading = stored(tag), ""
    elif upstream and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            body, heading = translate(upstream), f"## Neu in CrossWatch {tag}"
        except Exception as exc:  # keep the English notes rather than fail the release
            print(f"translation failed: {exc}", file=sys.stderr)

    print(f"Deutsche Ausgabe von CrossWatch, Stand Original [{tag}](https://github.com/cenodude/CrossWatch/releases/tag/{tag}),"
          " mit deutscher Oberfläche und Sicherheits-Ergänzungen.")
    print()
    print("**Aktualisieren:** Glocke in CrossWatch → «Jetzt aktualisieren», oder `update` in der Konsole des Containers.")
    if body:
        print()
        if heading:
            print(heading)
            print()
        print(body)
    if fork:
        print()
        print("## Neu in der deutschen Ausgabe")
        print("\n".join(fork))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
