import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, PrivateAttr

from utils.ml_logging import get_logger


class KernelPlugin(BaseModel):
    """
    Represents a plugin loaded from a directory.

    Provides functionality to identify the plugin's directory and loaded functions.
    This class is a placeholder and can be extended to parse YAML, directories, or
    Python classes to load actual functionalities.
    """

    plugin_name: str = Field(..., description="The name of the plugin.")
    directory: str = Field(..., description="The plugin directory path.")
    functions: Dict[str, Any] = Field(
        default_factory=dict, description="Functions from the plugin."
    )

    @classmethod
    def from_directory(
        cls,
        plugin_name: str,
        parent_directory: str,
        description: Optional[str] = None,
        class_init_arguments: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> "KernelPlugin":
        """
        Load a plugin from the specified directory. This is a stub implementation.

        :param plugin_name: The name of the plugin to load.
        :param parent_directory: The directory from which to load the plugin.
        :param description: (optional) A description of the plugin.
        :param class_init_arguments: (optional) Arguments for Python classes in the plugin.
        :return: An instance of KernelPlugin.
        :raises FileNotFoundError: If the directory does not exist.
        :raises ValueError: If the plugin cannot be initialized correctly.
        """
        logger = logging.getLogger(__name__)
        plugin_path = os.path.join(parent_directory, plugin_name)
        if not os.path.isdir(plugin_path):
            logger.error("Plugin directory '%s' does not exist.", plugin_path)
            raise FileNotFoundError(f"Plugin directory '{plugin_path}' does not exist.")

        # In a real scenario, parse and load plugin configuration here.
        return cls(plugin_name=plugin_name, directory=plugin_path, functions={})


class Skills(BaseModel):
    """
    Manages loading and retrieval of multiple plugins (skills).

    Provides methods to:
    - Load multiple plugins from a specified parent directory.
    - Retrieve individual loaded plugins.
    - List available skills (plugin directories) in the parent directory.
    """

    parent_directory: str = Field(
        ..., description="The parent directory containing plugins."
    )
    _logger: logging.Logger = PrivateAttr()
    _plugins: Dict[str, KernelPlugin] = PrivateAttr(default_factory=dict)

    def __init__(self, parent_directory: str) -> None:
        """
        Initialize the Skills manager with a given parent directory.

        :param parent_directory: The directory that contains the plugin directories.
        :return: None
        """
        super().__init__(parent_directory=parent_directory)
        object.__setattr__(
            self,
            "_logger",
            get_logger(name="SkillsManager", level=10, tracing_enabled=False),
        )
        self._logger.debug(
            "Skills manager initialized with parent directory: %s", parent_directory
        )

    def load_skills(self, skill_names: List[str]) -> None:
        """
        Load multiple plugins (skills) from the specified parent directory.

        :param skill_names: A list of skill (plugin) names to be loaded.
        :return: None
        :raises FileNotFoundError: If a plugin directory does not exist.
        :raises ValueError: If any plugin fails to load.
        """
        for skill_name in skill_names:
            try:
                self._logger.debug("Attempting to load skill: %s", skill_name)
                plugin = KernelPlugin.from_directory(
                    plugin_name=skill_name, parent_directory=self.parent_directory
                )
                self._plugins[skill_name] = plugin
                self._logger.info("Successfully loaded skill: %s", skill_name)
            except Exception as e:
                self._logger.error(
                    "Failed to load skill '%s': %s", skill_name, str(e), exc_info=True
                )
                raise e

    def get_skill(self, skill_name: str) -> KernelPlugin:
        """
        Retrieve a loaded skill (plugin) by name.

        :param skill_name: The name of the skill to retrieve.
        :return: The KernelPlugin instance associated with the given skill name.
        :raises KeyError: If the skill is not found.
        """
        try:
            return self._plugins[skill_name]
        except KeyError as e:
            self._logger.error("Skill '%s' not found.", skill_name, exc_info=True)
            raise KeyError(f"Skill '{skill_name}' not found.") from e

    def list_available_skills(self) -> List[str]:
        """
        List available skills in the parent directory by identifying directories that
        could represent plugins.

        :return: A list of plugin (skill) names available in the parent directory.
        :raises FileNotFoundError: If the parent directory does not exist.
        """
        if not os.path.isdir(self.parent_directory):
            self._logger.error(
                "The parent directory '%s' does not exist.", self.parent_directory
            )
            raise FileNotFoundError(
                f"The parent directory '{self.parent_directory}' does not exist."
            )

        skill_names = []
        for item in os.listdir(self.parent_directory):
            path = os.path.join(self.parent_directory, item)
            # Filter out non-directories and hidden/system directories
            if os.path.isdir(path) and not item.startswith("_"):
                skill_names.append(item)
        self._logger.debug("Available skills found: %s", skill_names)
        return skill_names
