import os
import subprocess
import sys
from pathlib import Path

import genanki
import pytest

from smartdeck.vault.db import Vault

# --- helpers to build a minimal .apkg ---
def make_test_apkg(path: Path, word: str = "foobar") -> None:
    """
    Create a one‑note Anki deck with a single field containing `word`,
    and write it to `path`.
    """
    model = genanki.Model(
        1607392319,
        "Simple Model",
        fields=[{"name": "Word"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Word}}",
                "afmt": "{{FrontSide}}",
            }
        ],
    )
    deck = genanki.Deck(2059400110, "TestDeck")
    note = genanki.Note(model=model, fields=[word])
    deck.add_note(note)
    genanki.Package(deck).write_to_file(str(path))


@pytest.mark.parametrize("word", ["apple", "Banane", "laufen"])
def test_sync_add_then_remove_apkg(tmp_path: Path, monkeypatch, word: str):
    """
    1) build a tiny .apkg containing `word`
    2) ensure vault reports it UNKNOWN
    3) run `smartdeck sync add apkg` → vault covers it
    4) run `smartdeck sync remove apkg` → vault again reports it UNKNOWN
    """
    # 1) make .apkg and isolated DB
    apkg_path = tmp_path / "deck.apkg"
    make_test_apkg(apkg_path, word=word)

    db_path = tmp_path / "vault.db"
    # point SMARTDECK_DB at our temp DB
    env = {**os.environ, "SMARTDECK_DB": str(db_path)}

    # 2) vault should start with 0% coverage on our single word
    v = Vault(db_path)
    cov0, unknowns0, _ = v.coverage("en", [word])
    assert cov0 == 0.0
    assert word in unknowns0

    # 3) ingest via CLI: add the .apkg
    add_cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "sync", "add", "apkg", str(apkg_path),
        "--lang", "en",
    ]
    r = subprocess.run(add_cmd, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    # now coverage should be 100%
    v2 = Vault(db_path)
    cov1, unknowns1, _ = v2.coverage("en", [word])
    assert cov1 == pytest.approx(1.0)
    assert not unknowns1

    # 4) remove via CLI
    rem_cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "sync", "remove", "apkg", str(apkg_path),
    ]
    r2 = subprocess.run(rem_cmd, env=env, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr

    # coverage back to 0%
    v3 = Vault(db_path)
    cov2, unknowns2, _ = v3.coverage("en", [word])
    assert cov2 == pytest.approx(0.0)
    assert word in unknowns2

