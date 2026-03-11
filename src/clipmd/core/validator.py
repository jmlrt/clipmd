"""Core validation logic for clipmd configuration and setup."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from clipmd.config import get_config_file_path, load_config
from clipmd.core.discovery import discover_markdown_files
from clipmd.exceptions import ClipmdError

if TYPE_CHECKING:
    from clipmd.config import Config


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    message: str
    details: str | None = None


@dataclass
class ValidationReport:
    """Complete validation report."""

    checks: list[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if all validations passed."""
        return all(c.passed for c in self.checks)

    @property
    def warnings(self) -> list[ValidationResult]:
        """Get checks that passed but have warnings."""
        return [c for c in self.checks if c.passed and c.details]

    @property
    def failures(self) -> list[ValidationResult]:
        """Get failed checks."""
        return [c for c in self.checks if not c.passed]


def validate_config_exists(config_path: Path | None) -> ValidationResult:
    """Check if config file exists at $XDG_CONFIG_HOME/clipmd/config.yaml.

    Args:
        config_path: Explicit config path or None to use default ($XDG_CONFIG_HOME/clipmd/config.yaml).

    Returns:
        Validation result.
    """
    try:
        path = get_config_file_path(config_path)
    except ClipmdError as e:
        return ValidationResult(
            passed=False,
            message="Config path error",
            details=str(e),
        )

    if not path.exists():
        return ValidationResult(
            passed=False,
            message=f"Config file not found at {path}",
            details=(
                f"Create a config file at {path}. You can use the project's "
                "example-config.yaml as a starting point."
            ),
        )

    return ValidationResult(
        passed=True,
        message=f"Config file found: {path}",
    )


def validate_config_syntax(config_path: Path | None) -> ValidationResult:
    """Check if config file has valid syntax.

    Args:
        config_path: Explicit config path or None to use default.

    Returns:
        Validation result.
    """
    try:
        path = get_config_file_path(config_path)
    except ClipmdError as e:
        return ValidationResult(
            passed=False,
            message="Cannot validate config syntax",
            details=str(e),
        )

    if not path.exists():
        return ValidationResult(
            passed=False,
            message="Cannot validate config syntax - file not found",
        )

    try:
        load_config(path)
        return ValidationResult(
            passed=True,
            message="Config syntax valid",
        )
    except ClipmdError as e:
        return ValidationResult(
            passed=False,
            message="Config syntax invalid",
            details=str(e),
        )


def validate_root_exists(
    config_path: Path | None, config: Config | None = None
) -> ValidationResult:
    """Check if vault root path exists.

    Args:
        config_path: Explicit config path or None to use default.
        config: Already-loaded config or None to load from disk.

    Returns:
        Validation result.
    """
    # Use provided config or load from disk
    if config is None:
        try:
            path = get_config_file_path(config_path)
        except ClipmdError as e:
            return ValidationResult(
                passed=False,
                message="Cannot validate vault root",
                details=str(e),
            )

        if not path.exists():
            return ValidationResult(
                passed=False,
                message="Cannot validate vault root - config not found",
            )

        try:
            config = load_config(path)
        except Exception as e:
            return ValidationResult(
                passed=False,
                message="Cannot validate vault root",
                details=str(e),
            )

    try:
        root = config.vault
        if root is None:
            return ValidationResult(
                passed=False,
                message="Vault path not configured",
            )

        if root.exists() and root.is_dir():
            return ValidationResult(
                passed=True,
                message=f"Vault path exists: {root.resolve()}",
            )
        return ValidationResult(
            passed=False,
            message=f"Vault path does not exist: {root}",
        )
    except Exception as e:
        return ValidationResult(
            passed=False,
            message="Cannot validate vault root",
            details=str(e),
        )


