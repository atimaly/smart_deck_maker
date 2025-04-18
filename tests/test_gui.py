
import pytest
from PyQt6.QtWidgets import QApplication, QLineEdit, QPushButton
from smartdeck.gui import MainWindow

@pytest.fixture(scope="session")
def app():
    """Provide a single QApplication instance for all GUI tests."""
    return QApplication([])

def test_window_opens(app):
    """MainWindow should instantiate and have the correct title."""
    win = MainWindow()
    win.show()
    assert win.windowTitle() == "SmartDeck Maker"

def test_diff_tab_layout(app):
    """
    Difficulty tab should contain at least one QLineEdit for the file/pagespec
    and a QPushButton labeled 'Compute Difficulty'.
    """
    win = MainWindow()
    tab = win.diff_tab

    # There must be a QLineEdit in the diff tab
    assert tab.findChild(QLineEdit) is not None, "No QLineEdit found in the Difficulty tab"

    # There must be a button with the exact text "Compute Difficulty"
    buttons = tab.findChildren(QPushButton)
    assert any(btn.text() == "Compute Difficulty" for btn in buttons), \
        "Could not find a QPushButton with text 'Compute Difficulty'"
