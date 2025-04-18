"""Text extractors for EPUB and PDF."""
from .epub import extract_epub
from .pdf import extract_pdf

__all__ = ["extract_epub", "extract_pdf"]

