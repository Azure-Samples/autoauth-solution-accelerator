import os
from typing import Any, Dict

import yaml

from utils.ml_logging import get_logger

# Set up logging
logger = get_logger()


def load_config(config_file: str = "config.yaml") -> Dict[str, Any]:
    """
    Safely loads the YAML configuration file.

    Args:
        config_file (str): Relative or absolute path to the YAML configuration file.
                           Defaults to "config.yaml".

    Returns:
        Dict[str, Any]: Configuration dictionary. Returns an empty dict on error.
    """
    # Convert to absolute path if necessary
    if not os.path.isabs(config_file):
        base_dir = os.path.dirname(__file__)
        config_file = os.path.abspath(os.path.join(base_dir, config_file))

    if not os.path.exists(config_file):
        logger.error(f"Configuration file not found: {config_file}")
        return {}

    try:
        with open(config_file, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            if not data:
                logger.warning(
                    f"Configuration file is empty or invalid YAML: {config_file}"
                )
                return {}
            return data
    except yaml.YAMLError as yaml_error:
        logger.error(f"Error parsing YAML content in {config_file}: {yaml_error}")
    except Exception as e:
        logger.error(f"Unexpected error reading {config_file}: {e}")

    return {}
