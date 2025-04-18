
import subprocess
import sys
from pathlib import Path


def test_build_on_sample_epub(tmp_path):
    """
    Verify that the 'build' subcommand creates a non-empty .apkg from a sample EPUB.
    """
    epub = Path("tests/assets/sample.epub")
    out = tmp_path / "out.apkg"
    # invoke via the interpreter inside the venv, specifying the 'build' subcommand
    cmd = [
        sys.executable, "-m", "smartdeck.cli",
        "build", str(epub),
        "--lang", "de",
        "--top", "10",
        "--output", str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert out.exists() and out.stat().st_size > 0
