# setup_guard.py
# CrossWatch - one-time setup link for the first sign-in (fork addition)
#
# Before any credentials exist, POST /api/app-auth/credentials is open by design,
# so whoever reaches a fresh instance first could claim it. This guard requires a
# one-time token: it is written to <config>/.setup_token (mode 600) and printed
# to the log as a link (/?setup=<token>). Opening that link stores the token in a
# cookie; only a browser holding it can create the first credentials. The token
# is removed after a successful setup and created again when sign-in is reset.
from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
from pathlib import Path
from urllib.parse import parse_qs

from starlette.middleware import Middleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = ["install_setup_guard", "setup_token_path", "ensure_setup_token"]

_LOG = logging.getLogger("crosswatch.setup_guard")
_COOKIE = "cw_setup"
_CREDENTIALS_PATH = "/api/app-auth/credentials"


def setup_token_path() -> Path:
    from cw_platform.config_base import CONFIG_BASE

    return CONFIG_BASE() / ".setup_token"


def _setup_open() -> bool:
    """True while no credentials exist yet or a sign-in reset is pending."""
    try:
        from api.appAuthAPI import credentials_configured, reset_pending
        from cw_platform.config_base import load_config

        cfg = load_config()
        return (not credentials_configured(cfg)) or reset_pending(cfg)
    except Exception:
        return False


def _read_token() -> str:
    try:
        return setup_token_path().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def ensure_setup_token() -> str:
    """Create the token file if needed and return the token."""
    token = _read_token()
    if token:
        return token
    token = secrets.token_urlsafe(24)
    path = setup_token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(token + "\n")
    port = os.getenv("WEB_PORT", "8787")
    msg = f"[SETUP] First sign-in is locked. Open http://<server>:{port}/?setup={token} to create the admin account."
    _LOG.warning(msg)
    return token


def _consume_token() -> None:
    try:
        setup_token_path().unlink()
    except OSError:
        pass


def _cookie_token(headers: dict[str, str]) -> str:
    for part in headers.get("cookie", "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == _COOKIE:
            return value.strip()
    return ""


async def _json(send: Send, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode()
    await send({"type": "http.response.start", "status": status, "headers": [
        (b"content-type", b"application/json"), (b"cache-control", b"no-store"),
        (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


class SetupGuardMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}

        # /?setup=<token>: remember the token in a cookie, then show the normal page
        if method == "GET" and path == "/":
            query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
            given = (query.get("setup") or [""])[0].strip()
            if given:
                expected = _read_token()
                ok = bool(expected) and hmac.compare_digest(given, expected)
                cookie = f"{_COOKIE}={given}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400" if ok else f"{_COOKIE}=; Path=/; Max-Age=0"
                await send({"type": "http.response.start", "status": 302, "headers": [
                    (b"location", b"/"), (b"set-cookie", cookie.encode()), (b"cache-control", b"no-store")]})
                await send({"type": "http.response.body", "body": b""})
                return

        if method == "POST" and path == _CREDENTIALS_PATH and _setup_open():
            expected = ensure_setup_token()
            given = _cookie_token(headers)
            if not given or not hmac.compare_digest(given, expected):
                await _json(send, 403, {"ok": False, "error": "Setup link required. Open the setup link from the server log."})
                return
            status = {"code": 0}

            async def _send(message: Message) -> None:
                if message["type"] == "http.response.start":
                    status["code"] = int(message.get("status") or 0)
                await send(message)

            await self.app(scope, receive, _send)
            if 200 <= status["code"] < 300 and not _setup_open():
                _consume_token()
            return

        await self.app(scope, receive, send)


def install_setup_guard(app) -> None:
    app.user_middleware.append(Middleware(SetupGuardMiddleware))
    if _setup_open():
        ensure_setup_token()
