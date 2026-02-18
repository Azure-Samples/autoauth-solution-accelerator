"""Configuration loader for the Policy Indexer Function App."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def load_settings(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load indexer settings from YAML config file.

    Resolves the config path in order:
      1. Explicit ``config_path`` argument
      2. ``INDEXER_CONFIG_PATH`` environment variable
      3. Default ``config/settings.yaml`` relative to this file

    Returns:
        Parsed YAML config dict.
    """
    if config_path is None:
        config_path = os.getenv(
            "INDEXER_CONFIG_PATH",
            str(Path(__file__).resolve().parent.parent / "config" / "settings.yaml"),
        )

    config_path = Path(config_path).resolve()
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    """
    Retrieve an environment variable, raising if required and missing.
    """
    value = os.getenv(name, default)
    if required and not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")
    return value
