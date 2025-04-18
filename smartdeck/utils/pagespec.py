"""Parse page specs like '1-3,7' into zero‑based indices."""
from __future__ import annotations
import re
from typing import List

_RANGE = re.compile(r"(\d+)(?:-(\d+))?")

def parse_pagespec(spec: str | None, total_pages: int | None = None) -> List[int]:
    if spec is None:
        return list(range(total_pages or 0))
    pages: set[int] = set()
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        m = _RANGE.fullmatch(token)
        if not m:
            raise ValueError(f"Bad token: {token!r}")
        start = int(m.group(1))
        end = int(m.group(2) or start)
        if end < start:
            raise ValueError(f"Descending range: {token!r}")
        pages.update(range(start - 1, end))      # zero‑based
    if total_pages is not None:
        pages = {p for p in pages if p < total_pages}
    return sorted(pages)

def virtual_split(text: str, every: int) -> List[str]:
    """
    Split `text` into pseudo-pages of `every` words each.
    E.g., virtual_split("a b c d e", 2) → ["a b", "c d", "e"].
    """
    words = text.split()
    return [
        " ".join(words[i : i + every])
        for i in range(0, len(words), every)
        if words[i : i + every]
    ]
