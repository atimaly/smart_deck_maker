
import subprocess
import sys
import os
from pathlib import Path


def test_diff_on_sample_epub(tmp_path):
    """
    Verify that the 'diff' subcommand reports coverage and tier correctly for a sample EPUB.
    """
    epub = Path("tests/assets/sample.epub")
    # point Vault at a fresh temp DB
    env = {**os.environ, "SMARTDECK_DB": str(tmp_path / "known.db")}

    cmd = [
        sys.executable,
        "-m",
        "smartdeck.cli",
        "diff",             # specify the diff subcommand
        str(epub),
        "--lang", "en",
        "--top", "3",
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "Coverage:" in out
    assert "Tier:" in out
    assert "Unknown lemmas (top 3):" in out

