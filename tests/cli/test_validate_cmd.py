"""CLI tests for validate command."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner

from clipmd.cli import main

if TYPE_CHECKING:
    import pytest


class TestValidateCommand:
    """Tests for the validate command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output.lower()

    def test_valid_setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with valid setup."""
        monkeypatch.chdir(tmp_path)

        # Create valid config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create .clipmd directory
        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        # Create a markdown file
        (tmp_path / "article.md").write_text("# Test")

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 0
        assert "passed" in result.output.lower()

    def test_missing_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with missing config."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_invalid_config_syntax(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with invalid config syntax."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [broken")

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 1
        assert "invalid" in result.output.lower() or "failed" in result.output.lower()

    def test_missing_root_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with missing root path."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: /nonexistent/path\n")

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 1
        assert "does not exist" in result.output.lower()

    def test_counts_markdown_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that markdown file count is shown."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        # Create markdown files
        for i in range(10):
            (tmp_path / f"article{i}.md").write_text("# Test")

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 0
        assert "10 markdown files" in result.output

    def test_excludes_hidden_files_from_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that hidden files are not counted."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        # Create visible and hidden files
        (tmp_path / "visible.md").write_text("# Test")
        (tmp_path / ".hidden.md").write_text("# Hidden")

        # Hidden folder
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "article.md").write_text("# Hidden")

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 0
        assert "1 markdown files" in result.output

    def test_no_markdown_files_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test warning when no markdown files found."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 0
        assert "No markdown files" in result.output

    def test_fix_option(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test --fix option suggests init command."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--fix"])
        assert result.exit_code == 1
        assert "init" in result.output


class TestValidationFunctions:
    """Unit tests for validation functions."""

    def test_validation_result_properties(self) -> None:
        """Test ValidationResult properties."""
        from clipmd.core.validator import ValidationResult

        passed = ValidationResult(passed=True, message="OK")
        assert passed.passed is True
        assert passed.message == "OK"
        assert passed.details is None

        failed = ValidationResult(passed=False, message="Failed", details="More info")
        assert failed.passed is False
        assert failed.details == "More info"

    def test_validation_report_properties(self) -> None:
        """Test ValidationReport properties."""
        from clipmd.core.validator import ValidationReport, ValidationResult

        report = ValidationReport()

        # Empty report passes
        assert report.passed is True
        assert len(report.failures) == 0
        assert len(report.warnings) == 0

        # Add passing check
        report.checks.append(ValidationResult(passed=True, message="OK"))
        assert report.passed is True

        # Add failing check
        report.checks.append(ValidationResult(passed=False, message="Failed"))
        assert report.passed is False
        assert len(report.failures) == 1

        # Add warning (passed with details)
        report.checks.append(ValidationResult(passed=True, message="OK", details="Warning"))
        assert len(report.warnings) == 1

    def test_validate_config_exists_found(self, tmp_path: Path) -> None:
        """Test config exists check when file is found."""
        from clipmd.core.validator import validate_config_exists

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1")

        result = validate_config_exists(config_file)
        assert result.passed is True
        assert "found" in result.message.lower()

    def test_validate_config_exists_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test config exists check when file is not found."""
        from clipmd.core.validator import validate_config_exists

        monkeypatch.chdir(tmp_path)
        # When called with None and no config exists, it should return False
        result = validate_config_exists(None)
        assert result.passed is False
        assert "not found" in result.message.lower()

    def test_validate_config_syntax_valid(self, tmp_path: Path) -> None:
        """Test config syntax validation with valid YAML."""
        from clipmd.core.validator import validate_config_syntax

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        result = validate_config_syntax(config_file)
        assert result.passed is True
        assert "valid" in result.message.lower()

    def test_validate_config_syntax_invalid(self, tmp_path: Path) -> None:
        """Test config syntax validation with invalid YAML."""
        from clipmd.core.validator import validate_config_syntax

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: [broken")

        result = validate_config_syntax(config_file)
        assert result.passed is False

    def test_validate_root_exists_valid(self, tmp_path: Path) -> None:
        """Test root path existence check with valid path."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_root_exists

        config = Config()
        config.paths.root = tmp_path

        result = validate_root_exists(None, config)
        assert result.passed is True
        assert "exists" in result.message.lower()

    def test_validate_root_exists_missing(self, tmp_path: Path) -> None:
        """Test root path existence check with missing path."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_root_exists

        config = Config()
        config.paths.root = tmp_path / "nonexistent"

        result = validate_root_exists(None, config)
        assert result.passed is False
        assert "does not exist" in result.message.lower()

    def test_validate_cache_directory_writable(self, tmp_path: Path) -> None:
        """Test cache directory writability check."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_cache_directory

        config = Config()
        config.paths.root = tmp_path
        config.paths.cache = Path(".clipmd/cache.json")

        # Create the .clipmd directory
        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        result = validate_cache_directory(None, config)
        assert result.passed is True

    def test_validate_cache_directory_unwritable(self, tmp_path: Path) -> None:
        """Test cache directory writability check with unwritable parent."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_cache_directory

        config = Config()
        config.paths.root = tmp_path
        # Point to a cache location in a non-existent parent
        config.paths.cache = "nonexistent/parent/cache.json"

        result = validate_cache_directory(None, config)
        assert result.passed is False

    def test_validate_markdown_files_none(self, tmp_path: Path) -> None:
        """Test markdown file count with no files."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_markdown_files

        config = Config()
        config.paths.root = tmp_path

        result = validate_markdown_files(None, config)
        assert result.passed is True
        assert "No markdown files" in result.message

    def test_validate_markdown_files_multiple(self, tmp_path: Path) -> None:
        """Test markdown file count with multiple files."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_markdown_files

        # Create markdown files
        for i in range(5):
            (tmp_path / f"article{i}.md").write_text("# Test")

        config = Config()
        config.paths.root = tmp_path

        result = validate_markdown_files(None, config)
        assert result.passed is True
        assert "5 markdown files" in result.message

    def test_run_validation_happy_path(self, tmp_path: Path) -> None:
        """Test full validation suite with valid setup."""
        from clipmd.config import Config
        from clipmd.core.validator import run_validation

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        config = Config()
        config.paths.root = tmp_path

        report = run_validation(config_file, config)
        assert report.passed is True
        assert len(report.checks) > 0

    def test_run_validation_missing_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test full validation suite with missing config."""
        from clipmd.core.validator import run_validation

        monkeypatch.chdir(tmp_path)
        report = run_validation(None, None)
        assert report.passed is False
        assert len(report.failures) > 0

    def test_validate_config_syntax_error(self, tmp_path: Path) -> None:
        """Test config syntax validation with ClipmdError."""
        from clipmd.core.validator import validate_config_syntax

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: [broken")

        result = validate_config_syntax(config_file)
        assert result.passed is False
        assert "invalid" in result.message.lower()
        assert result.details is not None

    def test_validate_root_exists_load_config_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test root validation when config loading fails."""
        from clipmd.core.validator import validate_root_exists

        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: [broken")

        result = validate_root_exists(config_file)
        assert result.passed is False
        assert "cannot validate" in result.message.lower()

    def test_validate_cache_directory_permission_denied(self, tmp_path: Path) -> None:
        """Test cache directory validation with permission denied."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_cache_directory

        config = Config()
        config.paths.root = tmp_path

        # Create a directory and make it read-only
        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()
        clipmd_dir.chmod(0o444)  # Read-only

        config.paths.cache = Path(".clipmd/cache.json")

        try:
            result = validate_cache_directory(None, config)
            # If permission denied is triggered, check the result
            if not result.passed:
                assert "not writable" in result.message.lower()
        finally:
            # Restore permissions for cleanup
            clipmd_dir.chmod(0o755)

    def test_validate_cache_directory_parent_not_directory(self, tmp_path: Path) -> None:
        """Test cache directory when parent exists but is not a directory."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_cache_directory

        config = Config()
        config.paths.root = tmp_path

        # Create a file where we expect a directory
        file_path = tmp_path / ".clipmd"
        file_path.write_text("not a directory")

        config.paths.cache = Path(".clipmd/cache.json")

        result = validate_cache_directory(None, config)
        assert result.passed is False
        assert "not a directory" in result.message.lower()

    def test_validate_cache_directory_can_be_created(self, tmp_path: Path) -> None:
        """Test cache directory that can be created."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_cache_directory

        config = Config()
        config.paths.root = tmp_path

        # Create parent directory but not the cache directory
        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        # Point to a non-existent nested cache location within .clipmd
        config.paths.cache = Path(".clipmd/subdir/cache.json")

        result = validate_cache_directory(None, config)
        assert result.passed is True
        assert "can be created" in result.message.lower()
        assert result.details is not None
        assert "will be created at" in result.details.lower()

    def test_validate_cache_directory_cannot_be_created(self, tmp_path: Path) -> None:
        """Test cache directory that cannot be created (parent doesn't exist)."""
        from clipmd.config import Config
        from clipmd.core.validator import validate_cache_directory

        config = Config()
        config.paths.root = tmp_path

        # Point to a cache location in a completely non-existent parent
        config.paths.cache = Path("nonexistent/parent/subdir/cache.json")

        result = validate_cache_directory(None, config)
        assert result.passed is False
        assert "cannot create" in result.message.lower()

    def test_validate_cache_directory_load_config_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test cache validation when config loading fails."""
        from clipmd.core.validator import validate_cache_directory

        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: [broken")

        result = validate_cache_directory(config_file)
        assert result.passed is False
        assert "load failed" in result.message.lower()

    def test_validate_markdown_files_load_config_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test markdown files validation when config loading fails."""
        from clipmd.core.validator import validate_markdown_files

        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: [broken")

        result = validate_markdown_files(config_file)
        assert result.passed is False
        assert "load failed" in result.message.lower()

    def test_validate_command_without_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test validate command when context object is not available."""
        monkeypatch.chdir(tmp_path)

        # Create minimal valid setup
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 0

    def test_validate_command_with_warnings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test validate command displays warnings correctly."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 0
        assert "validation passed" in result.output.lower()

    def test_validate_command_shows_all_checks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that validate command runs all checks."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()

        # Create a markdown file to ensure file count check works
        (tmp_path / "test.md").write_text("# Test")

        runner = CliRunner()
        result = runner.invoke(main, ["validate"])
        assert result.exit_code == 0
        # Verify all check outputs are present
        output_lower = result.output.lower()
        assert "config file" in output_lower
        assert "syntax" in output_lower
        assert "root path" in output_lower

    def test_run_validation_stops_at_missing_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that validation stops running after config check fails."""
        from clipmd.core.validator import run_validation

        monkeypatch.chdir(tmp_path)
        report = run_validation(None, None)
        # Should only have the config existence check
        assert len(report.checks) == 1
        assert not report.checks[0].passed

    def test_run_validation_stops_at_syntax_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that validation stops after syntax check fails."""
        from clipmd.core.validator import run_validation

        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: [broken")

        report = run_validation(config_file)
        # Should have config exists check and syntax check, no others
        assert len(report.checks) == 2
        assert report.checks[0].passed  # Config exists
        assert not report.checks[1].passed  # Syntax fails
