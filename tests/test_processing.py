# tests/test_processing.py

import pytest
from smartdeck.nlp.processing import tokenize_lemmas, WordInfo

def test_tokenize_simple_sentence():
    texts = ["Cats are running! 123"]
    infos = tokenize_lemmas(texts, lang="en")
    # Expect at least these lemmas
    lemmas = [w["lemma"] for w in infos]
    assert "cat" in lemmas
    assert "run" in lemmas
    # POS tags should be valid strings
    assert all(isinstance(w["pos"], str) for w in infos)

def test_non_alpha_filtered_out():
    texts = ["hello #world 42!"]
    infos = tokenize_lemmas(texts, lang="en")
    lemmas = [w["lemma"] for w in infos]
    assert "hello" in lemmas
    assert "world" in lemmas
    # numeric tokens never appear
    assert not any(w["lemma"].isdigit() for w in infos)

