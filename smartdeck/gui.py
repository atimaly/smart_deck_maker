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

from smartdeck.extract.epub import extract_epub
from smartdeck.extract.pdf import extract_pdf
from smartdeck.nlp.processing import tokenize_lemmas
from smartdeck.vault.db import Vault
from smartdeck.deck.excerpt import capture_excerpts
from smartdeck.deck.builder import build_deck


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
            # Extract text
            if self.source.suffix.lower() == ".epub":
                texts = extract_epub(self.source, self.pages, self.virtual_pages)
            else:
                texts = extract_pdf(self.source, self.pages, self.virtual_pages)

            # Lemmatise
            tokens = tokenize_lemmas(texts, lang=self.lang)
            lemmas = [w["lemma"] for w in tokens]

            vault = Vault()
            pct, unknowns, tier = vault.coverage(self.lang, lemmas)

            if self.mode == "diff":
                lines: List[str] = [f"Coverage: {pct:.1%}", f"Tier: {tier}", "", "Top unknowns:"]
                for lem, cnt in unknowns.most_common(self.top):
                    lines.append(f"  {lem} ({cnt})")
                self.finished.emit("\n".join(lines))
                return

            # Build deck
            top_lemmas = [l for l, _ in unknowns.most_common(self.top)]
            occ = capture_excerpts(texts, top_lemmas)
            vault.add_words(self.lang, top_lemmas, kind="book", ident=str(self.source), occurrences=occ)
            vault._get_or_add_source("deck", str(self.output))

            entries = [(l, "", occ[l][0], occ[l][1]) for l in top_lemmas]
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
        w = QWidget()
        layout = QVBoxLayout()

        hfile = QHBoxLayout()
        hfile.addWidget(QLabel("Book:"))
        self.diff_file = QLineEdit()
        hfile.addWidget(self.diff_file)
        btn_file = QPushButton("Browse…")
        btn_file.clicked.connect(lambda: self._choose_file(self.diff_file))
        hfile.addWidget(btn_file)
        layout.addLayout(hfile)

        opts = QHBoxLayout()
        self.diff_pages = QLineEdit(); self.diff_pages.setPlaceholderText("Pagespec e.g. 1-3,5")
        self.diff_top = QSpinBox(); self.diff_top.setRange(1, 1000); self.diff_top.setValue(20)
        self.diff_lang = QComboBox(); self.diff_lang.addItems(["en", "de"])
        opts.addWidget(QLabel("Pages:")); opts.addWidget(self.diff_pages)
        opts.addWidget(QLabel("Top N:")); opts.addWidget(self.diff_top)
        opts.addWidget(QLabel("Lang:")); opts.addWidget(self.diff_lang)
        layout.addLayout(opts)

        run_btn = QPushButton("Compute Difficulty")
        run_btn.clicked.connect(self.on_diff)
        layout.addWidget(run_btn)

        self.diff_out = QTextBrowser()
        layout.addWidget(self.diff_out)
        w.setLayout(layout)
        return w

    def _make_build_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()

        hfile = QHBoxLayout()
        hfile.addWidget(QLabel("Book:"))
        self.build_file = QLineEdit()
        hfile.addWidget(self.build_file)
        btn_file = QPushButton("Browse…")
        btn_file.clicked.connect(lambda: self._choose_file(self.build_file))
        hfile.addWidget(btn_file)
        layout.addLayout(hfile)

        opts = QHBoxLayout()
        self.build_pages = QLineEdit(); self.build_pages.setPlaceholderText("Pagespec")
        self.build_virtual = QSpinBox(); self.build_virtual.setRange(0, 5000)
        self.build_top = QSpinBox(); self.build_top.setRange(1, 1000); self.build_top.setValue(100)
        self.build_lang = QComboBox(); self.build_lang.addItems(["en", "de"])
        opts.addWidget(QLabel("Pages:")); opts.addWidget(self.build_pages)
        opts.addWidget(QLabel("Virtual words:")); opts.addWidget(self.build_virtual)
        opts.addWidget(QLabel("Top N:")); opts.addWidget(self.build_top)
        opts.addWidget(QLabel("Lang:")); opts.addWidget(self.build_lang)
        layout.addLayout(opts)

        hout = QHBoxLayout()
        hout.addWidget(QLabel("Output .apkg:"))
        self.build_out = QLineEdit("deck.apkg")
        hout.addWidget(self.build_out)
        btn_out = QPushButton("Browse…")
        btn_out.clicked.connect(lambda: self._choose_file(self.build_out, save=True, filter="*.apkg"))
        hout.addWidget(btn_out)
        layout.addLayout(hout)

        self.build_progress = QProgressBar()
        layout.addWidget(self.build_progress)
        run_btn = QPushButton("Build Deck")
        run_btn.clicked.connect(self.on_build)
        layout.addWidget(run_btn)

        w.setLayout(layout)
        return w

    def _make_sync_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()

        hl = QHBoxLayout()
        hl.addWidget(QLabel("Registered sources:"))
        self.sync_combo = QComboBox()
        hl.addWidget(self.sync_combo)

        btn = QPushButton("Remove Selected Source")
        btn.clicked.connect(self.on_remove_source)
        hl.addWidget(btn)

        layout.addLayout(hl)
        w.setLayout(layout)

        self._refresh_sources()
        return w

    def _refresh_sources(self):
        vault = Vault()
        with vault._conn() as con:
            rows = con.execute("SELECT kind, ident FROM sources").fetchall()

        self.sync_combo.clear()
        for row in rows:
            kind = row["kind"]
            ident = row["ident"]
            display = f"{kind}: {ident}"
            self.sync_combo.addItem(display, (kind, ident))

    def on_remove_source(self):
        data = self.sync_combo.currentData()
        if not data:
            QMessageBox.warning(self, "Remove Source", "No source selected.")
            return
        kind, ident = data
        Vault().remove_source(kind, ident)
        QMessageBox.information(self, "Remove Source", f"Removed {kind!r} '{ident}'.")
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
            "diff"
        )
        self.worker.finished.connect(self.diff_out.setPlainText)
        self.worker.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        self.worker.start()

    def on_build(self):
        # reuse Worker for consistency
        self.worker = Worker(
            Path(self.build_file.text()),
            self.build_pages.text() or None,
            self.build_virtual.value() or None,
            self.build_top.value(),
            self.build_lang.currentText(),
            Path(self.build_out.text()),
            "build"
        )
        self.worker.finished.connect(self._on_build_finished)
        self.worker.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        self.worker.start()

    def _on_build_finished(self, msg: str):
        QMessageBox.information(self, "Done", msg)
        # now refresh the Sync tab’s list of sources
        self._refresh_sources()

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

