from typing import Sequence, Union
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
        {"name": "POS"},
        {"name": "Excerpt"},
        {"name": "SentenceTranslation"},
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
            <div><strong>POS:</strong> {{POS}}</div>
            <div><strong>Sentence Translation:</strong> {{SentenceTranslation}}</div>
        """,
    }],
    css="""
        .h { background-color: #ffeb3b; }
        body { font-family: Arial; line-height: 1.4; }
        div { margin-bottom: 0.5em; }
    """,
)

# An entry may be:
#  - 7‑tuple: (lemma, translation, ipa, pos, excerpt, sent_trans, loc)
#  - 5‑tuple: (lemma, translation, pos, excerpt, loc)
#  - 4‑tuple: (lemma, pos, excerpt, loc)
Entry = Union[
    tuple[str, str, str, str, str, str, str],
    tuple[str, str, str, str, str],
    tuple[str, str, str, str],
]

def build_deck(
    deck_name: str,
    entries: Sequence[Entry],
    output_file: str,
) -> None:
    """
    entries:
      - (lemma, translation, ipa, pos, excerpt, sent_trans, location), or
      - (lemma, translation, pos, excerpt, location), or
      - (lemma, pos, excerpt, location)
    """
    deck = genanki.Deck(deck_id=_DECK_ID, name=deck_name)
    for entry in entries:
        L = len(entry)
        if L == 7:
            lemma, translation, ipa, pos, excerpt, sent_trans, loc = entry
        elif L == 5:
            lemma, translation, pos, excerpt, loc = entry
            ipa = sent_trans = ""
        elif L == 4:
            lemma, pos, excerpt, loc = entry
            translation = ipa = sent_trans = ""
        else:
            raise ValueError(f"Expected 4,5 or 7 elements, got {L}")

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
                ipa,
                pos,
                field_excerpt,
                sent_trans,
            ],
        )
        deck.add_note(note)

    genanki.Package(deck).write_to_file(output_file)

