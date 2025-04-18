"""Extract per‑page text from PDF using pdfminer.six."""
from __future__ import annotations

from pathlib import Path
from typing import List

from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams

from ..utils.pagespec import parse_pagespec, virtual_split


def extract_pdf(
    path: str | Path,
    pages: str | None = None,
    virtual_pages: int | None = None,
) -> List[str]:
    """
    Read `path` PDF and return list of strings per page:
      - Splits the raw text on form‑feeds (\f) to get pages.
      - Applies the same `pages` spec and optional virtual splitting.
    """
    laparams = LAParams()
    # this pulls the entire doc, with '\f' between pages
    raw = extract_text(str(path), laparams=laparams)
    # if extract_text fails or returns '', raw_pages may be ['']
    raw_pages = raw.split("\f")

    idxs = parse_pagespec(pages, total_pages=len(raw_pages))
    pages_text = [raw_pages[i].strip() for i in idxs if raw_pages[i].strip()]

    if virtual_pages:
        joined = " ".join(pages_text)
        return virtual_split(joined, virtual_pages)

    return pages_text

