"""CLI tests for clipmd."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from clipmd import __version__
from clipmd.cli import Context, main


class TestMainCommand:
    """Tests for the main CLI command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "clipmd" in result.output
        assert "organize" in result.output.lower()

    def test_version(self) -> None:
        """Test --version option."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_verbose_flag(self) -> None:
        """Test -v flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(main, ["-v", "--help"])
        assert result.exit_code == 0

    def test_quiet_flag(self) -> None:
        """Test -q flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(main, ["-q", "--help"])
        assert result.exit_code == 0

    def test_no_color_flag(self) -> None:
        """Test --no-color flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(main, ["--no-color", "--help"])
        assert result.exit_code == 0


class TestVersionCommand:
    """Tests for the version subcommand."""

    def test_version_command(self) -> None:
        """Test version subcommand."""
        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestInvalidConfig:
    """Tests for invalid config handling."""

    def test_invalid_config_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test that invalid config file shows error."""
        monkeypatch.chdir(tmp_path)

        # Create invalid config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        runner = CliRunner()
        result = runner.invoke(main, ["--config", str(config_file), "version"])
        # Should show error message for invalid YAML
        assert result.exit_code != 0 or "Error" in result.output or "error" in result.output.lower()


class TestContext:
    """Tests for CLI context."""

    def test_load_config_caching(self, tmp_path: Path, monkeypatch) -> None:
        """Test that config is cached in context."""
        monkeypatch.chdir(tmp_path)

        # Create valid config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        ctx = Context()
        config1 = ctx.load_config(config_file)
        config2 = ctx.load_config(config_file)

        # Same object should be returned
        assert config1 is config2

    def test_context_defaults(self) -> None:
        """Test context default values."""
        ctx = Context()
        assert ctx.config is None
        assert ctx.verbose == 0
        assert ctx.quiet is False
        assert ctx.no_color is False
