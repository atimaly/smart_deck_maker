# conftest.py

import pytest
import genanki
import os
from pathlib import Path


@pytest.fixture(autouse=True, scope="session")
def use_temp_vault(tmp_path_factory):
    # before any tests run...
    db = tmp_path_factory.mktemp("vault") / "known.db"
    os.environ["SMARTDECK_DB"] = str(db)
    yield
    # afterwards you can inspect or just throw away db


@pytest.fixture
def make_test_apkg(tmp_path):
    """
    Create a minimal .apkg at the given Path containing one or more
    cards whose front field is each word (back empty).
    Usage:
        make_test_apkg(path, word=<str> or list[str])
    """
    def _make(path: Path, *, word):
        words = word if isinstance(word, (list, tuple)) else [word]
        model = genanki.Model(
            1607392319,
            "Simple Model",
            fields=[{"name": "Front"}, {"name": "Back"}],
            templates=[
                {
                    "name": "Card 1",
                    "qfmt": "{{Front}}",
                    "afmt": "{{Front}}<hr id='answer'>{{Back}}",
                }
            ],
        )
        deck = genanki.Deck(2059400110, name="Test Deck")
        for w in words:
            deck.add_note(genanki.Note(model=model, fields=[w, ""]))
        genanki.Package(deck).write_to_file(str(path))

    return _make

