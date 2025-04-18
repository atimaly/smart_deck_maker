"""SQLite‑backed known‑word vault."""
from __future__ import annotations

import sqlite3
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Literal, Tuple

# Default database location
_VAULT_PATH = Path("~/.smartdeck/known.db").expanduser()
_VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)

CoverageTier = Literal["EASY", "ADEQUATE", "CHALLENGING", "FRUSTRATING"]


class Vault:
    """Track which words a user already knows and where they came from."""

    # ------------------------------------------------------------------ setup
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path: Path = db_path or _VAULT_PATH
        self._ensure_schema()

    @contextmanager
    def _conn(self):
        """Yield a SQLite connection that auto‑commits and closes."""
        con = sqlite3.connect(self.db_path)
        try:
            con.row_factory = sqlite3.Row
            yield con
            con.commit()
        finally:
            con.close()

    def _ensure_schema(self) -> None:
        """Create tables the first time the DB is opened."""
        with self._conn() as con:
            con.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS sources (
                    id     INTEGER PRIMARY KEY,
                    kind   TEXT NOT NULL,   -- 'deck' or 'file'
                    ident  TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS known_words (
                    id     INTEGER PRIMARY KEY,
                    lang   TEXT NOT NULL,
                    lemma  TEXT NOT NULL,
                    UNIQUE (lang, lemma)
                );

                CREATE TABLE IF NOT EXISTS word_sources (
                    word_id INTEGER REFERENCES known_words(id) ON DELETE CASCADE,
                    src_id  INTEGER REFERENCES sources(id)     ON DELETE CASCADE,
                    PRIMARY KEY (word_id, src_id)
                );

                CREATE TABLE IF NOT EXISTS occurrences (
                    -- first time we saw the word in a text
                    word_id  INTEGER PRIMARY KEY
                             REFERENCES known_words(id) ON DELETE CASCADE,
                    excerpt  TEXT,
                    location TEXT
                );
                """
            )

    # ---------------------------------------------------------------- sources
    def _get_or_add_source(self, kind: str, ident: str) -> int:
        """Return the row‑id for (kind, ident), inserting if needed."""
        with self._conn() as con:
            cur = con.execute("SELECT id FROM sources WHERE ident = ?", (ident,))
            if row := cur.fetchone():
                return int(row["id"])
            cur = con.execute(
                "INSERT INTO sources(kind, ident) VALUES(?, ?)", (kind, ident)
            )
            return int(cur.lastrowid)

    def remove_source(self, kind: str, ident: str) -> None:
        """Delete one deck/file and any words that are now orphaned."""
        with self._conn() as con:
            cur = con.execute(
                "SELECT id FROM sources WHERE kind=? AND ident=?", (kind, ident)
            )
            if not (row := cur.fetchone()):
                return
            src_id = int(row["id"])
            con.execute("DELETE FROM word_sources WHERE src_id=?", (src_id,))
            # any word with zero remaining links vanishes
            con.execute(
                "DELETE FROM known_words "
                "WHERE id NOT IN (SELECT word_id FROM word_sources)"
            )
            con.execute("DELETE FROM sources WHERE id=?", (src_id,))

    # ---------------------------------------------------------------- add words
    def add_words(
        self,
        lang: str,
        lemmas: Iterable[str],
        kind: str,
        ident: str,
        occurrences: dict[str, Tuple[str, str]] | None = None,
    ) -> None:
        """Store new lemmas and link them to *ident* (file/deck)."""
        src_id = self._get_or_add_source(kind, ident)
        with self._conn() as con:
            for lemma in lemmas:
                con.execute(
                    "INSERT OR IGNORE INTO known_words(lang, lemma) VALUES(?, ?)",
                    (lang, lemma),
                )
                word_id = con.execute(
                    "SELECT id FROM known_words WHERE lang=? AND lemma=?",
                    (lang, lemma),
                ).fetchone()["id"]
                con.execute(
                    "INSERT OR IGNORE INTO word_sources(word_id, src_id) "
                    "VALUES(?, ?)",
                    (word_id, src_id),
                )
                if occurrences and lemma in occurrences:
                    excerpt, loc = occurrences[lemma]
                    con.execute(
                        "INSERT OR IGNORE INTO occurrences(word_id, excerpt, location) "
                        "VALUES(?, ?, ?)",
                        (word_id, excerpt, loc),
                    )

    # ---------------------------------------------------------------- coverage
    def coverage(
        self, lang: str, lemmas: Iterable[str]
    ) -> tuple[float, Counter[str], CoverageTier]:
        """Return coverage %, unknown Counter, and tier."""
        words = list(lemmas)
        with self._conn() as con:
            known = {
                r["lemma"]
                for r in con.execute(
                    "SELECT lemma FROM known_words WHERE lang=?", (lang,)
                )
            }

        unknown = [w for w in words if w not in known]
        cov = 1.0 - len(unknown) / max(1, len(words))

        if cov >= 0.98:
            tier: CoverageTier = "EASY"
        elif cov >= 0.95:
            tier = "ADEQUATE"
        elif cov >= 0.90:
            tier = "CHALLENGING"
        else:
            tier = "FRUSTRATING"

        return cov, Counter(unknown), tier

