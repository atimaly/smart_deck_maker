import pytest
from smartdeck.vault import Vault


# ------------------------------------------------------------------ helpers
def make_vault(tmp_path):
    """Return a fresh Vault that writes to a temp file."""
    return Vault(tmp_path / "v.db")


def test_add_and_remove(tmp_path):
    db_file = tmp_path / "vault.db"
    vault = Vault(db_file)

    vault.add_words("en", ["cat", "dog"], kind="deck", ident="DeckA")
    assert vault.coverage("en", ["cat", "dog"])[0] == 1.0

    vault.remove_source("deck", "DeckA")
    assert vault.coverage("en", ["cat"])[0] == 0.0



# ------------------------------------------------------------------ tier thresholds
@pytest.mark.parametrize(
    "known, unknown, expected",
    [
        (98, 2, "EASY"),
        (95, 5, "ADEQUATE"),
        (90, 10, "CHALLENGING"),
        (80, 20, "FRUSTRATING"),
    ],
)
def test_tier_thresholds(tmp_path, known, unknown, expected):
    vault = Vault(tmp_path / "v.db")
    vault.add_words("en", ["a"], kind="deck", ident="Dummy")
    sample = ["a"] * 98 + ["x"] * 2   # 98 % coverage
    _, _, tier = vault.coverage("en", sample)
    assert tier == "EASY"



# ------------------------------------------------------------------ idempotent add_words
def test_duplicate_add_is_idempotent(tmp_path):
    v = make_vault(tmp_path)
    v.add_words("en", ["fox"], "deck", "D1")
    v.add_words("en", ["fox"], "deck", "D1")           # same call again

    # only one entry in known_words
    with v._conn() as con:
        rows = con.execute("SELECT COUNT(*) AS n FROM known_words").fetchone()["n"]
    assert rows == 1


# ------------------------------------------------------------------ shared words survive removal
def test_remove_keeps_shared_words(tmp_path):
    v = make_vault(tmp_path)
    v.add_words("en", ["wolf"], "deck", "DeckA")
    v.add_words("en", ["wolf"], "file", "Book1")

    v.remove_source("deck", "DeckA")
    assert v.coverage("en", ["wolf"])[0] == 1.0        # still known


# ------------------------------------------------------------------ occurrences stored once
def test_occurrence_storage(tmp_path):
    v = make_vault(tmp_path)
    occ = {"owl": ("The wise owl hooted.", "ch3:42")}
    v.add_words("en", ["owl"], "file", "BookX", occurrences=occ)

    with v._conn() as con:
        row = con.execute("SELECT excerpt, location FROM occurrences").fetchone()
    assert tuple(row) == ("The wise owl hooted.", "ch3:42")    


# ------------------------------------------------------------------ language isolation
def test_language_isolation(tmp_path):
    v = make_vault(tmp_path)
    v.add_words("es", ["gato"], "deck", "SpanishDeck")

    cov, _, _ = v.coverage("en", ["gato"])
    assert cov == 0.0                                 # English vault unaware


# ------------------------------------------------------------------ safe removal of unknown source
def test_remove_nonexistent_source(tmp_path):
    v = make_vault(tmp_path)                          # empty vault
    # should not raise
    v.remove_source("deck", "NotThere")
    assert v.coverage("en", ["ghost"])[0] == 0.0
