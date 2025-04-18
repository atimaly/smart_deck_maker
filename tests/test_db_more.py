import pytest
from smartdeck.vault import Vault

def test_multiple_languages(tmp_path):
    v = Vault(tmp_path / "ml.db")
    v.add_words("en", ["hello"], kind="deck", ident="D1")
    v.add_words("de", ["hallo"], kind="deck", ident="D2")
    cov_en, _, _ = v.coverage("en", ["hello"])
    cov_de, _, _ = v.coverage("de", ["hallo"])
    assert cov_en == 1.0 and cov_de == 1.0
    # cross‑language queries return 0%
    cov_cross, _, _ = v.coverage("en", ["hallo"])
    assert cov_cross == 0.0

def test_remove_source_idempotent(tmp_path):
    v = Vault(tmp_path / "r.db")
    # removing twice is safe
    v.remove_source("deck", "NoSuch")
    v.remove_source("deck", "NoSuch")
    assert v.coverage("en", ["any"])[0] == 0.0

