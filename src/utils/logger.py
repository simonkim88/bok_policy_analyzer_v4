# pyright: basic
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.config import get_config


def setup_logging(config: Optional[dict] = None):
    """Setup centralized logging based on config."""
    cfg = config or get_config()
    logging_cfg = cfg.get("logging", {})

    level_name = logging_cfg.get("level", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)
    fmt = logging_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    log_file = Path(logging_cfg.get("file", "logs/bok_analyzer.log"))
    if not log_file.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent
        log_file = (project_root / log_file).resolve()

    log_file.parent.mkdir(parents=True, exist_ok=True)

    max_bytes = int(logging_cfg.get("max_bytes", 10 * 1024 * 1024))
    backup_count = int(logging_cfg.get("backup_count", 5))

    formatter = logging.Formatter(fmt)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
