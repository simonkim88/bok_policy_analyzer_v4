from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
_cached_config: Dict[str, Any] | None = None


def _resolve_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((PROJECT_ROOT / path).resolve())


def _resolve_config_paths(config: Dict[str, Any]) -> Dict[str, Any]:
    resolved = deepcopy(config)

    for key, value in resolved.get("paths", {}).items():
        if isinstance(value, str):
            resolved["paths"][key] = _resolve_path(value)

    indicators = resolved.get("ecos", {}).get("indicators", {})
    for indicator in indicators.values():
        csv_path = indicator.get("csv_path")
        if isinstance(csv_path, str):
            indicator["csv_path"] = _resolve_path(csv_path)

    logging_cfg = resolved.get("logging", {})
    if isinstance(logging_cfg.get("file"), str):
        logging_cfg["file"] = _resolve_path(logging_cfg["file"])

    return resolved


def get_config() -> Dict[str, Any]:
    """Load and cache project configuration from config.yaml."""
    global _cached_config

    if _cached_config is not None:
        return _cached_config

    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as fp:
        loaded = yaml.safe_load(fp) or {}

    _cached_config = _resolve_config_paths(loaded)
    return _cached_config
