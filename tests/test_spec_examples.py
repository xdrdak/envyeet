"""Additional integration tests based on spec.md examples."""

import os
import tempfile
from pathlib import Path

import pytest

from envyeet import merge_env_files, parse_env_file


class TestSpecExamples:
    def test_example_1_basic_merge_no_squash(self, tmp_path):
        """Test Example 1 from spec: Basic merge without squash."""
        source = tmp_path / ".env.staging"
        source.write_text("""# Staging database config
DATABASE_URL="postgresql://staging-db:5432/app"
REDIS_HOST="staging-redis"
DEBUG=false

# Staging-only key (won't be added)
STAGING_FEATURE_ENABLED=true
""")

        target = tmp_path / ".env"
        target.write_text("""# Production database config
DATABASE_URL="postgresql://prod-db:5432/app"
API_KEY="prod-key-123"
REDIS_HOST="prod-redis"
DEBUG=true
""")

        merged = merge_env_files(str(source), str(target), squash=False)
        merged_content = "".join(merged)

        assert 'DATABASE_URL="postgresql://staging-db:5432/app"' in merged_content
        assert 'REDIS_HOST="staging-redis"' in merged_content
        assert "DEBUG=false" in merged_content
        assert 'API_KEY="prod-key-123"' in merged_content
        assert "STAGING_FEATURE_ENABLED" not in merged_content

    def test_example_2_merge_with_squash(self, tmp_path):
        """Test Example 2 from spec: Merge with squash."""
        source = tmp_path / ".env.staging"
        source.write_text("""# Staging database config
DATABASE_URL="postgresql://staging-db:5432/app"
REDIS_HOST="staging-redis"
DEBUG=false

# Staging-only key (won't be added)
STAGING_FEATURE_ENABLED=true
""")

        target = tmp_path / ".env"
        target.write_text("""# Production database config
DATABASE_URL="postgresql://prod-db:5432/app"
API_KEY="prod-key-123"
REDIS_HOST="prod-redis"
DEBUG=true
""")

        merged = merge_env_files(str(source), str(target), squash=True)
        merged_content = "".join(merged)

        assert 'DATABASE_URL="postgresql://staging-db:5432/app"' in merged_content
        assert 'REDIS_HOST="staging-redis"' in merged_content
        assert "DEBUG=false" in merged_content
        assert 'API_KEY="prod-key-123"' in merged_content
        assert "STAGING_FEATURE_ENABLED=true" in merged_content

    def test_example_3_quoting_style_preservation(self, tmp_path):
        """Test Example 3 from spec: Quoting style preservation."""
        source = tmp_path / ".env.local"
        source.write_text("""export DATABASE_URL='postgresql://localhost:5432/app'
export DEBUG=false
export TIMEOUT=30
""")

        target = tmp_path / ".env"
        target.write_text("""export DATABASE_URL="postgresql://remote:5432/app"
export DEBUG="true"
export TIMEOUT="60"
export API_KEY="secret"
""")

        merged = merge_env_files(str(source), str(target), squash=False)
        merged_content = "".join(merged)

        assert "export DATABASE_URL='postgresql://localhost:5432/app'" in merged_content
        assert "export DEBUG=false" in merged_content
        assert "export TIMEOUT=30" in merged_content
        assert 'export API_KEY="secret"' in merged_content

    def test_export_keyword_preservation(self, tmp_path):
        """Test that export keyword is preserved when present."""
        source = tmp_path / "source.env"
        source.write_text("export KEY=value\n")

        target = tmp_path / "target.env"
        target.write_text("KEY=old\n")

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        assert "export KEY=value" in merged_content

    def test_mixed_export_and_non_export(self, tmp_path):
        """Test handling of mixed export and non-export lines."""
        source = tmp_path / "source.env"
        source.write_text("export KEY1=value1\nKEY2=value2\n")

        target = tmp_path / "target.env"
        target.write_text("KEY1=old\nexport KEY2=old\n")

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        assert "export KEY1=value1" in merged_content
        assert "export KEY2=value2" in merged_content

    def test_empty_values(self, tmp_path):
        """Test handling of empty values."""
        source = tmp_path / "source.env"
        source.write_text("KEY1=\nKEY2=value\n")

        target = tmp_path / "target.env"
        target.write_text("KEY1=old\nKEY3=value3\n")

        merged = merge_env_files(str(source), str(target), squash=True)
        merged_content = "".join(merged)

        assert "KEY1=" in merged_content
        assert "KEY2=value" in merged_content

    def test_values_with_special_characters(self, tmp_path):
        """Test handling of values with special characters."""
        source = tmp_path / "source.env"
        source.write_text('URL="http://example.com:8080/path?query=value"\n')

        target = tmp_path / "target.env"
        target.write_text('URL="http://old.com"\n')

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        assert 'URL="http://example.com:8080/path?query=value"' in merged_content

    def test_multiline_values(self, tmp_path):
        """Test that multiline values are not supported (as per spec)."""
        source = tmp_path / "source.env"
        source.write_text('KEY="value"\n')

        target = tmp_path / "target.env"
        target.write_text('KEY="old"\n')

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        assert 'KEY="value"' in merged_content

    def test_preserve_line_order(self, tmp_path):
        """Test that the order of keys in target is preserved."""
        source = tmp_path / "source.env"
        source.write_text("KEY3=value3\nKEY1=value1\nKEY2=value2\n")

        target = tmp_path / "target.env"
        target.write_text("KEY1=old1\nKEY2=old2\nKEY3=old3\n")

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        key1_pos = merged_content.find("KEY1")
        key2_pos = merged_content.find("KEY2")
        key3_pos = merged_content.find("KEY3")

        assert key1_pos < key2_pos < key3_pos

    def test_comment_preservation_between_keys(self, tmp_path):
        """Test that comments between keys are preserved."""
        source = tmp_path / "source.env"
        source.write_text("KEY1=value1\nKEY2=value2\n")

        target = tmp_path / "target.env"
        target.write_text("KEY1=old1\n# Comment between keys\nKEY2=old2\n")

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        assert "# Comment between keys" in merged_content

    def test_empty_line_preservation_between_keys(self, tmp_path):
        """Test that empty lines between keys are preserved."""
        source = tmp_path / "source.env"
        source.write_text("KEY1=value1\nKEY2=value2\n")

        target = tmp_path / "target.env"
        target.write_text("KEY1=old1\n\nKEY2=old2\n")

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        lines = merged_content.split("\n")
        assert "" in lines

    def test_duplicate_keys_in_source(self, tmp_path):
        """Test that duplicate keys in source use last value."""
        source = tmp_path / "source.env"
        source.write_text("KEY=value1\nKEY=value2\n")

        target = tmp_path / "target.env"
        target.write_text("KEY=old\n")

        merged = merge_env_files(str(source), str(target))
        merged_content = "".join(merged)

        assert "KEY=value2" in merged_content
        assert "KEY=value1" not in merged_content

    def test_no_changes_scenario(self, tmp_path):
        """Test when source and target have no overlapping keys."""
        source = tmp_path / "source.env"
        source.write_text("KEY1=value1\n")

        target = tmp_path / "target.env"
        target.write_text("KEY2=value2\n")

        merged = merge_env_files(str(source), str(target), squash=False)
        merged_content = "".join(merged)

        assert "KEY1=value1" not in merged_content
        assert "KEY2=value2" in merged_content
