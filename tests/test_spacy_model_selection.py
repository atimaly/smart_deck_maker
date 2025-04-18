
import pytest
import spacy

def test_english_model_is_small():
    """
    The default English model should be the lightweight 'sm' version.
    """
    nlp = spacy.load("en_core_web_sm")
    model_name = nlp.meta.get("name", "")
    assert "core_web_sm" in model_name, f"Expected 'core_web_sm', got: {model_name}"
