"""Additional integration tests based on spec.md examples."""

import os
import tempfile
import unittest
from pathlib import Path

from envyeet import merge_env_files, parse_env_file


class TestSpecExamples(unittest.TestCase):
    def test_example_1_basic_merge_no_squash(self):
        """Test Example 1 from spec: Basic merge without squash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / ".env.staging"
            source.write_text("""# Staging database config
DATABASE_URL="postgresql://staging-db:5432/app"
REDIS_HOST="staging-redis"
DEBUG=false

# Staging-only key (won't be added)
STAGING_FEATURE_ENABLED=true
""")

            target = Path(tmpdir) / ".env"
            target.write_text("""# Production database config
DATABASE_URL="postgresql://prod-db:5432/app"
API_KEY="prod-key-123"
REDIS_HOST="prod-redis"
DEBUG=true
""")

            merged = merge_env_files(str(source), str(target), squash=False)
            merged_content = "".join(merged)

            self.assertIn(
                'DATABASE_URL="postgresql://staging-db:5432/app"', merged_content
            )
            self.assertIn('REDIS_HOST="staging-redis"', merged_content)
            self.assertIn("DEBUG=false", merged_content)
            self.assertIn('API_KEY="prod-key-123"', merged_content)
            self.assertNotIn("STAGING_FEATURE_ENABLED", merged_content)

    def test_example_2_merge_with_squash(self):
        """Test Example 2 from spec: Merge with squash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / ".env.staging"
            source.write_text("""# Staging database config
DATABASE_URL="postgresql://staging-db:5432/app"
REDIS_HOST="staging-redis"
DEBUG=false

# Staging-only key (won't be added)
STAGING_FEATURE_ENABLED=true
""")

            target = Path(tmpdir) / ".env"
            target.write_text("""# Production database config
DATABASE_URL="postgresql://prod-db:5432/app"
API_KEY="prod-key-123"
REDIS_HOST="prod-redis"
DEBUG=true
""")

            merged = merge_env_files(str(source), str(target), squash=True)
            merged_content = "".join(merged)

            self.assertIn(
                'DATABASE_URL="postgresql://staging-db:5432/app"', merged_content
            )
            self.assertIn('REDIS_HOST="staging-redis"', merged_content)
            self.assertIn("DEBUG=false", merged_content)
            self.assertIn('API_KEY="prod-key-123"', merged_content)
            self.assertIn("STAGING_FEATURE_ENABLED=true", merged_content)

    def test_example_3_quoting_style_preservation(self):
        """Test Example 3 from spec: Quoting style preservation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / ".env.local"
            source.write_text("""export DATABASE_URL='postgresql://localhost:5432/app'
export DEBUG=false
export TIMEOUT=30
""")

            target = Path(tmpdir) / ".env"
            target.write_text("""export DATABASE_URL="postgresql://remote:5432/app"
export DEBUG="true"
export TIMEOUT="60"
export API_KEY="secret"
""")

            merged = merge_env_files(str(source), str(target), squash=False)
            merged_content = "".join(merged)

            self.assertIn(
                "export DATABASE_URL='postgresql://localhost:5432/app'", merged_content
            )
            self.assertIn("export DEBUG=false", merged_content)
            self.assertIn("export TIMEOUT=30", merged_content)
            self.assertIn('export API_KEY="secret"', merged_content)

    def test_export_keyword_preservation(self):
        """Test that export keyword is preserved when present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("export KEY=value\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY=old\n")

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            self.assertIn("export KEY=value", merged_content)

    def test_mixed_export_and_non_export(self):
        """Test handling of mixed export and non-export lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("export KEY1=value1\nKEY2=value2\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY1=old\nexport KEY2=old\n")

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            self.assertIn("export KEY1=value1", merged_content)
            self.assertIn("export KEY2=value2", merged_content)

    def test_empty_values(self):
        """Test handling of empty values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY1=\nKEY2=value\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY1=old\nKEY3=value3\n")

            merged = merge_env_files(str(source), str(target), squash=True)
            merged_content = "".join(merged)

            self.assertIn("KEY1=", merged_content)
            self.assertIn("KEY2=value", merged_content)

    def test_values_with_special_characters(self):
        """Test handling of values with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text('URL="http://example.com:8080/path?query=value"\n')

            target = Path(tmpdir) / "target.env"
            target.write_text('URL="http://old.com"\n')

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            self.assertIn(
                'URL="http://example.com:8080/path?query=value"', merged_content
            )

    def test_multiline_values(self):
        """Test that multiline values are not supported (as per spec)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text('KEY="value"\n')

            target = Path(tmpdir) / "target.env"
            target.write_text('KEY="old"\n')

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            self.assertIn('KEY="value"', merged_content)

    def test_preserve_line_order(self):
        """Test that the order of keys in target is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY3=value3\nKEY1=value1\nKEY2=value2\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY1=old1\nKEY2=old2\nKEY3=old3\n")

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            key1_pos = merged_content.find("KEY1")
            key2_pos = merged_content.find("KEY2")
            key3_pos = merged_content.find("KEY3")

            self.assertLess(key1_pos, key2_pos)
            self.assertLess(key2_pos, key3_pos)

    def test_comment_preservation_between_keys(self):
        """Test that comments between keys are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY1=value1\nKEY2=value2\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY1=old1\n# Comment between keys\nKEY2=old2\n")

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            self.assertIn("# Comment between keys", merged_content)

    def test_empty_line_preservation_between_keys(self):
        """Test that empty lines between keys are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY1=value1\nKEY2=value2\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY1=old1\n\nKEY2=old2\n")

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            lines = merged_content.split("\n")
            self.assertIn("", lines)

    def test_duplicate_keys_in_source(self):
        """Test that duplicate keys in source use last value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY=value1\nKEY=value2\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY=old\n")

            merged = merge_env_files(str(source), str(target))
            merged_content = "".join(merged)

            self.assertIn("KEY=value2", merged_content)
            self.assertNotIn("KEY=value1", merged_content)

    def test_no_changes_scenario(self):
        """Test when source and target have no overlapping keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.env"
            source.write_text("KEY1=value1\n")

            target = Path(tmpdir) / "target.env"
            target.write_text("KEY2=value2\n")

            merged = merge_env_files(str(source), str(target), squash=False)
            merged_content = "".join(merged)

            self.assertNotIn("KEY1=value1", merged_content)
            self.assertIn("KEY2=value2", merged_content)


if __name__ == "__main__":
    unittest.main()
