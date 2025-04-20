# smartdeck/gui.py

from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Literal

from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextBrowser, QFileDialog, QLabel,
    QSpinBox, QComboBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal

import requests
import epitran

from smartdeck.extract.epub import extract_epub
from smartdeck.extract.pdf import extract_pdf
from smartdeck.nlp.processing import tokenize_lemmas
from smartdeck.vault.db import Vault
from smartdeck.deck.excerpt import capture_excerpts
from smartdeck.deck.builder import build_deck


def _translate(word: str, src: str, dest: str) -> str:
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": src, "tl": dest, "dt": "t", "q": word}
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        return r.json()[0][0][0]
    except Exception:
        return ""


class Worker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        source: Path,
        pages: str | None,
        virtual_pages: int | None,
        top: int,
        lang: str,
        output: Path,
        mode: Literal["diff", "build"],
    ):
        super().__init__()
        self.source = source
        self.pages = pages
        self.virtual_pages = virtual_pages
        self.top = top
        self.lang = lang
        self.output = output
        self.mode = mode

    def run(self):
        try:
            # 1) Extract text
            if self.source.suffix.lower() == ".epub":
                texts = extract_epub(self.source, self.pages, self.virtual_pages)
            else:
                texts = extract_pdf(self.source, self.pages, self.virtual_pages)

            # 2) Lemmatize
            tokens = tokenize_lemmas(texts, lang=self.lang)
            lemmas = [w["lemma"] for w in tokens]

            # 3) Coverage
            vault = Vault()
            pct, unknowns, tier = vault.coverage(self.lang, lemmas)

            if self.mode == "diff":
                lines = [f"Coverage: {pct:.1%}", f"Tier: {tier}", "", "Top unknowns:"]
                for lem, cnt in unknowns.most_common(self.top):
                    lines.append(f"  {lem} ({cnt})")
                self.finished.emit("\n".join(lines))
                return

            # === BUILD ===

            # 4) select top
            top_lemmas = [l for l, _ in unknowns.most_common(self.top)]

            # 5) excerpts
            occ = capture_excerpts(texts, top_lemmas)

            # 6) translations
            dest = "de" if self.lang.lower().startswith("en") else "en"
            translations = {w: _translate(w, src=self.lang, dest=dest) for w in top_lemmas}

            # 7) IPA
            iso3 = {"en": "eng", "de": "deu"}.get(self.lang.lower(), self.lang.lower())
            epi = epitran.Epitran(f"{iso3}-Latn")
            ipas = {w: epi.transliterate(w) for w in top_lemmas}

            # 8) sentence translations
            sent_trans = {w: _translate(occ[w][0], src=self.lang, dest=dest) for w in top_lemmas}

            # 9) build note entries
            pos_map = {w["lemma"]: w["pos"] for w in tokens}
            entries: list[tuple[str, ...]] = []
            for w in top_lemmas:
                entries.append((
                    w,
                    translations.get(w, ""),
                    ipas.get(w, ""),
                    pos_map.get(w, ""),
                    occ[w][0],
                    sent_trans.get(w, ""),
                    occ[w][1],
                ))

            # 10) persist & write
            vault.add_words(
                self.lang, top_lemmas,
                kind="book", ident=str(self.source),
                occurrences=occ,
            )
            build_deck(self.source.name, entries, str(self.output))
            self.finished.emit(f"Deck written to {self.output}")

        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartDeck Maker")
        self.resize(600, 400)

        self.tabs = QTabWidget()
        self.diff_tab = self._make_diff_tab()
        self.build_tab = self._make_build_tab()
        self.sync_tab = self._make_sync_tab()
        self.tabs.addTab(self.diff_tab, "Difficulty")
        self.tabs.addTab(self.build_tab, "Build Deck")
        self.tabs.addTab(self.sync_tab, "Sync / Remove")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def _make_diff_tab(self) -> QWidget:
        w = QWidget(); layout = QVBoxLayout()
        hfile = QHBoxLayout()
        hfile.addWidget(QLabel("Book:")); self.diff_file = QLineEdit(); hfile.addWidget(self.diff_file)
        btn = QPushButton("Browse…"); btn.clicked.connect(lambda: self._choose_file(self.diff_file))
        hfile.addWidget(btn); layout.addLayout(hfile)

        opts = QHBoxLayout()
        self.diff_pages = QLineEdit(); self.diff_pages.setPlaceholderText("Pagespec")
        self.diff_top   = QSpinBox(); self.diff_top.setRange(1,1000); self.diff_top.setValue(20)
        self.diff_lang  = QComboBox(); self.diff_lang.addItems(["en","de"])
        opts.addWidget(QLabel("Pages:")); opts.addWidget(self.diff_pages)
        opts.addWidget(QLabel("Top N:")); opts.addWidget(self.diff_top)
        opts.addWidget(QLabel("Lang:")); opts.addWidget(self.diff_lang)
        layout.addLayout(opts)

        run = QPushButton("Compute Difficulty"); run.clicked.connect(self.on_diff)
        layout.addWidget(run)
        self.diff_out = QTextBrowser(); layout.addWidget(self.diff_out)
        w.setLayout(layout)
        return w

    def _make_build_tab(self) -> QWidget:
        w = QWidget(); layout = QVBoxLayout()
        hfile = QHBoxLayout()
        hfile.addWidget(QLabel("Book:")); self.build_file = QLineEdit(); hfile.addWidget(self.build_file)
        btn = QPushButton("Browse…"); btn.clicked.connect(lambda: self._choose_file(self.build_file))
        hfile.addWidget(btn); layout.addLayout(hfile)

        opts = QHBoxLayout()
        self.build_pages   = QLineEdit(); self.build_pages.setPlaceholderText("Pagespec")
        self.build_virtual = QSpinBox(); self.build_virtual.setRange(0,5000)
        self.build_top     = QSpinBox(); self.build_top.setRange(1,1000); self.build_top.setValue(100)
        self.build_lang    = QComboBox(); self.build_lang.addItems(["en","de"])
        opts.addWidget(QLabel("Pages:")); opts.addWidget(self.build_pages)
        opts.addWidget(QLabel("Virtual words:")); opts.addWidget(self.build_virtual)
        opts.addWidget(QLabel("Top N:")); opts.addWidget(self.build_top)
        opts.addWidget(QLabel("Lang:")); opts.addWidget(self.build_lang)
        layout.addLayout(opts)

        hout = QHBoxLayout()
        hout.addWidget(QLabel("Output .apkg:")); self.build_out = QLineEdit("deck.apkg"); hout.addWidget(self.build_out)
        btn2 = QPushButton("Browse…"); btn2.clicked.connect(lambda: self._choose_file(self.build_out, save=True, filter="*.apkg"))
        hout.addWidget(btn2)
        layout.addLayout(hout)

        self.build_progress = QProgressBar(); layout.addWidget(self.build_progress)
        run = QPushButton("Build Deck"); run.clicked.connect(self.on_build)
        layout.addWidget(run)

        w.setLayout(layout)
        return w

    def _make_sync_tab(self) -> QWidget:
        w = QWidget(); layout = QVBoxLayout()
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Registered sources:"))
        self.sync_combo = QComboBox(); hl.addWidget(self.sync_combo)
        btn = QPushButton("Remove Selected Source"); btn.clicked.connect(self.on_remove_source)
        hl.addWidget(btn)
        layout.addLayout(hl)
        w.setLayout(layout)
        self._refresh_sources()
        return w

    def _refresh_sources(self):
        self.sync_combo.clear()
        with Vault()._conn() as con:
            for row in con.execute("SELECT kind,ident FROM sources"):
                display = f"{row['kind']}: {row['ident']}"
                self.sync_combo.addItem(display, (row['kind'], row['ident']))

    def on_remove_source(self):
        data = self.sync_combo.currentData()
        if not data:
            QMessageBox.warning(self, "Remove Source", "No source selected.")
            return
        kind, ident = data
        Vault().remove_source(kind, ident)
        QMessageBox.information(self, "Remove Source", f"Removed {kind!r} '{ident}'")
        self._refresh_sources()

    def _choose_file(self, line: QLineEdit, save: bool=False, filter: str="*.*"):
        dlg = QFileDialog(self, directory=".", filter=filter)
        if save:
            path, _ = dlg.getSaveFileName(self, filter=filter)
        else:
            path, _ = dlg.getOpenFileName(self, filter=filter)
        if path:
            line.setText(path)

    def on_diff(self):
        self.diff_out.clear()
        self.worker = Worker(
            Path(self.diff_file.text()),
            self.diff_pages.text() or None,
            None,
            self.diff_top.value(),
            self.diff_lang.currentText(),
            Path(),
            "diff",
        )
        self.worker.finished.connect(self.diff_out.setPlainText)
        self.worker.error.connect(lambda m: QMessageBox.critical(self, "Error", m))
        self.worker.start()

    def on_build(self):
        self.worker = Worker(
            Path(self.build_file.text()),
            self.build_pages.text() or None,
            self.build_virtual.value() or None,
            self.build_top.value(),
            self.build_lang.currentText(),
            Path(self.build_out.text()),
            "build",
        )
        self.worker.progress.connect(self.build_progress.setValue)
        self.worker.finished.connect(lambda m: QMessageBox.information(self, "Done", m) or self._refresh_sources())
        self.worker.error.connect(lambda m: QMessageBox.critical(self, "Error", m))
        self.worker.start()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

