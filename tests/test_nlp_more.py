# tests/test_nlp_german_more.py

import pytest
# Skip these tests if Germalemma isn't installed
pytest.importorskip("germalemma")

from smartdeck.nlp.processing import tokenize_lemmas

@pytest.mark.parametrize("token, expected", [
    ("ist", "sein"),
    ("bist", "sein"),
    ("läuft", "laufen"),
    ("gegessen", "essen"),
    ("gewesen", "sein"),
])
def test_german_conjugated_verbs(token, expected):
    infos = tokenize_lemmas([token], lang="de")
    lemmas = [w["lemma"] for w in infos]
    assert expected in lemmas, f"Expected '{expected}' for '{token}', got {lemmas}"

def test_pronouns_and_nouns_are_preserved():
    sentence = "Er sie du wir Katze"
    infos = tokenize_lemmas([sentence], lang="de")
    lemmas = {w["lemma"] for w in infos}
    for item in ["er", "sie", "du", "wir", "katze"]:
        assert item in lemmas, f"Missing '{item}' in {lemmas}"

@pytest.mark.parametrize(
    "sentence, expected_lemmas",
    [
        ("Er hat den Apfel gegessen.", ["essen"]),
        ("Den Apfel habe ich gegessen.", ["essen"]),
        ("Ich habe drei Kugel Eis gegessen.", ["essen"]),
        ("Sie isst drei Mahlzeiten am Tag.", ["essen"]),
        ("Er isst einen Apfel, weil er Hunger hat.", ["essen", "haben"]),
        ("Es wird nichts so heiß gegessen, wie es gekocht wird.", ["essen", "kochen"]),
        ("Ich habe zu viel gegessen.", ["essen"]),
        ("Tom hat tagelang nichts gegessen.", ["essen"]),
        ("Hast du etwas Schlechtes gegessen?", ["essen"]),
        ("Ich habe noch nicht gegessen.", ["essen"]),
        ("Welche Insekten haben Sie gegessen?", ["essen"]),
        ("Der Dieb ist spurlos verschwunden.", ["verschwinden"]),
        ("Die Rosen sind wundervoll aufgeblüht.", ["aufblühen"]),
        ("Wir haben ein Lied gesungen.", ["singen"]),
        ("Wir sind ein bisschen durch die Innenstadt gebummelt.", ["bummeln"]),
        ("Sie spricht fließend Deutsch.", ["sprechen"]),
        ("Ich habe gestern Abend im Bett ein Buch gelesen.", ["lesen"]),
    ],
)
def test_german_corpus_lemmata(sentence, expected_lemmas):
    lemmas = [w["lemma"] for w in tokenize_lemmas([sentence], lang="de")]
    for exp in expected_lemmas:
        assert exp in lemmas, f"Expected lemma '{exp}' in {lemmas}"
