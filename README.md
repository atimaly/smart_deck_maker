# SmartDeck Maker

SmartDeck Maker helps you generate Anki decks from EPUB or PDF books by:

- Identifying your “unknown” vocabulary  
- Capturing example sentences with highlighted words  
- Fetching word translations (via Google Translate HTTP API)  
- Generating IPA/transliteration (via Epitran)  
- Translating full example sentences  
- Building ready‑to‑import Anki `.apkg` files  
- Syncing with existing Anki decks (import/remove `.apkg` sources)

---

## Installation

```bash
git clone https://github.com/your‑org/smartdeck‑maker.git
cd smartdeck‑maker
poetry install
```

> **Optional**:  
> To override the default vault location (`~/.smartdeck/known.db`), set  
> `export SMARTDECK_DB=/path/to/your/vault.db`.

---

## Command‑Line Usage

Invoke via Python’s `-m` interface or through the Poetry virtualenv:

```bash
poetry run python -m smartdeck.cli [COMMAND] [OPTIONS]
```

### 1. Difficulty Report

```bash
poetry run python -m smartdeck.cli diff <book> \
  --lang <lang> \
  --top <N> \
  [--pages <pagespec>]
```

- `<book>`: path to `.epub` or `.pdf`  
- `--lang`: language code (e.g. `en`, `de`)  
- `--top`: show top N unknown lemmas  
- `--pages`: e.g. `1-3,5` (omit for all)

### 2. Build Anki Deck

```bash
poetry run python -m smartdeck.cli build <book> \
  --lang <lang> \
  --top <N> \
  --output <deck.apkg> \
  [--pages <pagespec>] [--virtual-pages <words>]
```

- Extracts & lemmatizes text  
- Picks the top N unknown lemmas  
- Captures and highlights sentences (≤120 chars around each lemma)  
- Fetches:
  - **Word translation**  
  - **IPA/transliteration**  
  - **Sentence translation**  
- Produces `<deck.apkg>` ready for import

### 3. Sync / Remove Known Words

```bash
# Import words from an existing .apkg
poetry run python -m smartdeck.cli sync add apkg path/to/deck.apkg --lang en

# Register (stub) a live AnkiConnect deck
poetry run python -m smartdeck.cli sync add live "MyDeckName" --lang de

# Remove a source (cascades orphan words)
poetry run python -m smartdeck.cli sync remove apkg path/to/deck.apkg
```

---

## Graphical Interface

```bash
poetry run python -m smartdeck.gui
```

- **Difficulty** tab: run coverage report  
- **Build Deck** tab: configure and generate `.apkg`  
- **Sync/Remove** tab: list and remove registered sources  

---

## Development & Testing

- Run the full test suite:  
  ```bash
  poetry run pytest -q
  ```
- Code formatting:  
  ```bash
  poetry run black .
  poetry run flake8
  ```
- Contribute by forking, branching (`feature/…`), adding tests, and opening a PR.

---

## License

Released under the MIT License. See [LICENSE](LICENSE) for details.
