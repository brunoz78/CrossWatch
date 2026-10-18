#!/usr/bin/env python3
"""Collect user-visible English UI strings from the CrossWatch frontend.

Scans the JavaScript under assets/ and the HTML embedded in the Python page
builders, keeps strings that look like human text and writes them as a sorted
JSON list.  Template literal placeholders (${...}) become {0}, {1}, ... so the
runtime can match them as patterns.

Usage:
    python tools/i18n/extract.py                 # write tools/i18n/strings.json
    python tools/i18n/extract.py --missing de    # list strings missing in assets/i18n/de.js
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import locale_file  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "i18n" / "strings.json"

JS_GLOBS = ["assets/**/*.js"]
PY_FILES = ["ui_frontend.py", "api/*.py", "crosswatch.py"]
SKIP_PARTS = {"i18n", "vendor", "fonts", "img", "pwa"}

ATTRS = ("title", "placeholder", "aria-label", "alt", "data-tip", "data-tooltip", "data-title", "data-label", "label")

WORD = re.compile(r"[A-Za-z]{2,}")
HTML_TEXT = re.compile(r">([^<>]+)<")
HTML_ATTR = re.compile(r"\b(?:%s)\s*=\s*(\"[^\"]*\"|'[^']*')" % "|".join(re.escape(a) for a in ATTRS))
# JS property assignments that end up in the DOM as text
JS_TEXT_PROPS = re.compile(r"\.(?:textContent|innerText|title|placeholder|ariaLabel|label)\s*=\s*$")


def _js_literals(src: str):
    """Yield (kind, value, prefix) for every JS string literal in src."""
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "'\"`":
            start = i
            i += 1
            buf, parts, depth = [], [], 0
            while i < n:
                ch = src[i]
                if ch == "\\" and i + 1 < n:
                    buf.append(src[i:i + 2])
                    i += 2
                    continue
                if c == "`" and ch == "$" and i + 1 < n and src[i + 1] == "{":
                    # keep a placeholder and scan the expression for its own literals
                    end = _expr_end(src, i + 2)
                    yield from _js_literals(src[i + 2:end])
                    buf.append("\x00")
                    i = end + 1
                    continue
                if ch == c:
                    break
                if ch == "\n" and c != "`":
                    break
                buf.append(ch)
                i += 1
            yield c, "".join(buf), src[max(0, start - 40):start]
            i += 1
            continue
        i += 1


def _expr_end(src: str, i: int) -> int:
    """Index of the "}" closing a ${...} expression that starts at i."""
    n, depth = len(src), 1
    while i < n:
        ch = src[i]
        if ch in "'\"":
            i += 1
            while i < n and src[i] != ch and src[i] != "\n":
                i += 2 if src[i] == "\\" else 1
        elif ch == "`":
            i += 1
            while i < n and src[i] != "`":
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                    i = _expr_end(src, i + 2)
                i += 1
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n


def _unescape_js(s: str) -> str:
    return re.sub(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", lambda m: _esc(m.group(1)), s)


def _esc(e: str) -> str:
    if e[0] == "u":
        return chr(int(e[1:], 16))
    if e[0] == "x":
        return chr(int(e[1:], 16))
    return {"n": "\n", "t": "\t", "r": ""}.get(e, e)


def normalize(s: str) -> str:
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def looks_human(s: str) -> bool:
    if not s or len(s) > 400 or not WORD.search(s):
        return False
    if s.startswith(("http://", "https://", "/api/", "/assets/", "data:", "#", ".", "--", "[", "]", ")", "<")):
        return False
    if '="' in s or "='" in s or re.match(r"\((?:max|min)-width|\((?:pointer|display-mode|prefers-)", s):
        return False  # attribute markup, media queries
    if re.fullmatch(r"(?:[a-z]+-[\w-]+|is-[\w-]+)(?: [\w-]+)*", s):
        return False  # class lists
    if re.search(r"[{};]\s*$", s) and ":" in s:  # css
        return False
    if re.fullmatch(r"[\w.\-/:#\[\]=\"'()>*,+~^$|@!]+", s) and " " not in s:
        # single token: keep only capitalised words such as "Save" or "Plex"
        return bool(re.fullmatch(r"(?:[A-Z][a-z]+(?:[A-Z][a-z]+)?|[A-Z]{3,})[.!?:…]?", s)) and len(s) > 2
    if re.search(r"\b(?:function|return|const|let|var|=>|querySelector|document\.|window\.)\b", s):
        return False
    if re.search(r"(?:^|\s)[.#][a-z][\w-]*(?:\s|$)", s) and not re.search(r"[A-Z][a-z]+ [a-z]+", s):
        return False  # selector list
    letters = sum(ch.isalpha() for ch in s)
    if letters < len(s) * 0.4:
        return False
    if re.fullmatch(r"[a-z0-9_\-]+(?: [a-z0-9_\-]+)*", s) and not re.search(r"\b(?:the|to|of|and|or|is|no|not|a|an|for|in|on|with|your|this|from)\b", s):
        return False  # class lists, keywords
    return True


def _with_placeholders(s: str) -> str:
    k = 0
    out = []
    for part in s.split("\x00"):
        out.append(part)
        out.append("\x00")
    out.pop()
    res = []
    for p in out:
        if p == "\x00":
            res.append("{%d}" % k)
            k += 1
        else:
            res.append(p)
    return "".join(res)


def _from_markup(s: str, found: set[str]) -> None:
    for m in HTML_TEXT.finditer(s):
        _add(m.group(1), found)
    for m in HTML_ATTR.finditer(s):
        _add(m.group(1)[1:-1], found)


def _add(raw: str, found: set[str]) -> None:
    raw = raw.replace("\x00", "{x}")
    # split at placeholders that stand alone so "{x} items" stays a pattern
    text = normalize(raw)
    if "{x}" in text:
        k = 0

        def sub(_m):
            nonlocal k
            k += 1
            return "{%d}" % (k - 1)

        text = re.sub(r"\{x\}", sub, text)
        if re.fullmatch(r"(?:\{\d+\}\W*)+", text):
            return
    if looks_human(re.sub(r"\{\d+\}", "", text)):
        found.add(text)


def scan_js(path: Path, found: set[str]) -> None:
    _scan_js_source(path.read_text(encoding="utf-8", errors="replace"), found)


def _scan_js_source(src: str, found: set[str]) -> None:
    for kind, val, prefix in _js_literals(src):
        if re.search(r"console\.\w+\(\s*$|import\s*\(?\s*$|from\s*$|require\(\s*$|querySelector(?:All)?\(\s*$|getElementById\(\s*$|classList\.\w+\(\s*$|addEventListener\(\s*$|dataset\.\w+\s*={1,3}\s*$", prefix):
            continue
        val = _unescape_js(val)
        if "<" in val and ">" in val:
            # markup: take text between tags and selected attributes
            wrapped = ">" + val + "<"
            _from_markup(wrapped, found)
            continue
        _add(val, found)


def scan_py(path: Path, found: set[str]) -> None:
    src = path.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'(?s)("""|\'\'\')(.*?)\1', src):
        block = m.group(2)
        if "<" not in block:
            continue
        for script in re.findall(r"(?s)<script\b[^>]*>(.*?)</script>", block):
            _scan_js_source(script, found)
        block = re.sub(r"(?s)<script\b.*?</script>|<style\b.*?</style>", "", block)
        block = re.sub(r"\{[^{}<>]*\}", "\x00", block)  # f-string expressions
        _from_markup(block, found)


