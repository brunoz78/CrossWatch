# fork_update.py
# CrossWatch - update button for the native LXC installation (fork addition)
#
# The web app never runs the update itself. An admin request writes
# <config>/.update/request; a systemd path unit on the host (installed by the
# Proxmox script) notices the file and runs /usr/local/bin/crosswatch-update as
# root. That script writes <config>/.update/status.json, which the UI polls.
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

__all__ = ["router", "install_update_router"]

router = APIRouter(prefix="/api/fork", tags=["fork"])


def _update_dir() -> Path:
    from cw_platform.config_base import CONFIG_BASE

    return CONFIG_BASE() / ".update"


def _supported() -> bool:
    return os.getenv("CW_UPDATER", "").strip().lower() == "systemd"


def _status() -> dict[str, Any]:
    try:
        data = json.loads((_update_dir() / "status.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _is_admin(request: Request) -> bool:
    try:
        from api.appAuthAPI import COOKIE_NAME, auth_required, is_admin_authenticated
        from cw_platform.config_base import load_config

        cfg = load_config()
        if not auth_required(cfg):
            return True
        return bool(is_admin_authenticated(cfg, request.cookies.get(COOKIE_NAME)))
    except Exception:
        return False


@router.get("/update")
def api_update_status(request: Request) -> JSONResponse:
    pending = (_update_dir() / "request").exists()
    return JSONResponse({
        "supported": _supported(),
        "admin": _is_admin(request),
        "pending": pending,
        "status": _status(),
    }, headers={"Cache-Control": "no-store"})


@router.post("/update")
def api_update_start(request: Request) -> JSONResponse:
    if not _is_admin(request):
        return JSONResponse({"ok": False, "error": "Administrator access required."}, status_code=403)
    try:
        from api.appAuthAPI import _origin_allowed

        if not _origin_allowed(request):
            return JSONResponse({"ok": False, "error": "Origin not allowed"}, status_code=403)
    except ImportError:
        pass
    if not _supported():
        return JSONResponse({"ok": False, "error": "Updates from the web interface are not set up on this installation."}, status_code=409)
    d = _update_dir()
    d.mkdir(parents=True, exist_ok=True)
    if (d / "request").exists() or _status().get("state") == "running":
        return JSONResponse({"ok": True, "already": True})
    (d / "request").write_text(str(int(time.time())), encoding="utf-8")
    return JSONResponse({"ok": True})


def install_update_router(app) -> None:
    app.include_router(router)
