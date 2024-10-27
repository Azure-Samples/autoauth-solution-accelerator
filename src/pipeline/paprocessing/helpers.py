from pathlib import Path
import os
from typing import List , Union    

from utils.ml_logging import get_logger

logger = get_logger()

def find_all_files(
     root_folder: str, extensions: Union[List[str], str]
    ) -> List[str]:
        """
        Recursively find all files with specified extensions under the root folder.

        Args:
            root_folder (str): The root folder to search for files.
            extensions (Union[List[str], str]): List of file extensions to search for.

        Returns:
            List[str]: List of full paths to the found files.
        """
        if isinstance(extensions, str):
            extensions = [extensions]

        files_list = []
        root_folder_path = Path(root_folder).resolve()

        for root, _, files in os.walk(root_folder_path):
            for file in files:
                if any(file.lower().endswith(f".{ext}") for ext in extensions):
                    files_list.append(str(Path(root) / file))
        logger.info(f"Found {len(files_list)} files with extensions {extensions}")
        return files_list