def validate_cache_directory(
    config_path: Path | None, config: Config | None = None
) -> ValidationResult:
    """Check if cache directory is writable.

    Args:
        config_path: Explicit config path or None to use default.
        config: Already-loaded config or None to load from disk.

    Returns:
        Validation result.
    """
    # Use provided config or load from disk
    if config is None:
        try:
            path = get_config_file_path(config_path)
        except ClipmdError as e:
            return ValidationResult(
                passed=False,
                message="Cannot validate cache directory",
                details=str(e),
            )

        if not path.exists():
            return ValidationResult(
                passed=False,
                message="Cannot validate cache directory - config not found",
            )

        try:
            config = load_config(path)
        except Exception as e:
            return ValidationResult(
                passed=False,
                message="Cannot validate cache directory - config load failed",
                details=str(e),
            )

    try:
        cache_path = config.cache
        if cache_path is None:
            return ValidationResult(
                passed=False,
                message="Cache path not configured",
            )

        cache_dir = cache_path.parent

        # Check if parent directory exists or can be created
        if cache_dir.exists():
            if cache_dir.is_dir():
                # Try to check if writable
                test_file = cache_dir / ".clipmd_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                    return ValidationResult(
                        passed=True,
                        message="Cache directory writable",
                    )
                except PermissionError:
                    return ValidationResult(
                        passed=False,
                        message=f"Cache directory not writable: {cache_dir}",
                    )
            return ValidationResult(
                passed=False,
                message=f"Cache path parent is not a directory: {cache_dir}",
            )

        # Directory doesn't exist, check if parent is writable
        parent = cache_dir.parent
        if parent.exists() and parent.is_dir():
            return ValidationResult(
                passed=True,
                message="Cache directory can be created",
                details=f"Will be created at: {cache_dir}",
            )

        return ValidationResult(
            passed=False,
            message=f"Cannot create cache directory: {cache_dir}",
        )

    except Exception as e:
        return ValidationResult(
            passed=False,
            message="Cannot validate cache directory",
            details=str(e),
        )


def validate_markdown_files(
    config_path: Path | None, config: Config | None = None
) -> ValidationResult:
    """Count markdown files in vault directory.

    Args:
        config_path: Explicit config path or None to use default.
        config: Already-loaded config or None to load from disk.

    Returns:
        Validation result with file count.
    """
    # Use provided config or load from disk
    if config is None:
        try:
            path = get_config_file_path(config_path)
        except ClipmdError as e:
            return ValidationResult(
                passed=False,
                message="Cannot count files",
                details=str(e),
            )

        if not path.exists():
            return ValidationResult(
                passed=False,
                message="Cannot count files - config not found",
            )

        try:
            config = load_config(path)
        except Exception as e:
            return ValidationResult(
                passed=False,
                message="Cannot count files - config load failed",
                details=str(e),
            )

    try:
        root = config.vault
        if root is None:
            return ValidationResult(
                passed=False,
                message="Cannot count files - vault path not configured",
            )

        # Count markdown files, excluding hidden and ignored files
        md_files = list(discover_markdown_files(root, config))
        count = len(md_files)

        if count == 0:
            return ValidationResult(
                passed=True,
                message="No markdown files found",
                details="Add some articles or run 'clipmd fetch'",
            )

        return ValidationResult(
            passed=True,
            message=f"{count} markdown files found",
        )

    except Exception as e:
        return ValidationResult(
            passed=False,
            message="Cannot count markdown files",
            details=str(e),
        )


def run_validation(config_path: Path | None, config: Config | None = None) -> ValidationReport:
    """Run all validation checks.

    Args:
        config_path: Explicit config path or None to search.
        config: Already-loaded config (with resolved vault root) or None to load from disk.

    Returns:
        Complete validation report.
    """

    report = ValidationReport()

    # Run checks in order
    report.checks.append(validate_config_exists(config_path))

    # Only run remaining checks if config exists
    if report.checks[-1].passed:
        report.checks.append(validate_config_syntax(config_path))

        # Only continue if syntax is valid
        if report.checks[-1].passed:
            report.checks.append(validate_root_exists(config_path, config))
            report.checks.append(validate_cache_directory(config_path, config))
            report.checks.append(validate_markdown_files(config_path, config))

    return report
