from typing import Optional
from smartdeck.vault.db import Vault

__all__ = ["ingest_live"]


def ingest_live(
    deck_name: str,
    lang: str,
    vault: Optional[Vault] = None,
) -> None:
    """
    Stub: register a live Anki deck source without fetching cards.
    """
    vault = vault or Vault()

    # stub-only import registers as deck
    kind = "deck"
    ident = deck_name
    vault._get_or_add_source(kind, ident)

    # future AnkiConnect logic goes here
    print(f"Registered stub deck source '{deck_name}'.")

