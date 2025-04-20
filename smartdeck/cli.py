from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

import typer
import requests
import epitran
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


def _translate(word: str, src: str, dest: str) -> str:
    """
    Translate a single word or sentence via Google Translate HTTP endpoint.
    """
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": src,
        "tl": dest,
        "dt": "t",
        "q": word,
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data[0][0][0]
    except Exception:
        return ""


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
    kind: str = typer.Argument(..., help="apkg, live, or book"),
    ident: str = typer.Argument(..., help="Path to .apkg, deck name, or book path"),
):
    vault = Vault()
    if kind == "apkg":
        vault.remove_source("deck", ident)
    elif kind == "live":
        vault.remove_source("live", ident)
        vault.remove_source("deck", ident)
    elif kind == "book":
        vault.remove_source("book", ident)
    else:
        typer.echo("Error: kind must be 'apkg', 'live', or 'book'", err=True)
        raise typer.Exit(code=1)
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
    """
    Build an Anki deck from the top‑N unknown words in a book,
    fetching translations and IPA on the fly (English⇄German).
    """
    # 1) Extract & lemmatize
    texts = (
        extract_epub(source, pages, virtual_pages)
        if source.suffix.lower() == ".epub"
        else extract_pdf(source, pages, virtual_pages)
    )
    tokens = tokenize_lemmas(texts, lang=lang)
    lemmas = [w["lemma"] for w in tokens]

    # 2) Map lemma → POS
    pos_map = {w["lemma"]: w["pos"] for w in tokens}

    # 3) Coverage & select top unknowns
    vault = Vault()
    _, unknowns, _ = vault.coverage(lang, lemmas)
    top_lemmas = [l for l, _ in unknowns.most_common(top)]

    # 4) Capture excerpts
    occ = capture_excerpts(texts, top_lemmas)

    # 5) Fetch word translations
    dest = "de" if lang.lower().startswith("en") else "en"
    translations = {
        lemma: _translate(lemma, src=lang, dest=dest)
        for lemma in top_lemmas
    }

    # 6) Generate IPA via Epitran
    iso3 = {"en": "eng", "de": "deu"}.get(lang.lower(), lang.lower())
    epi = epitran.Epitran(f"{iso3}-Latn")
    ipas = {lemma: epi.transliterate(lemma) for lemma in top_lemmas}

    # 7) Translate each full excerpt sentence
    sent_trans = {
        lemma: _translate(occ[lemma][0], src=lang, dest=dest)
        for lemma in top_lemmas
    }

    # 8) Build entries:
    #    (lemma, word‑translation, ipa, pos, excerpt, sent‑translation, loc)
    entries: list[tuple[str, ...]] = []
    for lemma in top_lemmas:
        entries.append((
            lemma,
            translations.get(lemma, ""),
            ipas.get(lemma, ""),
            pos_map.get(lemma, ""),
            occ[lemma][0],
            sent_trans.get(lemma, ""),
            occ[lemma][1],
        ))

    # 9) Persist & write deck
    vault.add_words(
        lang,
        top_lemmas,
        kind="book",
        ident=str(source),
        occurrences=occ,
    )
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

