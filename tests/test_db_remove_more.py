# tests/test_db_remove_more.py

import sqlite3
import pytest
from collections import Counter
from smartdeck.vault.db import Vault

def make_vault(tmp_path):
    """Helper to create a fresh Vault backed by tmp_path/known.db"""
    db = tmp_path / "known.db"
    return Vault(db)

def test_occurrences_persistence_across_sources(tmp_path):
    """
    Occurrences for a multi‑linked word should persist until the last source is removed.
    """
    db = tmp_path / "vault2.db"
    v = Vault(db)

    occ = {"b": ("Excerpt B", "loc:1")}
    # source1 adds a,b (with occurrence for b)
    v.add_words("en", ["a", "b"], kind="deck", ident="d1", occurrences=occ)
    # source2 adds b,c (no new occurrence)
    v.add_words("en", ["b", "c"], kind="deck", ident="d2")

    # ensure the one occurrence remains
    with v._conn() as con:
        rows = con.execute("SELECT excerpt, location FROM occurrences").fetchall()
    assert rows == [(occ["b"][0], occ["b"][1])]

    # now remove first source; b is still linked to d2, so occurrence remains
    v.remove_source("deck", "d1")
    with v._conn() as con:
        rows = con.execute("SELECT excerpt, location FROM occurrences").fetchall()
    assert rows == [(occ["b"][0], occ["b"][1])]

    # finally remove second source; now b should vanish entirely
    v.remove_source("deck", "d2")
    with v._conn() as con:
        rows = con.execute("SELECT * FROM occurrences").fetchall()
    assert rows == []

def test_mixed_kinds_do_not_interfere(tmp_path):
    """
    Removing a 'file' source should not touch a 'deck' source with the same ident.
    """
    v = make_vault(tmp_path)

    # add under kind='file'
    v.add_words("en", ["x"], kind="file", ident="id1")
    # add under kind='deck'
    v.add_words("en", ["y"], kind="deck", ident="id1")

    # remove only the file‑kind source
    v.remove_source("file", "id1")

    # x should be gone, but y remains
    with v._conn() as con:
        remaining = {r["lemma"] for r in con.execute("SELECT lemma FROM known_words")}
    assert remaining == {"y"}

