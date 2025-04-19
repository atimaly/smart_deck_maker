from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

import typer
from typer import Context

from smartdeck.utils.pagespec import parse_pagespec
from smartdeck.extract.epub import extract_epub
from smartdeck.extract.pdf import extract_pdf
from smartdeck.nlp.processing import tokenize_lemmas
from smartdeck.vault.db import Vault
from smartdeck.deck.excerpt import capture_excerpts
from smartdeck.deck.builder import build_deck

from smartdeck.ingest.apkg import ingest_apkg
from smartdeck.ingest.live import ingest_live

app = typer.Typer(help="SmartDeck Maker CLI")
sync_app = typer.Typer(help="Synchronize Anki decks ↔ known‑word vault")
app.add_typer(sync_app, name="sync")


@sync_app.command("add")
def sync_add(
    kind: str = typer.Argument(..., help="apkg or live"),
    ident: str = typer.Argument(..., help="Path to .apkg or deck name"),
    lang: str = typer.Option("en", "--lang", "-l", help="Language code"),
    top: Optional[int] = typer.Option(None, "--top", "-t", help="Max unknowns to ingest"),
):
    vault = Vault()
    if kind == "apkg":
        path = Path(ident)
        if not path.exists():
            typer.echo(f"Error: file not found: {path}", err=True)
            raise typer.Exit(code=1)
        ingest_apkg(path, lang=lang, vault=vault, top=top)
        typer.echo(f"Imported {path.name} into vault.")
    elif kind == "live":
        vault._get_or_add_source("live", ident)
        ingest_live(ident, lang=lang, vault=vault)
        typer.echo(f"Imported live deck '{ident}' into vault.")
    else:
        typer.echo("Error: kind must be 'apkg' or 'live'", err=True)
        raise typer.Exit(code=1)


@sync_app.command("remove")
def sync_remove(
    kind: str = typer.Argument(..., help="apkg or live"),
    ident: str = typer.Argument(..., help="Path to .apkg or deck name"),
):
    vault = Vault()
    if kind == "apkg":
        vault.remove_source("deck", ident)
    elif kind == "live":
        vault.remove_source("live", ident)
        vault.remove_source("deck", ident)
    typer.echo(f"Removed {kind} '{ident}' and any orphaned words.")


@app.command("diff")
def diff_cmd(
    source: Path = typer.Argument(..., help="EPUB or PDF file to analyze"),
    pages: Optional[str] = typer.Option(None, "--pages", "-p"),
    virtual_pages: Optional[int] = typer.Option(None, "--virtual-pages", "-v"),
    top: int = typer.Option(20, "--top", "-t"),
    lang: str = typer.Option("en", "--lang", "-l"),
):
    texts = (
        extract_epub(source, pages, virtual_pages)
        if source.suffix.lower() == ".epub"
        else extract_pdf(source, pages, virtual_pages)
    )
    tokens = tokenize_lemmas(texts, lang=lang)
    lemmas = [w["lemma"] for w in tokens]
    pct, unknowns, tier = Vault().coverage(lang, lemmas)

    typer.echo(f"Coverage: {pct:.1%}")
    typer.echo(f"Tier: {tier}")
    typer.echo(f"\nUnknown lemmas (top {top}):")
    for lem, cnt in unknowns.most_common(top):
        typer.echo(f"  {lem} ({cnt})")


@app.command("build")
def build_cmd(
    source: Path = typer.Argument(..., help="EPUB or PDF file to build from"),
    pages: Optional[str] = typer.Option(None, "--pages", "-p"),
    virtual_pages: Optional[int] = typer.Option(None, "--virtual-pages", "-v"),
    top: int = typer.Option(100, "--top", "-t"),
    lang: str = typer.Option("en", "--lang", "-l"),
    output: Path = typer.Option(Path("deck.apkg"), "--output", "-o"),
):
    texts = (
        extract_epub(source, pages, virtual_pages)
        if source.suffix.lower() == ".epub"
        else extract_pdf(source, pages, virtual_pages)
    )
    tokens = tokenize_lemmas(texts, lang=lang)
    lemmas = [w["lemma"] for w in tokens]
    _, unknowns, _ = Vault().coverage(lang, lemmas)

    top_lemmas = [l for l, _ in unknowns.most_common(top)]
    occ = capture_excerpts(texts, top_lemmas)
    Vault().add_words(lang, top_lemmas, kind="book", ident=str(source), occurrences=occ)

    entries = [(l, "", occ[l][0], occ[l][1]) for l in top_lemmas]
    build_deck(source.name, entries, str(output))
    typer.echo(f"✅ Deck written to {output}")


@app.callback(invoke_without_command=True)
def main(
    ctx: Context,
    version: bool = typer.Option(False, "--version"),
):
    if version:
        import pkg_resources
        v = pkg_resources.get_distribution("smart-deck-maker").version
        typer.echo(v)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


if __name__ == "__main__":
    app()

