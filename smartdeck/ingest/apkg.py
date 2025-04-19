import sqlite3
import tempfile
import zipfile
from pathlib import Path
from zipfile import ZipFile

from smartdeck.vault.db import Vault

__all__ = ['ingest_apkg']


def ingest_apkg(
    path: Path,
    lang: str,
    vault: Vault | None = None,
    top: int | None = None,
) -> None:
    """
    Ingest an Anki .apkg file offline and register its words in the vault.
    """
    vault = vault or Vault()
    kind = "deck"
    ident = str(path)

    # attempt to unzip; on failure, register stub source only
    try:
        with ZipFile(path, 'r') as z:
            tmpdir = tempfile.mkdtemp()
            z.extract('collection.anki2', tmpdir)
            coll_db = Path(tmpdir) / 'collection.anki2'
    except (zipfile.BadZipFile, KeyError):
        vault._get_or_add_source(kind, ident)
        return

    # read note fields
    conn = sqlite3.connect(coll_db)
    rows = conn.execute("SELECT flds FROM notes").fetchall()
    conn.close()

    # extract first field, lowercase
    lemmas = [flds.split("\x1f", 1)[0].lower() for (flds,) in rows]

    # apply --top limit
    if top is not None:
        lemmas = lemmas[:top]

    vault.add_words(lang, lemmas, kind=kind, ident=ident)

