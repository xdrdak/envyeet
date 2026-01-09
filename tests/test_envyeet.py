"""Tests for envyeet CLI."""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from envyeet import (
    EnvLine,
    backup_file,
    cmd_backup,
    cmd_merge,
    generate_line,
    is_tty,
    merge_env_files,
    parse_env_file,
    prompt_confirmation,
    write_output,
)


class TestEnvLine(unittest.TestCase):
    def test_env_line_creation(self):
        line = EnvLine(
            raw="KEY=value\n",
            key="KEY",
            value="value",
            quote_style=None,
            is_export=False,
            is_comment=False,
            is_empty=False,
        )
        self.assertEqual(line.raw, "KEY=value\n")
        self.assertEqual(line.key, "KEY")
        self.assertEqual(line.value, "value")
        self.assertIsNone(line.quote_style)

    def test_env_line_repr(self):
        line = EnvLine(raw="KEY=value\n", key="KEY", value="value")
        repr_str = repr(line)
        self.assertIn("KEY", repr_str)
        self.assertIn("value", repr_str)


class TestParseEnvFile(unittest.TestCase):
    def test_parse_simple_key_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "test.env"
            env_file.write_text("KEY1=value1\nKEY2=value2\n")

            env_dict, lines = parse_env_file(str(env_file))

            self.assertEqual(len(env_dict), 2)
            self.assertEqual(env_dict["KEY1"].value, "value1")
            self.assertEqual(env_dict["KEY2"].value, "value2")
            self.assertEqual(len(lines), 2)

    def test_parse_with_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "test.env"
            env_file.write_text("export KEY=value\n")

            env_dict, lines = parse_env_file(str(env_file))

            self.assertEqual(len(env_dict), 1)
            self.assertEqual(env_dict["KEY"].value, "value")
            self.assertTrue(env_dict["KEY"].is_export)

    def test_parse_with_quotes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "test.env"
            env_file.write_text("KEY1=\"value1\"\nKEY2='value2'\nKEY3=value3\n")

            env_dict, lines = parse_env_file(str(env_file))

            self.assertEqual(env_dict["KEY1"].value, "value1")
            self.assertEqual(env_dict["KEY1"].quote_style, '"')
            self.assertEqual(env_dict["KEY2"].value, "value2")
            self.assertEqual(env_dict["KEY2"].quote_style, "'")
            self.assertEqual(env_dict["KEY3"].value, "value3")
            self.assertIsNone(env_dict["KEY3"].quote_style)

    def test_parse_with_comments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "test.env"
            env_file.write_text("# Comment\nKEY=value\n# Another comment\n")

            env_dict, lines = parse_env_file(str(env_file))

            self.assertEqual(len(env_dict), 1)
            self.assertEqual(env_dict["KEY"].value, "value")
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[0].is_comment)
            self.assertTrue(lines[2].is_comment)

    def test_parse_with_empty_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "test.env"
            env_file.write_text("\nKEY=value\n\n")

            env_dict, lines = parse_env_file(str(env_file))

            self.assertEqual(len(env_dict), 1)
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[0].is_empty)
            self.assertTrue(lines[2].is_empty)

    def test_parse_malformed_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "test.env"
            env_file.write_text("KEY=value\nINVALID LINE\n")

            env_dict, lines = parse_env_file(str(env_file))

            self.assertEqual(len(env_dict), 1)
            self.assertEqual(len(lines), 2)

    def test_parse_malformed_line_verbose(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "test.env"
            env_file.write_text("KEY=value\nINVALID LINE\n")

            stderr_capture = io.StringIO()
            with patch("sys.stderr", stderr_capture):
                env_dict, lines = parse_env_file(str(env_file), verbose=True)

            captured = stderr_capture.getvalue()
            self.assertIn("Skipping malformed line", captured)

    def test_parse_file_not_found(self):
        with self.assertRaises(ValueError) as context:
            parse_env_file("nonexistent.env")
        self.assertIn("not found", str(context.exception))


class TestGenerateLine(unittest.TestCase):
    def test_generate_unquoted(self):
        line = generate_line("KEY", "value", is_export=False, quote_style=None)
        self.assertEqual(line, "KEY=value\n")

    def test_generate_single_quoted(self):
        line = generate_line("KEY", "value", is_export=False, quote_style="'")
        self.assertEqual(line, "KEY='value'\n")

    def test_generate_double_quoted(self):
        line = generate_line("KEY", "value", is_export=False, quote_style='"')
        self.assertEqual(line, 'KEY="value"\n')

    def test_generate_with_export(self):
        line = generate_line("KEY", "value", is_export=True, quote_style=None)
        self.assertEqual(line, "export KEY=value\n")

    def test_generate_none_value(self):
        line = generate_line("KEY", None, is_export=False, quote_style=None)
        self.assertEqual(line, "KEY=\n")


class TestMergeEnvFiles(unittest.TestCase):
    def test_basic_merge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("DATABASE_URL=staging\nDEBUG=false\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("DATABASE_URL=production\nAPI_KEY=secret\nDEBUG=true\n")

            merged = merge_env_files(str(source), str(target), squash=False)
            merged_content = "".join(merged)

            self.assertIn("DATABASE_URL=staging", merged_content)
            self.assertIn("DEBUG=false", merged_content)
            self.assertIn("API_KEY=secret", merged_content)

    def test_merge_with_squash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("DATABASE_URL=staging\nNEW_KEY=new_value\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("DATABASE_URL=production\nAPI_KEY=secret\n")

            merged = merge_env_files(str(source), str(target), squash=True)
            merged_content = "".join(merged)

            self.assertIn("DATABASE_URL=staging", merged_content)
            self.assertIn("API_KEY=secret", merged_content)
            self.assertIn("NEW_KEY=new_value", merged_content)

    def test_merge_preserves_quotes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY='value'\n")

            target = Path(tmpdir) / "target.env"
            target.write_text('KEY="old"\n')

            merged = merge_env_files(str(source), str(target), squash=False)
            merged_content = "".join(merged)

            self.assertIn("KEY='value'", merged_content)

    def test_merge_preserves_comments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY=value\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("# Comment\nKEY=old\n")

            merged = merge_env_files(str(source), str(target), squash=False)
            merged_content = "".join(merged)

            self.assertIn("# Comment", merged_content)

    def test_merge_preserves_empty_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY=value\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("\nKEY=old\n")

            merged = merge_env_files(str(source), str(target), squash=False)
            merged_content = "".join(merged)

            self.assertGreaterEqual(merged_content.count("\n"), 2)

    def test_merge_preserves_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY1=val1\nKEY2=val2\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY2=old2\nKEY1=old1\n")

            merged = merge_env_files(str(source), str(target), squash=False)
            merged_content = "".join(merged)

            key1_pos = merged_content.find("KEY1")
            key2_pos = merged_content.find("KEY2")
            self.assertLess(key2_pos, key1_pos)

    def test_merge_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY=value\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY=old\n")

            stderr_capture = io.StringIO()
            with patch("sys.stderr", stderr_capture):
                merge_env_files(str(source), str(target), dry_run=True, verbose=True)

            captured = stderr_capture.getvalue()
            self.assertIn("Keys to update", captured)


class TestBackupFile(unittest.TestCase):
    def test_backup_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = Path(tmpdir) / "original.env"
            original.write_text("KEY=value\n")

            backup_path = backup_file(str(original))

            self.assertTrue(os.path.exists(backup_path))
            self.assertEqual(Path(backup_path).read_text(), "KEY=value\n")

    def test_backup_with_custom_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = Path(tmpdir) / "original.env"
            original.write_text("KEY=value\n")

            custom_backup = Path(tmpdir) / "custom.env"
            backup_path = backup_file(str(original), str(custom_backup))

            self.assertEqual(backup_path, str(custom_backup))
            self.assertTrue(custom_backup.exists())
            self.assertEqual(custom_backup.read_text(), "KEY=value\n")

    def test_backup_file_exists_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = Path(tmpdir) / "original.env"
            original.write_text("KEY=value\n")

            existing = Path(tmpdir) / "existing.env"
            existing.write_text("OLD=value\n")

            with self.assertRaises(ValueError) as context:
                backup_file(str(original), str(existing))
            self.assertIn("already exists", str(context.exception))

    def test_backup_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent.env"

            with self.assertRaises(ValueError) as context:
                backup_file(str(nonexistent))
            self.assertIn("not found", str(context.exception))


class TestIsTty(unittest.TestCase):
    def test_is_tty(self):
        self.assertIsInstance(is_tty(), bool)


class TestPromptConfirmation(unittest.TestCase):
    def test_prompt_confirmation(self):
        with patch("sys.stdout.isatty", return_value=True):
            with patch("builtins.input", return_value="y"):
                self.assertTrue(prompt_confirmation("Test?"))

    def test_prompt_confirmation_no(self):
        with patch("sys.stdout.isatty", return_value=True):
            with patch("builtins.input", return_value="n"):
                self.assertFalse(prompt_confirmation("Test?"))

    def test_prompt_confirmation_not_tty(self):
        with patch("sys.stdout.isatty", return_value=False):
            self.assertFalse(prompt_confirmation("Test?"))


class TestWriteOutput(unittest.TestCase):
    def test_write_to_stdout(self):
        content = ["LINE1\n", "LINE2\n"]
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            write_output(content, None, quiet=False)

        captured = stdout_capture.getvalue()
        self.assertIn("LINE1", captured)
        self.assertIn("LINE2", captured)

    def test_write_quiet(self):
        content = ["LINE1\n"]
        stdout_capture = io.StringIO()
        with patch("sys.stdout", stdout_capture):
            write_output(content, None, quiet=True)

        captured = stdout_capture.getvalue()
        self.assertNotIn("LINE1", captured)

    def test_write_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = ["LINE1\n", "LINE2\n"]
            output_file = Path(tmpdir) / "output.txt"

            write_output(content, str(output_file), quiet=False)

            self.assertTrue(output_file.exists())
            self.assertEqual(output_file.read_text(), "LINE1\nLINE2\n")


class TestIntegration(unittest.TestCase):
    def test_full_merge_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("DATABASE_URL=staging\nDEBUG=false\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("DATABASE_URL=production\nAPI_KEY=secret\nDEBUG=true\n")

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            self.assertIn("DATABASE_URL=staging", merged_content)
            self.assertIn("DEBUG=false", merged_content)
            self.assertIn("API_KEY=secret", merged_content)

    def test_backup_and_merge_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original = Path(tmpdir) / "target.env"
            original.write_text("KEY=old\n")

            backup_file(str(original))

            source = Path(tmpdir) / "source.env"
            source.write_text("KEY=new\n")

            merged = merge_env_files(str(source), str(original))
            merged_content = "".join(merged)

            self.assertIn("KEY=new", merged_content)
            self.assertEqual(original.read_text(), "KEY=old\n")


if __name__ == "__main__":
    unittest.main()
