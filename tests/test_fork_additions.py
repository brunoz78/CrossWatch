# Tests for the additions of this fork (see FORK.md).
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("CONFIG_BASE", str(tmp_path))
    from fastapi.testclient import TestClient
    import crosswatch

    return TestClient(crosswatch.app)


def test_server_url_guard_blocks_metadata_but_allows_lan():
    from cw_platform.url_validation import config_server_url_error

    assert config_server_url_error({"plex": {"server_url": "http://169.254.169.254/"}})
    assert config_server_url_error({"jellyfin": {"instances": {"j2": {"server": "http://[fe80::1]:8096"}}}})
    assert config_server_url_error({"plex": {"server_url": "http://10.0.1.13:32400"}, "jellyfin": {"server": "http://jellyfin.lan:8096"}}) is None


def test_setup_link_is_required_for_the_first_account(client, monkeypatch, tmp_path):
    import setup_guard

    monkeypatch.setattr(setup_guard, "setup_token_path", lambda: tmp_path / ".setup_token")
    token = setup_guard.ensure_setup_token()
    body = {"enabled": True, "username": "admin", "password": "pw-test-12345", "password2": "pw-test-12345"}

    r = client.post("/api/app-auth/credentials", json=body)
    assert r.status_code == 403

    r = client.get("/?setup=wrong", follow_redirects=False)
    assert r.status_code == 302 and "Max-Age=0" in r.headers["set-cookie"]

    r = client.get(f"/?setup={token}", follow_redirects=False)
    assert r.status_code == 302 and "cw_setup=" in r.headers["set-cookie"]

    r = client.post("/api/app-auth/credentials", json=body)
    assert r.status_code == 200
    assert not (tmp_path / ".setup_token").exists()


def test_pages_load_the_translator(client):
    r = client.get("/", headers={"accept-language": "de-CH,de;q=0.9"})
    assert '/assets/i18n/de.js' in r.text and '/assets/i18n/i18n.js' in r.text and 'lang="de"' in r.text
    r = client.get("/", headers={"accept-language": "en", "cookie": "cw_lang=en"})
    assert '/assets/i18n/de.js' not in r.text and '/assets/i18n/i18n.js' in r.text


def test_update_button_needs_the_systemd_updater(monkeypatch):
    import fork_update

    monkeypatch.delenv("CW_UPDATER", raising=False)
    assert fork_update._supported() is False
    monkeypatch.setenv("CW_UPDATER", "systemd")
    assert fork_update._supported() is True
    assert any(getattr(r, "path", "") == "/api/fork/update" for r in fork_update.router.routes)


def test_german_dictionary_is_complete_and_valid():
    sys.path.insert(0, str(ROOT / "tools" / "i18n"))
    import extract
    import locale_file

    strings = locale_file.load("de")
    ignore = set(json.loads((ROOT / "tools" / "i18n" / "ignore.json").read_text(encoding="utf-8")))
    missing = [s for s in extract.collect() if s not in strings and s not in ignore]
    assert not missing, missing[:20]
    bad = {k: v for k, v in strings.items() if locale_file.problems(k, v)}
    assert not bad, list(bad.items())[:5]
