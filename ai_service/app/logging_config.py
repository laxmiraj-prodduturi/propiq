from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_LOG_DIR = Path(__file__).parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "ai_service.log"

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    _LOG_DIR.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file — 10 MB per file, keep 5 backups
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "openai", "langchain", "chromadb", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("ai_service").info("Logging initialised — file: %s", _LOG_FILE)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"ai_service.{name}")
