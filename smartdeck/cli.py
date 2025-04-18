# smartdeck/cli.py

from pathlib import Path
from typing import List
import typer

from smartdeck.utils.pagespec import parse_pagespec
from smartdeck.extract.epub import extract_epub
from smartdeck.extract.pdf import extract_pdf
from smartdeck.nlp.processing import tokenize_lemmas
from smartdeck.vault.db import Vault
from smartdeck.deck.excerpt import capture_excerpts
from smartdeck.deck.builder import build_deck

app = typer.Typer(help="Smart Deck Maker CLI")

@app.command()
def build(
    source: Path = typer.Argument(..., help="Path to EPUB or PDF"),
    pages: str = typer.Option(None, "--pages", help="Pagespec, e.g. '1-3,5'"),
    virtual_pages: int = typer.Option(0, "--virtual-pages", help="Split every N words"),
    top: int = typer.Option(100, "--top", help="Top N unknown lemmas"),
    lang: str = typer.Option("en", "--lang", help="Language code"),
    output: Path = typer.Option(Path("deck.apkg"), "--output", help="Output .apkg"),
):
    """
    Build an Anki deck from the given EPUB or PDF, capturing new vocabulary.
    """
    # 1) extract text pages
    if source.suffix.lower() == ".epub":
        pages_text: List[str] = extract_epub(
            source,
            pages=pages,
            virtual_pages=virtual_pages or None,
        )
    else:
        pages_text = extract_pdf(
            source,
            pages=pages,
            virtual_pages=virtual_pages or None,
        )

    # 2) tokenize & find unknown lemmas
    vault = Vault()  # uses ~/.smartdeck/known.db by default
    tokens = tokenize_lemmas(pages_text, lang=lang)
    lemmas = [w["lemma"] for w in tokens]
    _, unknowns, _ = vault.coverage(lang, lemmas)

    top_lemmas = [lem for lem, _ in unknowns.most_common(top)]

    # 3) capture excerpts
    occ = capture_excerpts(pages_text, top_lemmas)

    # 4) add to vault & build deck
    vault.add_words(
        lang,
        top_lemmas,
        kind="book",
        ident=str(source),
        occurrences=occ,
    )
    entries = [(l, "", occ[l][0], occ[l][1]) for l in top_lemmas]
    build_deck(str(source.name), entries, str(output))

    typer.echo(f"✅ Deck written to {output}")

# smartdeck/cli.py  (append below your existing build command)

@app.command()
def diff(
    source: Path = typer.Argument(..., help="Path to EPUB or PDF"),
    pages: str = typer.Option(None, "--pages", help="Pagespec, e.g. '1-3,5'"),
    virtual_pages: int = typer.Option(0, "--virtual-pages", help="Split every N words"),
    top: int = typer.Option(20, "--top", help="Show top N unknowns"),
    lang: str = typer.Option("en", "--lang", help="Language code"),
):
    """
    Show coverage % and difficulty tier for a book,
    plus the top N unknown lemmas with counts.
    """
    # 1) extract text pages
    if source.suffix.lower() == ".epub":
        texts = extract_epub(source, pages=pages, virtual_pages=virtual_pages or None)
    else:
        texts = extract_pdf(source, pages=pages, virtual_pages=virtual_pages or None)

    # 2) compute lemmas & coverage
    vault = Vault()  # ~/.smartdeck/known.db
    lemmas = [w["lemma"] for w in tokenize_lemmas(texts, lang=lang)]
    pct, unknowns, tier = vault.coverage(lang, lemmas)

    # 3) print summary
    typer.echo(f"Coverage: {pct:.1f}%   Tier: {tier}")
    typer.echo(f"Unknown lemmas (top {top}):")
    for lemma, count in unknowns.most_common(top):
        typer.echo(f"  {lemma} ({count})")


if __name__ == "__main__":
    app()

import pkg_resources

__version__ = pkg_resources.get_distribution("smart_deck_maker").version

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version"),
):
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()
