import pytest
from smartdeck.deck.excerpt import capture_excerpts

def test_simple_excerpts():
    pages = [
        "This is a test. Das Wort Apfel hier.",
        "Noch ein Satz mit Apfel und Birne.",
    ]
    lemmas = ["apfel","birne"]
    occ = capture_excerpts(pages, lemmas)
    assert occ["apfel"][1] == "1:2"
    assert "Apfel" in occ["apfel"][0]
    assert occ["birne"][1] == "2:1"

def test_truncate_excerpt():
    long_sentence = "Lorem " + "a"*200 + " gegessen Ende."
    pages = [long_sentence]
    occ = capture_excerpts(pages, ["gegessen"])
    assert len(occ["gegessen"][0]) <= 123  # ~120 + ellipsis
    assert occ["gegessen"][1] == "1:1"

