# tests/test_extract.py

import pytest
from pathlib import Path
from smartdeck.extract import extract_epub, extract_pdf

@pytest.fixture
def ASSETS():
    return Path(__file__).parent / "assets"

def test_epub_whole(ASSETS):
    pages = extract_epub(ASSETS / "sample.epub")
    assert isinstance(pages, list) and len(pages) >= 1

def test_epub_pagespec(ASSETS):
    pages = extract_epub(ASSETS / "sample.epub", pages="1")
    assert len(pages) == 1

def test_pdf_whole(ASSETS):
    pages = extract_pdf(ASSETS / "sample.pdf")
    assert isinstance(pages, list) and len(pages) >= 1

def test_pdf_pagespec(ASSETS):
    pages = extract_pdf(ASSETS / "sample.pdf", pages="1-1")
    assert len(pages) == 1

