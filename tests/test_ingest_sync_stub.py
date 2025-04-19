import os
import sys
import subprocess
from pathlib import Path

import pytest

from smartdeck.vault.db import Vault
from smartdeck.ingest.apkg import ingest_apkg
from smartdeck.ingest.live import ingest_live


def test_ingest_apkg_stub_only_registers_source(tmp_path):
    db = tmp_path / "vault.db"
    vault = Vault(db)
    apkg = tmp_path / "deck.apkg"
    apkg.write_bytes(b"")  # empty file

    ingest_apkg(apkg, lang="en", vault=vault, top=10)

    # should have one source row, but no words imported
    with vault._conn() as con:
        src = con.execute("SELECT kind, ident FROM sources").fetchone()
        assert src["kind"] == "deck"
        assert src["ident"] == str(apkg)
        word_count = con.execute("SELECT COUNT(*) FROM known_words").fetchone()[0]
        assert word_count == 0


def test_ingest_live_stub_only_registers_source(tmp_path):
    db = tmp_path / "vault2.db"
    vault = Vault(db)

    live_name = "MyLiveDeck"
    ingest_live(live_name, lang="en", vault=vault)

    with vault._conn() as con:
        src = con.execute("SELECT kind, ident FROM sources").fetchone()
        assert src["kind"] == "deck"
        assert src["ident"] == live_name
        # still no known_words
        cnt = con.execute("SELECT COUNT(*) FROM known_words").fetchone()[0]
        assert cnt == 0


def test_cli_sync_add_apkg_file_not_found(tmp_path):
    db = tmp_path / "vault.db"
    env = {**os.environ, "SMARTDECK_DB": str(db)}

    # point at a non-existent file
    cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "sync", "add", "apkg", str(tmp_path / "no_such.apkg"),
        "--lang", "en",
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "file not found" in result.stderr.lower()


def test_cli_sync_remove_missing_source_is_noop(tmp_path):
    db = tmp_path / "vault.db"
    env = {**os.environ, "SMARTDECK_DB": str(db)}

    # removing something never added should still exit 0
    cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "sync", "remove", "apkg", str(tmp_path / "whatever.apkg"),
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert result.returncode == 0

    # DB is still empty
    vault = Vault(db)
    with vault._conn() as con:
        assert con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM known_words").fetchone()[0] == 0

