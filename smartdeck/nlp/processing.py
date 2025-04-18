# smartdeck/nlp/processing.py

from __future__ import annotations
import re
from functools import lru_cache
from typing import Iterable, List, TypedDict

import spacy
from spacy.language import Language
import stanza


class WordInfo(TypedDict):
    lemma: str  # normalized lowercase lemma
    pos: str    # UPOS tag for German, spaCy POS for others


# simple regex to keep only alphabetic tokens
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")


@lru_cache(maxsize=None)
def _stanza_de_pipeline() -> stanza.Pipeline:
    """
    Load and cache the Stanza German pipeline (tokenize, mwt, pos, lemma).
    """
    return stanza.Pipeline(
        lang="de",
        processors="tokenize,mwt,pos,lemma",
        use_gpu=False,
        verbose=False,
    )


@lru_cache(maxsize=None)
def _spacy_model(lang: str) -> Language:
    """
    Load & cache spaCy models for non‑German languages.
    """
    name_map = {
        "en": "en_core_web_sm",
        # add others here if needed
    }
    model = name_map.get(lang.lower(), "en_core_web_sm")
    return spacy.load(model, disable=["ner", "parser", "textcat"])


def tokenize_lemmas(
    texts: Iterable[str],
    lang: str = "en",
) -> List[WordInfo]:
    """
    Lemmatise text chunks:
      - German ('de'): use Stanza UD pipeline for perfect accuracy.
      - Others: use spaCy.
    """
    lang = lang.lower()
    results: List[WordInfo] = []

    if lang == "de":
        nlp_de = _stanza_de_pipeline()
        for text in texts:
            doc = nlp_de(text)
            for sentence in doc.sentences:
                for word in sentence.words:
                    # skip tokens that aren’t pure letters
                    if not _WORD_RE.fullmatch(word.text):
                        continue
                    results.append(
                        WordInfo(lemma=word.lemma.lower(), pos=word.upos)
                    )
    else:
        nlp = _spacy_model(lang)
        for doc in nlp.pipe(texts, batch_size=20):
            for token in doc:
                if not token.is_alpha or not _WORD_RE.fullmatch(token.text):
                    continue
                results.append(
                    WordInfo(lemma=token.lemma_.lower(), pos=token.pos_)
                )

    return results

