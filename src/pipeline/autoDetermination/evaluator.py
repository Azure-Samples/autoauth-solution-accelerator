import asyncio
import glob
import importlib
import json
import os
import shutil
import sys
from datetime import datetime

import jq
from colorama import Fore
from numpy.f2py.auxfuncs import throw_error

from src.aifoundry.aifoundry_helper import AIFoundryManager
from src.aoai.aoai_helper import AzureOpenAIManager
from src.evals.case import Case, Evaluation
from src.evals.pipeline import PipelineEvaluator
from src.pipeline.autoDetermination.run import AutoPADeterminator
from src.pipeline.paprocessing.run import PAProcessingPipeline
from src.pipeline.promptEngineering.models import (
    ClinicalInformation,
    PatientInformation,
    PhysicianInformation,
)
from src.pipeline.promptEngineering.prompt_manager import PromptManager
from src.pipeline.utils import load_config
from src.utils.ml_logging import get_logger


class AutoDeterminationEvaluator(PipelineEvaluator):
    """
    Evaluator for the 'autoDetermination' pipeline component.

    Follows the standard pipeline steps:
      1. preprocess()         – Gathers test cases from YAML, instantiates runner (AutoPADeterminator).
      2. run_evaluations()    – Inherited from PipelineEvaluator; triggers the Azure Evaluate pipeline.
      3. post_processing()    – Summarizes results from Azure Evaluate.
      4. generate_responses() – Actually calls the AutoPADeterminator to get the final determination text.
    """

    # Must match the 'pipeline.class' field from your YAML so that we pick up the correct test cases.
    EXPECTED_PIPELINE = (
        "src.pipeline.autoDetermination.evaluator.AutoDeterminationEvaluator"
    )

    def __init__(self, cases_dir: str, temp_dir: str = "./temp", logger=None):
        """
        :param cases_dir: Directory containing the YAML files that define the test cases.
        :param temp_dir:  Directory for temporary data, if needed.
        :param logger:    Optional logger (if not provided, a default is created).
        """
        self.cases_dir = cases_dir
        self.temp_dir = temp_dir

        # PipelineEvaluator expects these:
        self.case_id = None
        self.scenario = None
        self.cases = {}  # Dict[str, Case]
        self.results = []

        # Create the runner (AutoPADeterminator) once we confirm pipeline class in preprocess().
        self.auto_determinator = None

        # AIFoundry + config
        self.ai_foundry_manager = AIFoundryManager()
        self.config_file = os.path.join("autoDetermination", "settings.yaml")
        self.config = load_config(self.config_file)
        self.run_config = self.config.get("run", {})

        # Logger
        self.logger = get_logger(
            name=self.run_config["logging"]["name"],
            level=self.run_config["logging"]["level"],
            tracing_enabled=self.run_config["logging"]["enable_tracing"],
        )

        # Azure OpenAI client
        azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
        azure_openai_chat_deployment_id = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID")
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_client = AzureOpenAIManager(
            completion_model_name=azure_openai_chat_deployment_id,
            api_key=azure_openai_key,
            azure_endpoint=azure_openai_endpoint,
        )
        self.prompt_manager = PromptManager()
        self.temperature = self.config["azure_openai"]["temperature"]
        self.max_tokens = self.config["azure_openai"]["max_tokens"]
        self.top_p = self.config["azure_openai"]["top_p"]
        self.frequency_penalty = self.config["azure_openai"]["frequency_penalty"]
        self.presence_penalty = self.config["azure_openai"]["presence_penalty"]
        self.seed = self.config["azure_openai"]["seed"]

    async def preprocess(self):
        """
        1. Load YAML definitions from self.cases_dir.
        2. Validate pipeline config, matching EXPECTED_PIPELINE.
        3. For each test case, create a `Case` object:
           - Instantiate evaluators.
           - For each 'evaluation' in the test case:
             * Read context (patient_info, physician_info, clinical_info, summarized_policy).
             * Call generate_responses() with these objects to get the final determination.
             * Store result in an Evaluation object.
        """
        yaml_files = glob.glob(os.path.join(self.cases_dir, "*.yaml"))
        for file_path in yaml_files:
            content = self._load_yaml(file_path)
            if not content:
                continue

            # Typically the root key matches the filename
            file_id = os.path.splitext(os.path.basename(file_path))[0]
            if file_id not in content:
                self.logger.warning(
                    f"Expected root key '{file_id}' not found in {file_path}. Skipping."
                )
                continue

            root_obj = content[file_id]

            # Validate the pipeline config
            pipeline_config = self._get_pipeline_config(root_obj, file_path)
            if not pipeline_config:
                # If pipeline.class doesn't match EXPECTED_PIPELINE, skip.
                continue

            # Store pipeline-specific info
            self.case_id = pipeline_config.get("case_id")

            # Instantiate the AutoPADeterminator (similar to AgenticRAG in the ideal version)
            self.auto_determinator = AutoPADeterminator(caseId=self.case_id)

            # Retrieve the list of test cases
            case_list = root_obj.get("cases", [])
            if not case_list:
                self.logger.warning(
                    f"No cases found under root key '{file_id}' in {file_path}. Skipping."
                )
                continue

            # Build each test case
            for case_id in case_list:
                if case_id not in content:
                    self.logger.warning(
                        f"Test case '{case_id}' not found in {file_path}. Skipping."
                    )
                    continue

                test_case_obj = content[case_id]
                self.cases[case_id] = Case(case_name=case_id)

                # Instantiate evaluators:
                if "evaluators" in test_case_obj:
                    case_evaluators = self._instantiate_evaluators(test_case_obj)
                else:
                    case_evaluators = self._instantiate_evaluators(root_obj)
                self.cases[case_id].evaluators = case_evaluators

                # Each test case can have multiple "evaluations"
                evaluations = test_case_obj.get("evaluations", [])
                if not evaluations:
                    self.logger.warning(
                        f"No 'evaluations' section for case '{case_id}'. Skipping."
                    )
                    continue

                for eval_item in evaluations:
                    # Extract query and ground truth
                    query = eval_item.get("query")
                    ground_truth = eval_item.get("ground_truth")

                    # 1) Retrieve context data (if any) from the evaluation
                    context_data = eval_item.get("context", {})

                    # Instantiate each context object if the data is present
                    patient_info_obj = self._instantiate_context(
                        context_data,
                        "src.pipeline.promptEngineering.models:PatientInformation",
                    )

                    physician_info_obj = self._instantiate_context(
                        context_data,
                        "src.pipeline.promptEngineering.models:PhysicianInformation",
                    )

                    clinical_info_obj = self._instantiate_context(
                        context_data,
                        "src.pipeline.promptEngineering.models:ClinicalInformation",
                    )

                    policy_text = self._instantiate_context(
                        context_data,
                        "policy_text",
                    )

                    # 2) Generate a response from the runner (wrap in try/except)
                    processed_output = ""
                    try:
                        response = await self.generate_responses(
                            patient_info=patient_info_obj,
                            physician_info=physician_info_obj,
                            clinical_info=clinical_info_obj,
                            policy_text=policy_text,
                        )
                        processed_output = await self.process_generated_output(
                            response.get("generated_output", {}), query
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error generating auto determination for case {case_id}: {e}"
                        )

                    # Prepare evaluation context for logging/storage
                    eval_context = {
                        "patient_info": (
                            patient_info_obj.model_dump() if patient_info_obj else None
                        ),
                        "physician_info": (
                            physician_info_obj.model_dump()
                            if physician_info_obj
                            else None
                        ),
                        "clinical_info": (
                            clinical_info_obj.model_dump()
                            if clinical_info_obj
                            else None
                        ),
                        "policy_text": (policy_text if policy_text else None),
                    }

                    # 3) Create an Evaluation record
                    evaluation_record = Evaluation(
                        query=query,
                        response=processed_output,
                        ground_truth=ground_truth,
                        context=json.dumps(eval_context),
                        conversation=None,
                        scores=None,
                    )
                    self.cases[case_id].evaluations.append(evaluation_record)

                    # Also add to self.results for higher-level reporting
                    self.results.append(
                        {
                            "case": case_id,
                            "query": query,
                            "auto_determination_response": processed_output,
                            "ground_truth": ground_truth,
                            "context": evaluation_record.context,
                        }
                    )

        self.logger.info(
            f"AutoDeterminationEvaluator initialized with case_id={self.case_id}, scenario={self.scenario}"
        )

    async def generate_responses(
        self, patient_info, physician_info, clinical_info, policy_text
    ):
        """
        Calls AutoPADeterminator to produce a final determination text from the provided
        context fields. Returns a dict with timestamps and any errors.
        """
        dt_started = datetime.now().isoformat()
        try:

            async def summarize_policy_callback(text: str) -> str:
                summary = await self._summarize_policy(text)
                return summary

            use_o1 = bool(os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_01"))

            final_text, _conv_history = await self.auto_determinator.run(
                patient_info=patient_info,
                physician_info=physician_info,
                clinical_info=clinical_info,
                policy_text=policy_text,
                summarize_policy_callback=summarize_policy_callback,
                use_o1=use_o1,  # or True if you want to try your O1 path first
                caseId=self.case_id,
            )
            dt_completed = datetime.now().isoformat()
            return {
                "generated_output": final_text,
                "dt_started": dt_started,
                "dt_completed": dt_completed,
            }
        except Exception as e:
            self.logger.error(f"Error generating response for autoDetermination: {e}")
            dt_completed = datetime.now().isoformat()
            return {
                "generated_output": "",
                "dt_started": dt_started,
                "dt_completed": dt_completed,
                "error": str(e),
            }

    def post_processing(self) -> str:
        """
        Summarize all cases' azure_eval_result after run_evaluations() finishes.
        """
        summary = {"cases": []}
        for case_id, case_obj in self.cases.items():
            summary["cases"].append(
                {"case": case_obj.case_name, "results": case_obj.azure_eval_result}
            )
        return json.dumps(summary, indent=2)

    def cleanup_temp_dir(self) -> None:
        """
        Cleanup any temporary dir used (if needed).
        """
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.logger.info(f"Cleaned up temporary directory: {self.temp_dir}")

    async def process_generated_output(self, generated_output: str, query: str):
        """
        Processes the generated output using a jq-compatible query.

        :param generated_output: The JSON object (dict) to process.
        :param query: The jq-compatible query string.
        :return: The extracted value(s) based on the query.
        """
        try:
            autodetermination = await self._summarize_autodetermination(
                generated_output
            )
            subset = jq.compile(query).input(json.loads(autodetermination)).all()
            result = str(subset[0]) if subset else ""
            return result
        except Exception as e:
            raise RuntimeError(f"Error processing generated output: {e}") from e

    async def _summarize_autodetermination(self, text: str) -> str:
        """
        Summarize a given autodetermination text using the LLM.

        Args:
            text: The full text of the policy document.

        Returns:
            A summarized version of the policy text.
        """
        self.logger.info(Fore.CYAN + "Summarizing AutoDetermination...")
        system_message_content = self.prompt_manager.get_prompt(
            "summarize_autodetermination_system.jinja"
        )
        prompt_user_query_summary = (
            self.prompt_manager.create_prompt_summary_autodetermination(text)
        )
        api_response_query = await self.azure_openai_client.generate_chat_response(
            query=prompt_user_query_summary,
            system_message_content=system_message_content,
            conversation_history=[],
            response_format="text",
            max_tokens=4096,
            top_p=self.top_p,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
        )
        return api_response_query["response"]

    async def _summarize_policy(self, policy_text: str) -> str:
        """
        Summarize a given policy text using the LLM.

        Args:
            policy_text: The full text of the policy document.

        Returns:
            A summarized version of the policy text.
        """
        self.logger.info(Fore.CYAN + "Summarizing Policy...")
        system_message_content = self.prompt_manager.get_prompt(
            "summarize_policy_system.jinja"
        )
        prompt_user_query_summary = self.prompt_manager.create_prompt_summary_policy(
            policy_text
        )
        api_response_query = await self.azure_openai_client.generate_chat_response(
            query=prompt_user_query_summary,
            system_message_content=system_message_content,
            conversation_history=[],
            response_format="text",
            max_tokens=4096,
            top_p=self.top_p,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
        )
        return api_response_query["response"]


if __name__ == "__main__":
    evaluator = AutoDeterminationEvaluator(cases_dir="./evals/cases")
    try:
        # run_pipeline() is defined in PipelineEvaluator, calls preprocess -> run_evaluations -> post_processing
        summary_result = asyncio.run(evaluator.run_pipeline())
        print(summary_result)
    except Exception as exc:
        import traceback

        print(f"Pipeline failed: {exc}\n{traceback.format_exc()}")
        exit(1)
