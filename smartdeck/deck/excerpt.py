import re
from typing import Iterable, Dict, Tuple

# Naïve sentence splitter (keeps punctuation)
_SENTENCE_RE = re.compile(r'([^\.!?]+[\.!?])', re.UNICODE)

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

    Excerpt is clipped to <=120 chars around the lemma.  If no sentence match
    is found, fall back to a 120‑char snippet containing the lemma (or blank),
    with a fuzzy location "page:?".  This guarantees you’ll always get back
    something (even if it’s just a snippet) rather than "".
    """
    needed = set(lemmas)
    seen: Dict[str, Tuple[str, str]] = {}

    # 1) First pass: sentence‑by‑sentence
    for p_idx, page in enumerate(pages, start=1):
        for s_idx, sent in enumerate(split_sentences(page), start=1):
            text = sent.strip()
            for lemma in list(needed):
                if _word_pattern(lemma).search(text):
                    low = text.lower()
                    start = low.find(lemma.lower())
                    # truncate to ~120 chars around the match
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

    # 2) Fallback: substring search for anything left
    for lemma in needed:
        snippet, loc = "", ""
        lower = lemma.lower()
        for p_idx, page in enumerate(pages, start=1):
            idx = page.lower().find(lower)
            if idx != -1:
                # grab a window around it
                start = max(0, idx - 40)
                snippet = page[start : start + 120].strip()
                if len(snippet) < len(page) and not snippet.endswith(("!", ".", "?", "…")):
                    snippet += "…"
                loc = f"{p_idx}:?"
                break
        seen[lemma] = (snippet, loc)

    return seen

