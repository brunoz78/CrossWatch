# i18n_frontend.py
# CrossWatch - UI language support (fork addition)
#
# Injects the runtime translator (assets/i18n/i18n.js) and the dictionary of the
# chosen language into every HTML page. The language comes from the cw_lang
# cookie, otherwise from CW_UI_LANG, otherwise from the browser's
# Accept-Language header.
from __future__ import annotations

import os
import re
from pathlib import Path

from starlette.middleware import Middleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = ["install_i18n", "SUPPORTED_LANGS", "pick_language"]

SUPPORTED_LANGS = ("en", "de")
_ROOT = Path(__file__).resolve().parent
_I18N_DIR = _ROOT / "assets" / "i18n"
_COOKIE_RE = re.compile(r"(?:^|;\s*)cw_lang=([a-z]{2})")
_HEAD_RE = re.compile(rb"<head(?:\s[^>]*)?>", re.IGNORECASE)
_HTML_LANG_RE = re.compile(rb'<html([^>]*?)\slang="[a-zA-Z-]*"', re.IGNORECASE)


def _version(name: str) -> str:
    try:
        return str(int((_I18N_DIR / name).stat().st_mtime))
    except OSError:
        return "0"


def pick_language(cookie_header: str, accept_language: str) -> str:
    m = _COOKIE_RE.search(cookie_header or "")
    if m and m.group(1) in SUPPORTED_LANGS:
        return m.group(1)
    env = (os.getenv("CW_UI_LANG") or "").strip().lower()[:2]
    if env in SUPPORTED_LANGS:
        return env
    for part in (accept_language or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in SUPPORTED_LANGS:
            return code
    return "en"


def _tags(lang: str) -> bytes:
    tags = []
    if lang != "en" and (_I18N_DIR / f"{lang}.js").exists():
        tags.append(f'<script src="/assets/i18n/{lang}.js?v={_version(lang + ".js")}"></script>')
    tags.append(f'<script src="/assets/i18n/i18n.js?v={_version("i18n.js")}"></script>')
    tags.append(f'<script src="/assets/fork/update.js?v={_version("../fork/update.js")}" defer></script>')
    return "".join(tags).encode()


class I18nMiddleware:
    """Adds the translator scripts to text/html responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path", "").startswith(("/api/", "/assets/", "/webhook")):
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        lang = pick_language(headers.get("cookie", ""), headers.get("accept-language", ""))
        start: Message | None = None
        chunks: list[bytes] = []

        async def _send(message: Message) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                hdrs = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in message.get("headers") or []}
                if "text/html" in hdrs.get("content-type", "") and "content-encoding" not in hdrs:
                    start = message
                    return
                await send(message)
                return
            if message["type"] == "http.response.body" and start is not None:
                chunks.append(message.get("body", b""))
                if message.get("more_body"):
                    return
                body = _inject(b"".join(chunks), lang)
                raw = [(k, v) for k, v in start.get("headers") or [] if k.lower() != b"content-length"]
                raw.append((b"content-length", str(len(body)).encode()))
                await send({**start, "headers": raw})
                await send({"type": "http.response.body", "body": body})
                return
            await send(message)

        await self.app(scope, receive, _send)


def _inject(body: bytes, lang: str) -> bytes:
    m = _HEAD_RE.search(body)
    if not m or b"/assets/i18n/i18n.js" in body:
        return body
    body = body[: m.end()] + _tags(lang) + body[m.end():]
    return _HTML_LANG_RE.sub(lambda h: b"<html" + h.group(1) + b' lang="' + lang.encode() + b'" data-cw-lang="' + lang.encode() + b'"', body, count=1)


def install_i18n(app) -> None:
    """Register the middleware as the innermost one so it sees uncompressed HTML."""
    app.user_middleware.append(Middleware(I18nMiddleware))
