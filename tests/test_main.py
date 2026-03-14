import subprocess
import sys


def test_main_help():
    result = subprocess.run(
        [sys.executable, "-m", "mnemolith.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "index" in result.stdout
    assert "search" in result.stdout
