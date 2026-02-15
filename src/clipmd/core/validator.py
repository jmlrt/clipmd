"""Core validation logic for clipmd configuration and setup."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from clipmd.config import find_config_file, load_config
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
    """Check if config file exists.

    Args:
        config_path: Explicit config path or None to search.

    Returns:
        Validation result.
    """
    path = find_config_file(config_path)
    if path is None:
        return ValidationResult(
            passed=False,
            message="Config file not found",
            details="Run 'clipmd init' to create one",
        )

    return ValidationResult(
        passed=True,
        message=f"Config file found: {path}",
    )


def validate_config_syntax(config_path: Path | None) -> ValidationResult:
    """Check if config file has valid syntax.

    Args:
        config_path: Explicit config path or None to search.

    Returns:
        Validation result.
    """
    path = find_config_file(config_path)
    if path is None:
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
    """Check if root path exists.

    Args:
        config_path: Explicit config path or None to search.
        config: Already-loaded config (with resolved vault root) or None to load from disk.

    Returns:
        Validation result.
    """
    # Use provided config or load from disk
    if config is None:
        path = find_config_file(config_path)
        if path is None:
            return ValidationResult(
                passed=False,
                message="Cannot validate root path - config not found",
            )
        try:
            config = load_config(path)
        except Exception as e:
            return ValidationResult(
                passed=False,
                message="Cannot validate root path",
                details=str(e),
            )

    try:
        root = config.paths.root
        if root.exists() and root.is_dir():
            return ValidationResult(
                passed=True,
                message=f"Root path exists: {root.resolve()}",
            )
        return ValidationResult(
            passed=False,
            message=f"Root path does not exist: {root}",
        )
    except Exception as e:
        return ValidationResult(
            passed=False,
            message="Cannot validate root path",
            details=str(e),
        )


def validate_cache_directory(
    config_path: Path | None, config: Config | None = None
) -> ValidationResult:
    """Check if cache directory is writable.

    Args:
        config_path: Explicit config path or None to search.
        config: Already-loaded config (with resolved vault root) or None to load from disk.

    Returns:
        Validation result.
    """
    # Use provided config or load from disk
    if config is None:
        path = find_config_file(config_path)
        if path is None:
            return ValidationResult(
                passed=False,
                message="Cannot validate cache directory - config not found",
            )
        try:
            config = load_config(path)
        except Exception:
            return ValidationResult(
                passed=False,
                message="Cannot validate cache directory - config load failed",
            )

    try:
        cache_path = config.paths.cache
        # If cache path is relative, resolve it against the vault root
        if not cache_path.is_absolute():
            cache_path = config.paths.root / cache_path
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
    """Count markdown files in root directory.

    Args:
        config_path: Explicit config path or None to search.
        config: Already-loaded config (with resolved vault root) or None to load from disk.

    Returns:
        Validation result with file count.
    """
    # Use provided config or load from disk
    if config is None:
        path = find_config_file(config_path)
        if path is None:
            return ValidationResult(
                passed=False,
                message="Cannot count files - config not found",
            )
        try:
            config = load_config(path)
        except Exception:
            return ValidationResult(
                passed=False,
                message="Cannot count files - config load failed",
            )

    try:
        root = config.paths.root

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
