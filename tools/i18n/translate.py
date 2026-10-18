#!/usr/bin/env python3
"""Translate missing UI strings with the Claude API and add them to assets/i18n/<lang>.js.

Needs the anthropic package and ANTHROPIC_API_KEY. Used by the weekly sync
workflow after upstream changes are merged.

Usage:
    python tools/i18n/translate.py de            # translate everything missing
    python tools/i18n/translate.py de --dry-run  # only list what would be sent
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract  # noqa: E402
import locale_file  # noqa: E402

MODEL = "claude-opus-5-5"
BATCH = 150

SYSTEM = """You translate the user interface of CrossWatch, a self-hosted tool that syncs
watch history, watchlists, ratings and playback progress between Plex, Jellyfin, Emby,
Trakt, SIMKL and other services, from English into German for Switzerland.

Rules:
- Swiss spelling: never use "ß", always "ss" (e.g. "schliessen", "gross").
- Address the user informally with "du" (lowercase).
- Keep placeholders such as {0}, {1} exactly; you may reorder them. A placeholder that only
  adds an English plural "s" may be dropped (write "Element(e)" or rephrase instead).
- Keep product and service names unchanged (CrossWatch, Plex, Jellyfin, Trakt, SIMKL, TMDb,
  Watcher, Scrobbler, Webhook, Snapshot, Blackbox, Tombstone, Watchlist).
- Use these terms consistently: sync = Abgleich / abgleichen, sync pair = Sync-Paar,
  synchronization = Synchronisierung, history = Verlauf, ratings = Bewertungen,
  progress = Fortschritt, collection = Sammlung, library = Mediathek, provider = Anbieter,
  mapping = Zuordnung, capture = Erfassung, unresolved = offen, settings = Einstellungen,
  scheduling = Zeitplan, maintenance = Wartung, sign in = anmelden, credentials = Zugangsdaten,
  Main (page) = Start, destination/target = Ziel, source = Quelle.
- Short labels stay short; keep capitalisation style (ALL CAPS stays all caps).
- Quote UI names with «» when the English text refers to a button or page by name.
- If a string is code, a CSS class, a URL or otherwise not human text, return it unchanged."""

SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"source": {"type": "string"}, "target": {"type": "string"}},
                "required": ["source", "target"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}


def translate_batch(client, items: list[str]) -> dict[str, str]:
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM,
        messages=[{"role": "user", "content": "Translate these strings. Return every source string exactly as given.\n\n"
                   + json.dumps(items, ensure_ascii=False, indent=1)}],
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"translation stopped: {response.stop_reason}")
    text = next(b.text for b in response.content if b.type == "text")
    wanted = set(items)
    out = {}
    for row in json.loads(text).get("translations", []):
        src, dst = row.get("source", ""), row.get("target", "")
        if src in wanted and dst and not locale_file.problems(src, dst):
            out[src] = dst
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lang")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    have = locale_file.load(args.lang)
    ignore_file = extract.ROOT / "tools" / "i18n" / "ignore.json"
    ignore = set(json.loads(ignore_file.read_text(encoding="utf-8"))) if ignore_file.exists() else set()
    missing = [s for s in extract.collect() if s not in have and s not in ignore]
    print(f"{len(missing)} strings missing for {args.lang}")
    if not missing or args.dry_run:
        print("\n".join(missing))
        return 0

    import anthropic

    client = anthropic.Anthropic()
    added = 0
    for i in range(0, len(missing), BATCH):
        batch = missing[i:i + BATCH]
        result = translate_batch(client, batch)
        have.update(result)
        added += len(result)
        locale_file.save(args.lang, have)
        print(f"batch {i // BATCH + 1}: {len(result)}/{len(batch)} translated")
    print(f"{added} strings added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
