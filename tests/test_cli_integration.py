"""End-to-end CLI integration tests."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def test_cli_merge_to_stdout():
    """Test merge command outputting to stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source.env"
        source.write_text("KEY=value\n")

        target = Path(tmpdir) / "target.env"
        target.write_text("KEY=old\nOTHER=keep\n")

        result = subprocess.run(
            ["python3", "envyeet.py", "merge", str(source), str(target)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "KEY=value" in result.stdout
        assert "OTHER=keep" in result.stdout


def test_cli_merge_to_file():
    """Test merge command with --output flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source.env"
        source.write_text("KEY=value\n")

        target = Path(tmpdir) / "target.env"
        target.write_text("KEY=old\n")

        output = Path(tmpdir) / "output.env"

        result = subprocess.run(
            [
                "python3",
                "envyeet.py",
                "merge",
                str(source),
                str(target),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert output.exists()
        assert output.read_text() == "KEY=value\n"


def test_cli_backup():
    """Test backup command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source.env"
        source.write_text("KEY=value\n")

        result = subprocess.run(
            ["python3", "envyeet.py", "backup", str(source)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert ".bkp-" in result.stdout
        backup_path = Path(result.stdout.strip())
        assert backup_path.exists()
        assert backup_path.read_text() == "KEY=value\n"


def test_cli_backup_custom_name():
    """Test backup command with custom name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source.env"
        source.write_text("KEY=value\n")

        backup = Path(tmpdir) / "backup.env"

        result = subprocess.run(
            ["python3", "envyeet.py", "backup", str(source), "--output", str(backup)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert backup.exists()
        assert backup.read_text() == "KEY=value\n"


def test_cli_quiet_mode():
    """Test --quiet flag suppresses output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source.env"
        source.write_text("KEY=value\n")

        target = Path(tmpdir) / "target.env"
        target.write_text("KEY=old\n")

        result = subprocess.run(
            ["python3", "envyeet.py", "-q", "merge", str(source), str(target)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert result.stdout == ""


def test_cli_version():
    """Test --version flag."""
    result = subprocess.run(
        ["python3", "envyeet.py", "--version"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_help():
    """Test --help flag."""
    result = subprocess.run(
        ["python3", "envyeet.py", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "envyeet" in result.stdout
    assert "merge" in result.stdout
    assert "backup" in result.stdout


def test_cli_file_not_found():
    """Test error handling for non-existent file."""
    result = subprocess.run(
        ["python3", "envyeet.py", "merge", "nonexistent.env", "target.env"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "not found" in result.stderr


def test_cli_verbose_dry_run():
    """Test --verbose --dry-run shows changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source.env"
        source.write_text("KEY=value\n")

        target = Path(tmpdir) / "target.env"
        target.write_text("KEY=old\n")

        result = subprocess.run(
            [
                "python3",
                "envyeet.py",
                "-v",
                "merge",
                str(source),
                str(target),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Keys to update" in result.stderr


if __name__ == "__main__":
    import sys

    pytest.main([__file__, "-v"] + sys.argv[1:])
