"""CLI context object for clipmd."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

from clipmd.config import load_config

if TYPE_CHECKING:
    from clipmd.config import Config


class Context:
    """CLI context object holding configuration and settings."""

    def __init__(self) -> None:
        self.config: Config | None = None
        self.config_path: Path | None = None
        self.verbose: int = 0
        self.quiet: bool = False
        self.no_color: bool = False

    def load_config(self, config_path: Path | None = None) -> Config:
        """Load configuration, caching the result."""
        if self.config is None:
            self.config = load_config(config_path)
            self.config_path = config_path
        return self.config

    def require_config(self) -> Config:
        """Require that config is loaded, raise error if not.

        Returns:
            Config object.

        Raises:
            ClickException: If config is not loaded.
        """
        if self.config is None:  # pragma: no cover
            raise click.ClickException("Configuration not loaded")
        return self.config

    def require_vault(self) -> Path:
        """Require that vault is configured, raise error if not.

        Returns:
            Vault path.

        Raises:
            ClickException: If config is not loaded or vault not configured.
        """
        config = self.require_config()
        if config.vault is None:  # pragma: no cover
            raise click.ClickException("Vault path not configured")
        return config.vault

    def require_cache(self) -> Path:
        """Require that cache is configured, raise error if not.

        Returns:
            Cache path.

        Raises:
            ClickException: If config is not loaded or cache not configured.
        """
        config = self.require_config()
        if config.cache is None:  # pragma: no cover
            raise click.ClickException("Cache path not configured")
        return config.cache
