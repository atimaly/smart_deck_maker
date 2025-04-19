# tests/test_ingest_apkg_and_sync.py

import os
import sys
import subprocess
from pathlib import Path

import pytest
from smartdeck.vault.db import Vault

# make_test_apkg is the fixture from test_cli_sync_apkg_remove.py
# It builds a minimal .apkg whose *first* field is the given word or list of words.

@pytest.mark.parametrize("words", [
    ["apple"],
    ["Banane"],                    # uppercase should be lowercased
    ["laufen", "Haus", "Auto"],    # multiple cards
])
def test_sync_add_then_remove_roundtrip(tmp_path, make_test_apkg, words):
    apkg = tmp_path / "deck.apkg"
    # accept both single‑string and list
    make_test_apkg(apkg, word=words if isinstance(words, list) else words)

    db = tmp_path / "vault.db"
    env = {**os.environ, "SMARTDECK_DB": str(db)}

    # 1) initially, coverage for these words is 0%
    v0 = Vault(db)
    cov0, unk0, _ = v0.coverage("en", words)
    assert cov0 == 0.0
    assert set(w.lower() for w in words) & set(unk0) == set(w.lower() for w in words)

    # 2) ingest via CLI
    add_cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "sync", "add", "apkg", str(apkg),
        "--lang", "en",
    ]
    r1 = subprocess.run(add_cmd, env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr

    # idempotency: running it again should still succeed and not duplicate
    r1b = subprocess.run(add_cmd, env=env, capture_output=True, text=True)
    assert r1b.returncode == 0, r1b.stderr

    # now coverage should be 100%
    v1 = Vault(db)
    cov1, unk1, _ = v1.coverage("en", words)
    assert cov1 == pytest.approx(1.0)
    assert not any(w.lower() in unk1 for w in words)

    # 3) remove
    rm_cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "sync", "remove", "apkg", str(apkg),
    ]
    r2 = subprocess.run(rm_cmd, env=env, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr

    # now coverage should be back to 0%
    v2 = Vault(db)
    cov2, unk2, _ = v2.coverage("en", words)
    assert cov2 == 0.0
    assert set(w.lower() for w in words) & set(unk2) == set(w.lower() for w in words)

    # 4) removing again is a no‑op (still succeeds, no crash)
    r3 = subprocess.run(rm_cmd, env=env, capture_output=True, text=True)
    assert r3.returncode == 0


def test_sync_add_respects_top_limit(tmp_path, make_test_apkg):
    # create an apkg with 5 distinct words
    words = ["one", "two", "three", "four", "five"]
    apkg = tmp_path / "deck.apkg"
    make_test_apkg(apkg, word=words)

    db = tmp_path / "vault.db"
    env = {**os.environ, "SMARTDECK_DB": str(db)}

    # ingest with --top=3: only first 3 cards should be recorded
    add_cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "sync", "add", "apkg", str(apkg),
        "--lang", "en",
        "--top", "3",
    ]
    r = subprocess.run(add_cmd, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    v = Vault(db)
    cov, unk, _ = v.coverage("en", words)
    # since only 3 of the words were added, coverage = 3/5
    assert cov == pytest.approx(3/5)
    # only those first 3 appear as known
    known = set(words[:3])
    assert not any(w in unk for w in words[:3])
    assert all(w in unk for w in words[3:])


def test_remove_nonexistent_source_is_noop(tmp_path):
    db = tmp_path / "vault.db"
    v = Vault(db)
    # no sources at all yet
    v.remove_source("apkg", "does-not-exist")
    # still empty
    with v._conn() as con:
        assert con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM known_words").fetchone()[0] == 0


def test_sync_live_stub_registers_source(tmp_path):
    # ingest_live is a stub: it only registers the source
    db = tmp_path / "vault.db"
    env = {**os.environ, "SMARTDECK_DB": str(db)}

    live_name = "MyLiveDeck"
    cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "sync", "add", "live", live_name,
        "--lang", "en",
    ]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert r.returncode == 0

    # the vault.sources table should have a row for kind=live, ident=live_name
    with Vault(db)._conn() as con:
        row = con.execute(
            "SELECT kind, ident FROM sources"
        ).fetchone()
    assert row["kind"] == "live"
    assert row["ident"] == live_name

    # and removing it cleans up
    rm = subprocess.run(
        [
            sys.executable, "-m", "smartdeck.cli",
            "sync", "remove", "live", live_name,
        ],
        env=env, capture_output=True, text=True
    )
    assert rm.returncode == 0
    with Vault(db)._conn() as con:
        assert con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0

