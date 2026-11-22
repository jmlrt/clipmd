"""clipmd - Clip, organize, and manage markdown articles."""

import warnings

# trafilatura (>=2.1) imports urllib3.contrib.socks at load time, which emits a
# DependencyWarning when the optional PySocks package is missing. clipmd fetches
# via httpx and never uses SOCKS proxies, so silence that specific warning.
warnings.filterwarnings(
    "ignore",
    message=r"SOCKS support in urllib3 requires.*",
    category=Warning,
    module=r"urllib3\.contrib\.socks",
)

__version__ = "0.1.0"
