"""CLI context object for clipmd."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from clipmd.config import load_config, resolve_vault_root

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
        self.vault_override: Path | None = None

    def load_config(self, config_path: Path | None = None) -> Config:
        """Load configuration, caching the result."""
        if self.config is None:
            self.config = load_config(config_path)
            self.config_path = config_path
        return self.config

    def get_vault_root(self) -> Path:
        """Get the resolved vault root directory.

        Returns:
            Resolved path to the vault root.
        """
        if self.config is None:
            self.load_config()
        return resolve_vault_root(self.config, self.vault_override)  # type: ignore[arg-type]
