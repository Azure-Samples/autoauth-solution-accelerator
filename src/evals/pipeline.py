import importlib
import logging
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from typing import final, List, Tuple
import inspect
import yaml
from azure.ai.evaluation import evaluate

from src.aifoundry.aifoundry_helper import AIFoundryManager
from src.pipeline.utils import load_config
from src.utils.ml_logging import get_logger

# @TODO: Remove this import when the package fix is available.
from azure.ai.evaluation._evaluate._eval_run import EvalRun
from src.evals.sdk.custom_azure_ai_evaluations import custom_start_run, CUSTOM_TAGS
import src.evals.sdk.custom_azure_ai_evaluations as custom_eval
EvalRun._start_run = custom_start_run

class PipelineEvaluator(ABC):
    """
    Base class for pipeline evaluators.

    This class standardizes a pipeline workflow consisting of:
      1. preprocess()      – An asynchronous method to prepare the data.
      2. run_evaluations()  – An asynchronous method to execute evaluations.
      3. post_processing()  – A method to process and summarize the results.
      4. generate_response() – An asynchronous method to generate a response.

    The run_pipeline() method executes these steps in order.
    """

    @abstractmethod
    def __init__(self):
        """
        Base initializer.

        Subclasses can extend this initializer to set up their own state.
        """
        self.EXPECTED_PIPELINE = None
        self.config_file = os.path.join("", "settings.yaml")
        self.config = load_config(self.config_file)
        self.run_config = self.config.get("run", {})
        self.cases = {}
        self.ai_foundry_manager = AIFoundryManager()

        self.logger = get_logger(
            name=self.run_config["logging"]["name"],
            level=self.run_config["logging"]["level"],
            tracing_enabled=self.run_config["logging"]["enable_tracing"],
        )

    def _generate_custom_tags(self, case_id: str, git_commit: str, class_name: str) ->  List[Tuple[str,str]]:
        computed_tags = [
            ("case",case_id),
            ("commit", git_commit),
            ("class", class_name)
        ]
        custom_eval.CUSTOM_TAGS = computed_tags
        return computed_tags

    def _resolve_object(self, value: str):
        """
        Given a string in the format 'module_path:object_path', import the module and resolve
        the nested attribute(s) to return the actual object.

        For example, for value "azure.ai.evaluation:RougeType.rogue4", this will:
          - Import module "azure.ai.evaluation"
          - Retrieve the attribute "RougeType" from that module
          - Then retrieve the attribute "rogue4" from that RougeType object
        """
        try:
            module_path, object_path = value.split(":", 1)
            module = importlib.import_module(module_path)
            parts = object_path.split(".")
            obj = module
            for part in parts:
                obj = getattr(obj, part)
            return obj
        except Exception as e:
            self.logger.error(f"Error resolving object from '{value}': {e}")
            return value  # Fall back to returning the original value if resolution fails

    def _instantiate_evaluators(self, root_obj: dict) -> dict:
        """
        Dynamically builds and returns a dictionary of evaluator instances.

        For each evaluator definition in root_obj["evaluators"]:
          - Splits the provided "class" string (format: "module_path:ClassName").
          - Imports the module and retrieves the class.
          - Processes the "args" dictionary. If an argument value is a string and contains a colon,
            attempts to resolve it into an object using _resolve_object().
          - Checks if the evaluator's __init__ has a 'model_config' parameter. If so, and if it is
            not already provided in the args, creates and passes in a model_config dictionary.
          - Instantiates the evaluator with the resolved arguments.

        Raises RuntimeError if any evaluator cannot be instantiated.
        """
        evaluators = {}
        evaluator_list = root_obj.get("evaluators", [])

        for evaluator_def in evaluator_list:
            evaluator_name = evaluator_def.get("name")
            evaluator_class_path = evaluator_def.get("class")
            if not evaluator_class_path:
                msg = f"Evaluator definition for '{evaluator_name}' is missing a 'class' field."
                self.logger.error(msg)
                raise ValueError(msg)

            # Get evaluator arguments from the config.
            args = evaluator_def.get("args", {})

            try:
                # Split the evaluator class path: "module_path:ClassName"
                module_path, class_name = evaluator_class_path.split(":", 1)
                module = importlib.import_module(module_path)
                evaluator_class = getattr(module, class_name)

                # Use inspect to check if __init__ has a "model_config" parameter.
                sig = inspect.signature(evaluator_class.__init__)
                if "model_config" in sig.parameters:
                    # If the caller didn't provide a model_config, then add it.
                    if "model_config" not in args or args["model_config"] is None:
                        model_config = {
                            "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                            "api_key": os.environ.get("AZURE_OPENAI_KEY"),
                            "azure_deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
                        }
                        if any(value is None for value in model_config.values()):
                            raise ValueError("model_config has null values, please check your environment variables: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT.")
                        args["model_config"] = model_config

                # Resolve each argument: if it's a string containing ":", attempt to resolve it.
                resolved_args = {}
                for key, value in args.items():
                    if isinstance(value, str) and ":" in value:
                        resolved_args[key] = self._resolve_object(value)
                    else:
                        resolved_args[key] = value

                evaluator_instance = evaluator_class(**resolved_args)
                evaluators[evaluator_name] = evaluator_instance
                self.logger.info(
                    f"Instantiated evaluator '{evaluator_name}' from '{evaluator_class_path}' with args: {self.sanitize_args(resolved_args)}"
                )
            except Exception as e:
                msg = f"Error instantiating evaluator '{evaluator_name}' from '{evaluator_class_path}': {e}"
                self.logger.error(msg)
                raise RuntimeError(msg)

        return evaluators

    def _get_git_hash(self) -> str:
        """Retrieve the current Git commit hash (short version)."""
        try:
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.STDOUT
            ).decode().strip()
            return git_hash
        except Exception as e:
            self.logger.error(f"Error retrieving Git hash: {e}")
            return "unknown"

    def _load_yaml(self, file_path: str) -> dict:
        """Load YAML configuration from a file."""
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading YAML file {file_path}: {e}")
            return {}

    def _get_pipeline_config(self, root_obj: dict, file_path: str) -> dict:
        """Extract and validate the pipeline configuration from the root object."""
        pipeline_config = root_obj.get("pipeline")
        if not pipeline_config:
            self.logger.info(f"Skipping file {file_path} because no pipeline configuration found.")
            return None
        if pipeline_config.get("class") != self.EXPECTED_PIPELINE:
            self.logger.info(
                f"Skipping file {file_path} because pipeline class is '{pipeline_config.get('class')}' "
                f"but expected '{self.EXPECTED_PIPELINE}'."
            )
            return None
        return pipeline_config

    def _flatten_dict(self, d: dict, parent_key: str = "", sep: str = ".") -> dict:
        """Recursively flattens a nested dictionary."""
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key, sep=sep))
            else:
                items[new_key] = str(v)
        return items

    def _instantiate_context(self, context_mapping: dict, key: str):
        """
        Instantiates a context object from a mapping.
        Expects a mapping of the form:
          { "src.pipeline.promptEngineering.models:ClinicalInformation": { ... } }
        Returns the instantiated object or None if instantiation fails.
        """
        if key not in context_mapping:
            self.logger.error(f"Key '{key}' not found in the provided context mapping.")
            return None

        value = context_mapping[key]

        if ":" in key:
            # Key is in the format "module_path:ClassName"
            try:
                module_path, class_name = key.split(":", 1)
                mod = importlib.import_module(module_path)
                context_class = getattr(mod, class_name)
                # We expect the value to be a dictionary of parameters for the class
                return context_class(**value)
            except Exception as e:
                self.logger.error(f"Error instantiating context for key '{key}': {e}")
                return None
        else:
            # Key does not contain ':', treat value as a direct string (or raw data)
            return value

    @abstractmethod
    async def preprocess(self):
        """
        Preprocess step.

        This method should be implemented by subclasses.
        """
        pass

    # @abstractmethod
    # async def run_evaluations(self):
    #     """
    #     Run evaluations step.
    #
    #     This method should be implemented by subclasses.
    #     """
    #     pass

    @abstractmethod
    def post_processing(self) -> dict:
        """
        Post-processing step.

        This method should be implemented by subclasses to summarize and process evaluation results.
        """
        pass

    @abstractmethod
    async def generate_responses(self, **kwargs) -> dict:
        """
        Generate response step.

        This method should be implemented by subclasses to generate a response
        based on the provided inputs (e.g. processing uploaded files and extracting data).
        """
        pass

    @final
    async def run_pipeline(self) -> dict:
        """
        Executes the pipeline steps in order:
          1. preprocess
          2. run_evaluations
          3. post_processing

        Returns:
            dict: The result from the post_processing step.
        """
        await self.preprocess()
        await self.run_evaluations()
        return self.post_processing()

    @final
    async def run_evaluations(self):
        """
        Evaluation step:
          - For each test case, creates an evaluation dataset and triggers the Azure AI evaluation.
          - Uses the evaluators stored on each Case object.
          - Stores the Azure evaluation results in each Case object.
        """
        git_hash = self._get_git_hash()
        for case_id, case_obj in self.cases.items():
            evaluators = getattr(case_obj, "evaluators", None)
            if evaluators is None:
                self.logger.warning(f"No evaluators set for case '{case_id}', skipping evaluation.")
                continue

            evaluator_config = {}
            # Build the column mapping for each evaluator.
            # "response" is always included, while "query", "ground_truth", and "context" are added
            # only if at least one evaluation in the case contains that attribute.
            for evaluator_name in evaluators.keys():
                column_mapping = {"response": "${data.response}"}
                optional_keys = ["query", "ground_truth", "context"]
                for key in optional_keys:
                    # Check if any evaluation object has the attribute and a non-None value.
                    if any(hasattr(eval_item, key) and getattr(eval_item, key) is not None for eval_item in case_obj.evaluations):
                        column_mapping[key] = "${data." + key + "}"
                evaluator_config[evaluator_name] = {
                    "column_mapping": column_mapping
                }

            with case_obj.create_evaluation_dataset() as dataset_path:
                custom_eval.CUSTOM_TAGS = self._generate_custom_tags(case_id, git_hash, self.__class__.__name__)
                azure_result = evaluate(
                    evaluation_name=f"{case_id}",
                    data=dataset_path,
                    evaluators=evaluators,
                    evaluator_config=evaluator_config,
                    azure_ai_project=self.ai_foundry_manager.project_config,
                )
                case_obj.azure_eval_result = azure_result

    def sanitize_args(self, args: dict, sensitive_keys: set = None) -> dict:
        """
        Recursively masks values for sensitive keys in a dictionary.

        Parameters:
            args (dict): The dictionary of arguments.
            sensitive_keys (set): A set of keys whose values should be masked.
                Defaults to {"api_key", "password", "secret", "token"}.

        Returns:
            dict: A new dictionary with sensitive values masked.
        """
        if sensitive_keys is None:
            sensitive_keys = {"api_key", "password", "secret", "token"}

        sanitized = {}
        for key, value in args.items():
            if key in sensitive_keys:
                sanitized[key] = "****"  # Mask the sensitive value
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_args(value, sensitive_keys)
            else:
                sanitized[key] = value
        return sanitized

    def cleanup_temp_dir(self) -> None:
        """
        Cleans up the temporary directory if it exists.
        Expects the instance to have an attribute 'temp_dir'.
        """
        temp_dir = getattr(self, "temp_dir", None)
        if not temp_dir:
            # No temporary directory defined; nothing to clean.
            return
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                if hasattr(self, "logger"):
                    self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
                else:
                    logging.getLogger(__name__).info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Failed to clean up temporary directory '{temp_dir}': {e}")
            else:
                logging.getLogger(__name__).error(f"Failed to clean up temporary directory '{temp_dir}': {e}")