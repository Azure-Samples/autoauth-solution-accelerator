import os
import pickle
from typing import Any, Union

import pandas as pd

from utils.ml_logging import get_logger

# Set up logging
logger = get_logger()


def save_dataframe(
    df: pd.DataFrame, path: Union[str, pd._typing.PathLike], file_format: str = "csv"
) -> None:
    """
    Save the given dataframe to the specified path in the desired format.

    :param df: Input DataFrame.
    :param path: The path where the dataframe should be saved.
    :param file_format: The format in which the dataframe should be saved. Default is 'csv'.
    :return: None
    :raises ValueError: If the specified file format is unsupported.
    """
    try:
        if file_format == "csv":
            df.to_csv(path, index=False)
            logger.info(f"DataFrame saved successfully at {path} in CSV format.")
        elif file_format == "excel":
            df.to_excel(path, index=False)
            logger.info(f"DataFrame saved successfully at {path} in Excel format.")
        elif file_format == "parquet":
            df.to_parquet(path, index=False)
            logger.info(f"DataFrame saved successfully at {path} in Parquet format.")
        elif file_format == "feather":
            df.to_feather(path)
            logger.info(f"DataFrame saved successfully at {path} in Feather format.")
        else:
            raise ValueError(
                f"Unsupported file format: {file_format}. Supported formats are: ['csv', 'excel', 'parquet', 'feather']."
            )
    except Exception as e:
        logger.error(f"Error while saving DataFrame: {e}")
        raise


def save_model_to_pickle(estimator: Any, file_path: str) -> None:  # nosec
    """
    Save a trained model to the specified file using Pickle.

    :param estimator: The trained model to save.
    :param file_path: The path where the model will be saved.
    :return: None.
    :raises Exception: If an error occurs while saving the model.
    """
    try:
        # Ensure the directory exists; if not, create it.
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        logger.info(f"Saving model to {file_path}.")
        with open(file_path, "wb") as file:
            pickle.dump(estimator, file)  # nosec
        logger.info(f"Model saved successfully to {file_path}.")
    except Exception as e:
        logger.error(f"Error occurred while saving model to {file_path}: {e}")
        raise e


def load_model_from_pickle(file_path: str) -> Any:
    """
    Load a trained model from the specified file using Pickle.

    :param file_path: The path from where the model is loaded.
    :return: Loaded model.
    :raises Exception: If an error occurs while loading the model.
    """
    try:
        logger.info(f"Loading model from {file_path}.")
        with open(file_path, "rb") as file:
            estimator = pickle.load(file)  # nosec
        logger.info(f"Model loaded successfully from {file_path}.")
        return estimator
    except Exception as e:
        logger.error(f"Error occurred while loading model from {file_path}: {e}")
        raise e


def load_dataframe_from_path(path: str) -> pd.DataFrame:
    """
    Load a dataframe from the specified path based on the file's extension.

    :param path: The path from where the dataframe should be loaded.
    :return: Loaded DataFrame.
    :raises ValueError: If the file format (determined by its extension) is unsupported.
    """
    _, file_extension = os.path.splitext(path)
    try:
        logger.info(f"Loading DataFrame from {path}.")
        if file_extension == ".csv":
            df = pd.read_csv(path)
        elif file_extension == ".excel" or file_extension == ".xlsx":
            df = pd.read_excel(path)
        elif file_extension == ".parquet":
            df = pd.read_parquet(path)
        elif file_extension == ".feather":
            df = pd.read_feather(path)
        else:
            raise ValueError(
                f"""Unsupported file format: {file_extension}. Supported formats are:
                ['.csv', '.excel', '.parquet', '.feather']."""
            )
        logger.info(f"DataFrame loaded successfully from {path}.")
        return df
    except Exception as e:
        logger.error(f"Error occurred while loading DataFrame from {path}: {e}")
        raise e


def resolve_python_object(path_str):
    module_str, obj_str = path_str.rsplit(".", 1)
    module = __import__(module_str, fromlist=[obj_str])
    return getattr(module, obj_str)
