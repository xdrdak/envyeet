"""Tests for envyeet CLI."""

import os
import tempfile
from pathlib import Path

import pytest

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


class TestEnvLine:
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
        assert line.raw == "KEY=value\n"
        assert line.key == "KEY"
        assert line.value == "value"
        assert line.quote_style is None

    def test_env_line_repr(self):
        line = EnvLine(raw="KEY=value\n", key="KEY", value="value")
        repr_str = repr(line)
        assert "KEY" in repr_str
        assert "value" in repr_str


class TestParseEnvFile:
    def test_parse_simple_key_value(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text("KEY1=value1\nKEY2=value2\n")

        env_dict, lines = parse_env_file(str(env_file))

        assert len(env_dict) == 2
        assert env_dict["KEY1"].value == "value1"
        assert env_dict["KEY2"].value == "value2"
        assert len(lines) == 2

    def test_parse_with_export(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text("export KEY=value\n")

        env_dict, lines = parse_env_file(str(env_file))

        assert len(env_dict) == 1
        assert env_dict["KEY"].value == "value"
        assert env_dict["KEY"].is_export is True

    def test_parse_with_quotes(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text("KEY1=\"value1\"\nKEY2='value2'\nKEY3=value3\n")

        env_dict, lines = parse_env_file(str(env_file))

        assert env_dict["KEY1"].value == "value1"
        assert env_dict["KEY1"].quote_style == '"'
        assert env_dict["KEY2"].value == "value2"
        assert env_dict["KEY2"].quote_style == "'"
        assert env_dict["KEY3"].value == "value3"
        assert env_dict["KEY3"].quote_style is None

    def test_parse_with_comments(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text("# Comment\nKEY=value\n# Another comment\n")

        env_dict, lines = parse_env_file(str(env_file))

        assert len(env_dict) == 1
        assert env_dict["KEY"].value == "value"
        assert len(lines) == 3
        assert lines[0].is_comment is True
        assert lines[2].is_comment is True

    def test_parse_with_empty_lines(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text("\nKEY=value\n\n")

        env_dict, lines = parse_env_file(str(env_file))

        assert len(env_dict) == 1
        assert len(lines) == 3
        assert lines[0].is_empty is True
        assert lines[2].is_empty is True

    def test_parse_malformed_line(self, tmp_path, capsys):
        env_file = tmp_path / "test.env"
        env_file.write_text("KEY=value\nINVALID LINE\n")

        env_dict, lines = parse_env_file(str(env_file))

        assert len(env_dict) == 1
        assert len(lines) == 2

    def test_parse_malformed_line_verbose(self, tmp_path, capsys):
        env_file = tmp_path / "test.env"
        env_file.write_text("KEY=value\nINVALID LINE\n")

        env_dict, lines = parse_env_file(str(env_file), verbose=True)

        captured = capsys.readouterr()
        assert "Skipping malformed line" in captured.err

    def test_parse_file_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            parse_env_file("nonexistent.env")


class TestGenerateLine:
    def test_generate_unquoted(self):
        line = generate_line("KEY", "value", is_export=False, quote_style=None)
        assert line == "KEY=value\n"

    def test_generate_single_quoted(self):
        line = generate_line("KEY", "value", is_export=False, quote_style="'")
        assert line == "KEY='value'\n"

    def test_generate_double_quoted(self):
        line = generate_line("KEY", "value", is_export=False, quote_style='"')
        assert line == 'KEY="value"\n'

    def test_generate_with_export(self):
        line = generate_line("KEY", "value", is_export=True, quote_style=None)
        assert line == "export KEY=value\n"

    def test_generate_none_value(self):
        line = generate_line("KEY", None, is_export=False, quote_style=None)
        assert line == "KEY=\n"


class TestMergeEnvFiles:
    def test_basic_merge(self, tmp_path):
        source = tmp_path / "source.env"
        source.write_text("DATABASE_URL=staging\nDEBUG=false\n")

        target = tmp_path / "target.env"
        target.write_text("DATABASE_URL=production\nAPI_KEY=secret\nDEBUG=true\n")

        merged = merge_env_files(str(source), str(target), squash=False)
        merged_content = "".join(merged)

        assert "DATABASE_URL=staging" in merged_content
        assert "DEBUG=false" in merged_content
        assert "API_KEY=secret" in merged_content

    def test_merge_with_squash(self, tmp_path):
        source = tmp_path / "source.env"
        source.write_text("DATABASE_URL=staging\nNEW_KEY=new_value\n")

        target = tmp_path / "target.env"
        target.write_text("DATABASE_URL=production\nAPI_KEY=secret\n")

        merged = merge_env_files(str(source), str(target), squash=True)
        merged_content = "".join(merged)

        assert "DATABASE_URL=staging" in merged_content
        assert "API_KEY=secret" in merged_content
        assert "NEW_KEY=new_value" in merged_content

    def test_merge_preserves_quotes(self, tmp_path):
        source = tmp_path / "source.env"
        source.write_text("KEY='value'\n")

        target = tmp_path / "target.env"
        target.write_text('KEY="old"\n')

        merged = merge_env_files(str(source), str(target), squash=False)
        merged_content = "".join(merged)

        assert "KEY='value'" in merged_content

    def test_merge_preserves_comments(self, tmp_path):
        source = tmp_path / "source.env"
        source.write_text("KEY=value\n")

        target = tmp_path / "target.env"
        target.write_text("# Comment\nKEY=old\n")

        merged = merge_env_files(str(source), str(target), squash=False)
        merged_content = "".join(merged)

        assert "# Comment" in merged_content

    def test_merge_preserves_empty_lines(self, tmp_path):
        source = tmp_path / "source.env"
        source.write_text("KEY=value\n")

        target = tmp_path / "target.env"
        target.write_text("\nKEY=old\n")

        merged = merge_env_files(str(source), str(target), squash=False)
        merged_content = "".join(merged)

        assert merged_content.count("\n") >= 2

    def test_merge_preserves_order(self, tmp_path):
        source = tmp_path / "source.env"
        source.write_text("KEY1=val1\nKEY2=val2\n")

        target = tmp_path / "target.env"
        target.write_text("KEY2=old2\nKEY1=old1\n")

        merged = merge_env_files(str(source), str(target), squash=False)
        merged_content = "".join(merged)

        key1_pos = merged_content.find("KEY1")
        key2_pos = merged_content.find("KEY2")
        assert key2_pos < key1_pos

    def test_merge_dry_run(self, tmp_path, capsys):
        source = tmp_path / "source.env"
        source.write_text("KEY=value\n")

        target = tmp_path / "target.env"
        target.write_text("KEY=old\n")

        merge_env_files(str(source), str(target), dry_run=True, verbose=True)

        captured = capsys.readouterr()
        assert "Keys to update" in captured.err


class TestBackupFile:
    def test_backup_creates_file(self, tmp_path):
        original = tmp_path / "original.env"
        original.write_text("KEY=value\n")

        backup_path = backup_file(str(original))

        assert os.path.exists(backup_path)
        assert Path(backup_path).read_text() == "KEY=value\n"

    def test_backup_with_custom_name(self, tmp_path):
        original = tmp_path / "original.env"
        original.write_text("KEY=value\n")

        custom_backup = tmp_path / "custom.env"
        backup_path = backup_file(str(original), str(custom_backup))

        assert backup_path == str(custom_backup)
        assert custom_backup.exists()
        assert custom_backup.read_text() == "KEY=value\n"

    def test_backup_file_exists_error(self, tmp_path):
        original = tmp_path / "original.env"
        original.write_text("KEY=value\n")

        existing = tmp_path / "existing.env"
        existing.write_text("OLD=value\n")

        with pytest.raises(ValueError, match="already exists"):
            backup_file(str(original), str(existing))

    def test_backup_file_not_found(self, tmp_path):
        nonexistent = tmp_path / "nonexistent.env"

        with pytest.raises(ValueError, match="not found"):
            backup_file(str(nonexistent))


class TestIsTty:
    def test_is_tty(self, monkeypatch):
        assert isinstance(is_tty(), bool)


class TestPromptConfirmation:
    def test_prompt_confirmation(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert prompt_confirmation("Test?") is True

    def test_prompt_confirmation_no(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert prompt_confirmation("Test?") is False

    def test_prompt_confirmation_not_tty(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: False)
        assert prompt_confirmation("Test?") is False


class TestWriteOutput:
    def test_write_to_stdout(self, capsys):
        content = ["LINE1\n", "LINE2\n"]
        write_output(content, None, quiet=False)

        captured = capsys.readouterr()
        assert "LINE1" in captured.out
        assert "LINE2" in captured.out

    def test_write_quiet(self, capsys):
        content = ["LINE1\n"]
        write_output(content, None, quiet=True)

        captured = capsys.readouterr()
        assert "LINE1" not in captured.out

    def test_write_to_file(self, tmp_path):
        content = ["LINE1\n", "LINE2\n"]
        output_file = tmp_path / "output.txt"

        write_output(content, str(output_file), quiet=False)

        assert output_file.exists()
        assert output_file.read_text() == "LINE1\nLINE2\n"


class TestIntegration:
    def test_full_merge_workflow(self, tmp_path):
        source = tmp_path / "source.env"
        source.write_text("DATABASE_URL=staging\nDEBUG=false\n")

        target = tmp_path / "target.env"
        target.write_text("DATABASE_URL=production\nAPI_KEY=secret\nDEBUG=true\n")

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        assert "DATABASE_URL=staging" in merged_content
        assert "DEBUG=false" in merged_content
        assert "API_KEY=secret" in merged_content

    def test_backup_and_merge_workflow(self, tmp_path):
        original = tmp_path / "target.env"
        original.write_text("KEY=old\n")

        backup_file(str(original))

        source = tmp_path / "source.env"
        source.write_text("KEY=new\n")

        merged = merge_env_files(str(source), str(original))
        merged_content = "".join(merged)

        assert "KEY=new" in merged_content
        assert original.read_text() == "KEY=old\n"
