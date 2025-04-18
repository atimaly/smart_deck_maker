# tests/test_builder.py

import os
from pathlib import Path
import pytest

from smartdeck.deck.builder import build_deck

@ pytest.fixture

def tmp_apkg(tmp_path: Path):
    return str(tmp_path / "test.apkg")


def test_build_minimal_deck(tmp_apkg):
    entries = [
        ("apfel", "NOUN", "Das ist ein Apfel.", "1:1"),
        ("essen", "VERB", "Ich habe gegessen.", "1:2"),
    ]
    build_deck("TestDeck", entries, tmp_apkg)
    # File should exist and be non-empty
    assert os.path.exists(tmp_apkg), "APKG file was not created"
    assert os.path.getsize(tmp_apkg) > 0, "APKG file is empty"

