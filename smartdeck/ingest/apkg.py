# smartdeck/ingest/apkg.py

import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

# Assuming Vault class is importable like this based on your structure
from smartdeck.vault.db import Vault

__all__ = ["ingest_apkg"]


def ingest_apkg(
    path: Path,
    lang: str,
    vault: Optional[Vault] = None,
    top: Optional[int] = None,
) -> None:
    """
    Ingest words from an Anki .apkg file into the SmartDeck vault.

    Reads the 'collection.anki2' SQLite database within the .apkg,
    extracts the first field from each note, and adds these words
    to the vault with kind='apkg' and the .apkg path as the identifier.

    Args:
        path: Path to the .apkg file.
        lang: Language code for the words being added.
        vault: An optional pre-initialized Vault instance. If None, creates one.
        top: Optional limit on the number of notes (words) to process.
    """
    if not path.is_file():
        raise FileNotFoundError(f"APKG file not found: {path}")

    # Ensure we have a vault instance
    vault_instance = vault or Vault()

    # Use a temporary directory to safely extract collection.anki2
    with tempfile.TemporaryDirectory() as tmpdir:
        apkg_path = Path(tmpdir) / "collection.anki2"
        try:
            with zipfile.ZipFile(path, "r") as zf:
                # Extract the main database file
                zf.extract("collection.anki2", path=tmpdir)
        except (zipfile.BadZipFile, KeyError) as e:
            # KeyError if collection.anki2 is missing
            raise ValueError(f"Failed to extract collection.anki2 from {path}: {e}")

        # Connect to the extracted SQLite database
        conn = None
        try:
            conn = sqlite3.connect(apkg_path)
            cursor = conn.cursor()

            # Query the 'notes' table for the fields ('flds') column
            # The 'flds' column contains all fields concatenated with ASCII 0x1f
            query = "SELECT flds FROM notes"
            if top is not None:
                query += f" LIMIT {int(top)}" # Add LIMIT clause if top is specified

            cursor.execute(query)
            rows = cursor.fetchall()

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to read notes from {apkg_path}: {e}")
        finally:
            if conn:
                conn.close()

        # Process the results
        lemmas_to_add = []
        field_separator = "\x1f"  # ASCII Unit Separator

        for row in rows:
            if not row or not row[0]:
                continue # Skip empty rows or rows with no fields data

            # Split fields and take the first one
            all_fields = row[0]
            first_field = all_fields.split(field_separator, 1)[0].strip()

            if first_field: # Ensure the extracted field is not empty after stripping
                lemmas_to_add.append(first_field)

        # Add the extracted words to the vault
        if lemmas_to_add:
            # Use the absolute path string as the unique identifier for this source
            ident = str(path.resolve())
            # Kind indicates the source type
            kind = "apkg"
            # Note: We are adding the raw first field content. Lemmatization is
            # NOT applied here, matching the assumption that deck words are
            # often already in a desired form (lemma or inflected word).
            # The vault stores them as provided.
            vault_instance.add_words(
                lang=lang,
                lemmas=lemmas_to_add,
                kind=kind,
                ident=ident
                # occurrences data is not available from apkg import directly
            )
        else:
             # If no words were found, still ensure the source is recorded
             # so that `remove` works correctly even for empty/failed imports.
             ident = str(path.resolve())
             kind = "apkg"
             vault_instance._get_or_add_source(kind=kind, ident=ident)

    # No explicit return value (returns None implicitly)

