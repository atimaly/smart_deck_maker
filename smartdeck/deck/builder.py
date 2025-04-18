# smartdeck/deck/builder.py

from typing import Sequence, Tuple
import genanki

# static IDs—change if you need uniqueness
_MODEL_ID = 1607392319
_DECK_ID = 2059400110

_MODEL = genanki.Model(
    model_id=_MODEL_ID,
    name="SmartDeckModel",
    fields=[
        {"name": "Word"},
        {"name": "IPA"},
        {"name": "Grammar"},
        {"name": "Excerpt"},
    ],
    templates=[{
        "name": "Card 1",
        "qfmt": """<div>{{Word}}</div><div>{{Excerpt}}</div>""",
        "afmt": """
            {{FrontSide}}
            <hr id="answer">
            <div><strong>IPA:</strong> {{IPA}}</div>
            <div><strong>POS:</strong> {{Grammar}}</div>
        """,
    }],
    css="""
        .h { background-color: #ffeb3b; }
        body { font-family: Arial; }
    """,
)

def build_deck(
    deck_name: str,
    entries: Sequence[Tuple[str, str, str, str]],
    output_file: str,
) -> None:
    """
    entries: list of (lemma, pos, excerpt, location)
    Writes an Anki .apkg to output_file.
    """
    deck = genanki.Deck(deck_id=_DECK_ID, name=deck_name)
    for lemma, pos, excerpt, loc in entries:
        # highlight lemma in excerpt
        highlighted = excerpt.replace(
            lemma, f'<span class="h">{lemma}</span>'
        )
        field_excerpt = f"{highlighted} <small>({loc})</small>"
        note = genanki.Note(
            model=_MODEL,
            fields=[lemma, "", pos, field_excerpt],
        )
        deck.add_note(note)
    genanki.Package(deck).write_to_file(output_file)

