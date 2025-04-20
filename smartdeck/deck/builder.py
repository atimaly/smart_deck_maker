# smartdeck/deck/builder.py

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
    templates=[
        {
            # forward card: show the word + excerpt, answer is translation etc.
            "name": "Card 1 (→ Translation)",
            "qfmt": """
                <div style="text-align:center; font-size:24px;"><strong>{{Word}}</strong></div>
                <div style="margin-top:1em; font-style:italic;">{{Excerpt}}</div>
            """,
            "afmt": """
                {{FrontSide}}
                <hr id="answer">
                <div style="text-align:center;"><strong>Translation:</strong> {{Translation}}</div>
                <div style="text-align:center;"><strong>IPA:</strong> {{IPA}}</div>
                <div style="text-align:center;"><strong>POS:</strong> {{POS}}</div>
                <div style="margin-top:1em;"><strong>Sentence Translation:</strong> {{SentenceTranslation}}</div>
            """,
        },
        {
            # reverse card: show the translation + sentence translation, answer is the original word
            "name": "Card 2 (→ Word)",
            "qfmt": """
                <div style="text-align:center; font-size:24px;"><strong>{{Translation}}</strong></div>
                <div style="margin-top:1em; font-style:italic;">{{SentenceTranslation}}</div>
            """,
            "afmt": """
                {{FrontSide}}
                <hr id="answer">
                <div style="text-align:center;"><strong>Word:</strong> {{Word}}</div>
                <div style="text-align:center;"><strong>IPA:</strong> {{IPA}}</div>
                <div style="text-align:center;"><strong>POS:</strong> {{POS}}</div>
                <div style="margin-top:1em;"><strong>Context:</strong> {{Excerpt}}</div>
            """,
        },
    ],
    css="""
        /* center everything and improve contrast */
        .card {
          font-family: Arial;
          text-align: center;
          color: #333;
          background-color: #f7f7f7;
        }
        .card div {
          margin: 0.5em 0;
        }
        .h { /* you removed yellow highlighting entirely; if you want another color, adjust here */ }
    """,
)

# an entry may be:
#  - 7‑tuple: (lemma, translation, ipa, pos, excerpt, sent_trans, location)
#  - 5‑tuple: (lemma, translation, pos, excerpt, location)
#  - 4‑tuple: (lemma, pos, excerpt, location)
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

        # highlight lemma in excerpt (if you want no highlighting, just use excerpt directly)
        highlighted = excerpt.replace(lemma, f"<strong>{lemma}</strong>")
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

