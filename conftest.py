# conftest.py

import pytest
import genanki
from pathlib import Path

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

