#!/usr/bin/env python3
"""Keep the German catalogs in assets/locales/de in step with the English ones.

Fork addition. Every key of assets/locales/en/*.json gets a German text in the matching
assets/locales/de/*.json. Existing German texts are kept. New keys are filled from the
runtime dictionary assets/i18n/de.js when the English text is known there; the rest is
listed so it can be translated (and then passed in with --apply).

Usage:
    python tools/i18n/locale_sync.py               # add new keys, print the open ones
    python tools/i18n/locale_sync.py --json        # open ones as JSON {key: english}
    python tools/i18n/locale_sync.py --apply f.json  # write {key: german} into the catalogs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ROOT / "assets" / "locales"
LANG = "de"
VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")
RICH = re.compile(r"\[\[/?[a-z]+\]\]")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import locale_file  # noqa: E402


def flatten(tree: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in tree.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, name))
        else:
            out[name] = value
    return out


def rebuild(english: dict, flat: dict[str, str], prefix: str = "") -> dict:
    """Same shape and key order as the English tree, values from flat."""
    out: dict = {}
    for key, value in english.items():
        name = f"{prefix}.{key}" if prefix else key
        out[key] = rebuild(value, flat, name) if isinstance(value, dict) else flat[name]
    return out


def from_runtime(text: str, runtime: dict[str, str]) -> str | None:
    """German text for an English catalog value, taken from the runtime dictionary."""
    if text in runtime and not VAR.search(text):
        return runtime[text]
    if RICH.search(text):
        return None
    names = VAR.findall(text)
    if not names:
        return None
    counter = iter(range(len(names)))
    key = VAR.sub(lambda _m: "{%d}" % next(counter), text)
    german = runtime.get(key)
    if german is None:
        return None
    out = re.sub(r"\{(\d+)\}", lambda m: "{{%s}}" % names[int(m.group(1))], german)
    return out if set(VAR.findall(out)) == set(names) else None


def same_as_english(text: str) -> bool:
    """Names and codes that stay as they are (Plex, IMDb, ZIP, 4K, …)."""
    words = re.findall(r"[A-Za-z]+", RICH.sub("", VAR.sub("", text)))
    return not words or all(w[0].isupper() and len(words) <= 2 and not w.islower() for w in words) and len(text) <= 24


def load(lang: str) -> dict[str, dict]:
    folder = LOCALES / lang
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))}


def save(lang: str, trees: dict[str, dict]) -> None:
    folder = LOCALES / lang
    folder.mkdir(exist_ok=True)
    for name, tree in trees.items():
        (folder / f"{name}.json").write_text(json.dumps(tree, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--apply", metavar="FILE")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    english = load("en")
    german = {name: flatten(tree) for name, tree in load(LANG).items()} if (LOCALES / LANG).exists() else {}
    runtime = locale_file.load(LANG)
    extra = json.loads(Path(args.apply).read_text(encoding="utf-8")) if args.apply else {}

    open_keys: dict[str, str] = {}
    out: dict[str, dict] = {}
    for name, tree in english.items():
        flat_en = flatten(tree)
        flat_de = german.get(name, {})
        merged: dict[str, str] = {}
        for key, text in flat_en.items():
            kept = flat_de.get(key)
            if kept == text:  # English placeholder from an earlier run, still open
                kept = None
            value = extra.get(key) or kept or from_runtime(text, runtime)
            if value is None and same_as_english(text):
                value = text
            if value is None:
                open_keys[key] = text
                value = text  # English until translated, so the catalog stays complete
            merged[key] = value
        out[name] = rebuild(tree, merged)
    save(LANG, out)

    if args.json:
        print(json.dumps(open_keys, ensure_ascii=False, indent=1))
    else:
        for key, text in open_keys.items():
            print(f"{key}\t{text}")
    print(f"{len(open_keys)} open of {sum(len(flatten(t)) for t in english.values())}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
