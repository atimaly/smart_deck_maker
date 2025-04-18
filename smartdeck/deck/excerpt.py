# smartdeck/deck/excerpt.py

import re
from typing import Iterable, Dict, Tuple

# Naïve sentence splitter (keeps punctuation)
_SENTENCE_RE = re.compile(r'([^\.!?]+[\.!?])', re.UNICODE)
# match whole‑word occurrences
def _word_pattern(lemma: str):
    return re.compile(rf'\b{re.escape(lemma)}\b', re.IGNORECASE)

def split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving the terminator."""
    return _SENTENCE_RE.findall(text)

def capture_excerpts(
    pages: Iterable[str],
    lemmas: Iterable[str]
) -> Dict[str, Tuple[str, str]]:
    """
    For each lemma, find the first sentence in pages that contains it.
    Returns { lemma: (excerpt, "page:sent_index") }.
    Excerpt is clipped to <=120 chars around the lemma.
    """
    needed = set(lemmas)
    seen: Dict[str, Tuple[str, str]] = {}
    for p_idx, page in enumerate(pages, start=1):
        for s_idx, sent in enumerate(split_sentences(page), start=1):
            text = sent.strip()
            for lemma in list(needed):
                if _word_pattern(lemma).search(text):
                    # truncate to 120 chars around search-hit
                    low = text.lower()
                    start = low.find(lemma.lower())
                    if len(text) > 120:
                        a = max(0, start - 40)
                        text = text[a : a + 120].strip()
                        if not text.endswith(("!", ".", "?")):
                            text += "…"
                    loc = f"{p_idx}:{s_idx}"
                    seen[lemma] = (text, loc)
                    needed.remove(lemma)
            if not needed:
                return seen
    # any remaining lemmas get a blank excerpt/location
    for lemma in needed:
        seen[lemma] = ("", "")
    return seen