def collect() -> list[str]:
    found: set[str] = set()
    for pattern in JS_GLOBS:
        for p in sorted(ROOT.glob(pattern)):
            if SKIP_PARTS & set(p.relative_to(ROOT).parts[1:-1]):
                continue
            scan_js(p, found)
    for pattern in PY_FILES:
        for p in sorted(ROOT.glob(pattern)):
            scan_py(p, found)
    return sorted(found, key=lambda s: (s.lower(), s))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--missing", metavar="LANG", help="print strings missing in assets/i18n/LANG.json")
    ap.add_argument("--json", action="store_true", help="with --missing: print JSON list")
    args = ap.parse_args()
    strings = collect()
    if args.missing:
        sys.stdout.reconfigure(encoding="utf-8")
        have = locale_file.load(args.missing)
        ignore = set(json.loads((ROOT / "tools" / "i18n" / "ignore.json").read_text(encoding="utf-8"))) if (ROOT / "tools" / "i18n" / "ignore.json").exists() else set()
        missing = [s for s in strings if s not in have and s not in ignore]
        if args.json:
            print(json.dumps(missing, ensure_ascii=False, indent=1))
        else:
            print("\n".join(missing))
        print(f"{len(missing)} missing of {len(strings)}", file=sys.stderr)
        return 0
    OUT.write_text(json.dumps(strings, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(strings)} strings -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
