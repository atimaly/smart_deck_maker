"""Extract text from an EPUB spine, with optional virtual‑page splitting."""
from __future__ import annotations

from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List

from ..utils.pagespec import parse_pagespec, virtual_split


def extract_epub(
    path: str | Path,
    pages: str | None = None,
    virtual_pages: int | None = None,
) -> List[str]:
    """
    Read `path` EPUB and return a list of strings, one per “page”:
      - If `pages="1-3,5"`, only those spine indices (1‑based) are included.
      - If `virtual_pages=n`, all text is concatenated and then split every n words.
      - Otherwise, returns one entry per spine document.
    """
    book = epub.read_epub(str(path))
    # correct unpacking: each spine entry is (idref, attrs)
    spine_ids = [idref for idref, _ in book.spine]

    total = len(spine_ids)

    idxs = parse_pagespec(pages, total_pages=total)
    texts: list[str] = []
    for i in idxs:
        item = book.get_item_with_id(spine_ids[i])
        html = item.get_content()
        # strip HTML to plain text
        soup = BeautifulSoup(html, "html.parser")
        texts.append(soup.get_text(" ", strip=True))

    if virtual_pages:
        joined = " ".join(texts)
        return virtual_split(joined, virtual_pages)

    return texts

