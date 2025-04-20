# smartdeck/deck/builder.py

from typing import Sequence, Tuple, Union
import genanki

# static IDs—keep these the same unless you need to force a new model/deck
_MODEL_ID = 1607392319
_DECK_ID = 2059400110

_MODEL = genanki.Model(
    model_id=_MODEL_ID,
    name="SmartDeckModel",
    fields=[
        {"name": "Word"},
        {"name": "Translation"},
        {"name": "IPA"},
        {"name": "Grammar"},
        {"name": "Excerpt"},
    ],
    templates=[{
        "name": "Card 1",
        "qfmt": """
            <div>{{Word}}</div>
            <div>{{Excerpt}}</div>
        """,
        "afmt": """
            {{FrontSide}}
            <hr id="answer">
            <div><strong>Translation:</strong> {{Translation}}</div>
            <div><strong>IPA:</strong> {{IPA}}</div>
            <div><strong>POS:</strong> {{Grammar}}</div>
        """,
    }],
    css="""
        .h { background-color: #ffeb3b; }
        body { font-family: Arial; line-height: 1.4; }
        div { margin-bottom: 0.5em; }
    """,
)

Entry = Union[
    Tuple[str, str, str, str, str],  # (lemma, translation, pos, excerpt, loc)
    Tuple[str, str, str, str],       # (lemma, pos, excerpt, loc)
]

def build_deck(
    deck_name: str,
    entries: Sequence[Entry],
    output_file: str,
) -> None:
    """
    entries: list of either
      - (lemma, translation, pos, excerpt, location), or
      - (lemma, pos, excerpt, location)  # translation will be empty
    Writes an Anki .apkg to output_file.
    """
    deck = genanki.Deck(deck_id=_DECK_ID, name=deck_name)
    for entry in entries:
        if len(entry) == 5:
            lemma, translation, pos, excerpt, loc = entry
        elif len(entry) == 4:
            lemma, pos, excerpt, loc = entry
            translation = ""
        else:
            raise ValueError(f"Expected 4 or 5 elements per entry, got {len(entry)}")

        # highlight lemma in excerpt
        highlighted = excerpt.replace(
            lemma, f'<span class="h">{lemma}</span>'
        )
        field_excerpt = f"{highlighted} <small>({loc})</small>"

        note = genanki.Note(
            model=_MODEL,
            fields=[
                lemma,
                translation,
                "",        # IPA left blank or filled in elsewhere
                pos,
                field_excerpt,
            ],
        )
        deck.add_note(note)

    genanki.Package(deck).write_to_file(output_file)

