"""End-to-end CLI integration tests."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestCLIIntegration(unittest.TestCase):
    def test_cli_merge_to_stdout(self):
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

            self.assertEqual(result.returncode, 0)
            self.assertIn("KEY=value", result.stdout)
            self.assertIn("OTHER=keep", result.stdout)

    def test_cli_merge_to_file(self):
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

            self.assertEqual(result.returncode, 0)
            self.assertTrue(output.exists())
            self.assertEqual(output.read_text(), "KEY=value\n")

    def test_cli_backup(self):
        """Test backup command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY=value\n")

            result = subprocess.run(
                ["python3", "envyeet.py", "backup", str(source)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn(".bkp-", result.stdout)
            backup_path = Path(result.stdout.strip())
            self.assertTrue(backup_path.exists())
            self.assertEqual(backup_path.read_text(), "KEY=value\n")

    def test_cli_backup_custom_name(self):
        """Test backup command with custom name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY=value\n")

            backup = Path(tmpdir) / "backup.env"

            result = subprocess.run(
                [
                    "python3",
                    "envyeet.py",
                    "backup",
                    str(source),
                    "--output",
                    str(backup),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(), "KEY=value\n")

    def test_cli_quiet_mode(self):
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

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_cli_version(self):
        """Test --version flag."""
        result = subprocess.run(
            ["python3", "envyeet.py", "--version"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("0.1.0", result.stdout)

    def test_cli_help(self):
        """Test --help flag."""
        result = subprocess.run(
            ["python3", "envyeet.py", "--help"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("envyeet", result.stdout)
        self.assertIn("merge", result.stdout)
        self.assertIn("backup", result.stdout)

    def test_cli_file_not_found(self):
        """Test error handling for non-existent file."""
        result = subprocess.run(
            ["python3", "envyeet.py", "merge", "nonexistent.env", "target.env"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr)

    def test_cli_verbose_dry_run(self):
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

            self.assertEqual(result.returncode, 0)
            self.assertIn("Keys to update", result.stderr)


if __name__ == "__main__":
    unittest.main()
