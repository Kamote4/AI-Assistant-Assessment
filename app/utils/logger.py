import logging
import os
import sys

_configured = False


def setup_logger(name: str) -> logging.Logger:
    """Configure root logging once, then return a named child logger."""
    global _configured
    if not _configured:
        _configure_root()
        _configured = True
    return logging.getLogger(name)


def _configure_root() -> None:
    from config import config

    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        return

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    if config.LOG_TO_FILE:
        os.makedirs(config.LOG_DIR, exist_ok=True)
        fh = logging.FileHandler(config.LOG_FILE)
        fh.setFormatter(formatter)
        root.addHandler(fh)
