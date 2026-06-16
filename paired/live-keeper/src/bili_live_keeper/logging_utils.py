"""Logging setup with mandatory redaction."""

import logging
import os
import time
from pathlib import Path
from typing import Optional

from .secrets import redact_text


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_text(super().format(record))


def setup_logging(level: str = "INFO", log_dir: Optional[Path] = None) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()

    formatter = RedactingFormatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    formatter.converter = time.gmtime

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_dir:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "bili-live-keeper.log"
            file_handler = logging.FileHandler(str(log_file))
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
            try:
                os.chmod(str(log_file), 0o640)
            except OSError:
                pass
        except OSError as exc:
            logging.getLogger(__name__).warning("Failed to enable file logging: %s", exc)
