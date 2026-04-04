"""CLI tests for triage command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from clipmd.cli import main


class TestTriageCommand:
    """Tests for the triage command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["triage", "--help"])
        assert result.exit_code == 0
        assert "triage" in result.output.lower()
        assert "fetch" in result.output.lower()

    def test_dry_run_with_empty_config(self, tmp_path: Path) -> None:
        """Test dry-run mode with no RSS/INBOX configured."""
        runner = CliRunner()
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            f"""
version: 1
vault: {tmp_path}
cache: {tmp_path / "cache.json"}
triage:
  rss_sources: []
  inbox_file: null
  staging_folder: "0-To-Categorize"
"""
        )

        result = runner.invoke(
            main,
            ["--config", str(config_file), "triage", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "complete" in result.output.lower()

    def test_staging_override(self, tmp_path: Path) -> None:
        """Test --staging option overrides config."""
        runner = CliRunner()
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            f"""
version: 1
vault: {tmp_path}
cache: {tmp_path / "cache.json"}
triage:
  rss_sources: []
  inbox_file: null
  staging_folder: "default-staging"
"""
        )

        result = runner.invoke(
            main,
            [
                "--config",
                str(config_file),
                "triage",
                "--dry-run",
                "--staging",
                "override-staging",
            ],
        )

        assert result.exit_code == 0

    def test_no_domain_rules_flag(self, tmp_path: Path) -> None:
        """Test --no-domain-rules flag."""
        runner = CliRunner()
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            f"""
version: 1
vault: {tmp_path}
cache: {tmp_path / "cache.json"}
triage:
  rss_sources: []
  inbox_file: null
  staging_folder: "0-To-Categorize"
domain_rules:
  example.com: Example
"""
        )

        result = runner.invoke(
            main,
            [
                "--config",
                str(config_file),
                "triage",
                "--dry-run",
                "--no-domain-rules",
            ],
        )

        assert result.exit_code == 0

    def test_missing_config(self, tmp_path: Path) -> None:
        """Test triage with missing required config fields."""
        runner = CliRunner()
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
version: 1
"""
        )

        result = runner.invoke(
            main,
            ["--config", str(config_file), "triage", "--dry-run"],
        )

        # Should fail because vault is required
        assert result.exit_code != 0

    def test_with_articles_in_root(self, tmp_path: Path) -> None:
        """Test triage with existing articles in vault root."""
        runner = CliRunner()
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            f"""
version: 1
vault: {tmp_path}
cache: {tmp_path / "cache.json"}
triage:
  rss_sources: []
  inbox_file: null
  staging_folder: "0-To-Categorize"
domain_rules:
  example.com: "Example"
"""
        )

        # Create test articles
        article1 = tmp_path / "article1.md"
        article1.write_text(
            """---
title: Test Article 1
source: https://example.com/article1
---

Content 1
"""
        )

        article2 = tmp_path / "article2.md"
        article2.write_text(
            """---
title: Test Article 2
source: https://unknown.com/article2
---

Content 2
"""
        )

        result = runner.invoke(
            main,
            ["--config", str(config_file), "triage", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "complete" in result.output.lower()

    def test_combined_options(self, tmp_path: Path) -> None:
        """Test triage with multiple options combined."""
        runner = CliRunner()
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            f"""
version: 1
vault: {tmp_path}
cache: {tmp_path / "cache.json"}
triage:
  rss_sources: []
  inbox_file: null
  staging_folder: "0-To-Categorize"
"""
        )

        result = runner.invoke(
            main,
            [
                "--config",
                str(config_file),
                "triage",
                "--dry-run",
                "--no-domain-rules",
                "--staging",
                "custom",
            ],
        )

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()

    def test_with_articles_and_domain_rules(self, tmp_path: Path) -> None:
        """Test triage with articles matching domain rules (integration)."""
        runner = CliRunner()
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            f"""
version: 1
vault: {tmp_path}
cache: {tmp_path / "cache.json"}
triage:
  rss_sources: []
  inbox_file: null
  staging_folder: "0-To-Categorize"
domain_rules:
  example.com: "Example-Folder"
  test.org: "Test-Folder"
"""
        )

        # Create test articles
        (tmp_path / "article1.md").write_text(
            "---\ntitle: Article 1\nsource: https://example.com/page1\n---\nContent"
        )
        (tmp_path / "article2.md").write_text(
            "---\ntitle: Article 2\nsource: https://test.org/page2\n---\nContent"
        )
        (tmp_path / "article3.md").write_text(
            "---\ntitle: Article 3\nsource: https://unknown.com/page3\n---\nContent"
        )

        result = runner.invoke(
            main,
            ["--config", str(config_file), "triage", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "complete" in result.output.lower()
        # Dry run should show what would happen
        assert "dry" in result.output.lower()
