"""CLI context object for clipmd."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from clipmd.config import get_vault_root, load_config, validate_config_paths

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
            # Validate that vault and cache are configured
            validate_config_paths(self.config)
        return self.config

    def get_vault_root(self) -> Path:
        """Get the resolved vault root directory.

        Returns:
            Resolved path to the vault root.
        """
        if self.config is None:
            self.load_config()
        assert self.config is not None
        return get_vault_root(self.config)
