import asyncio
import glob
import json
import os
import shutil
import importlib
from datetime import datetime

from azure.ai.evaluation import evaluate

from src.aifoundry.aifoundry_helper import AIFoundryManager
from src.evals.pipeline import PipelineEvaluator
from src.pipeline.agenticRag.run import AgenticRAG
from src.evals.case import Case, Evaluation
from src.pipeline.utils import load_config
from src.utils.ml_logging import get_logger

from src.pipeline.promptEngineering.models import ClinicalInformation

class AgenticRagEvaluator(PipelineEvaluator):
    EXPECTED_PIPELINE = "src.pipeline.clinicalExtractor.evaluator.AgenticRagEvaluator"

    def __init__(self, cases_dir: str, temp_dir: str = "./temp", logger=None):
        self.cases_dir = cases_dir
        self.temp_dir = temp_dir
        self.case_id = None      # Set from the pipeline YAML.
        self.scenario = None     # Set from the pipeline YAML.
        self.cases = {}          # Mapping from case identifiers to Case instances.
        self.results = []        # Stores evaluation results.
        self.agentic_rag = None  # Will hold the AgenticRAG runner instance.
        self.ai_foundry_manager = AIFoundryManager()
        self.config_file = os.path.join("agenticRag", "settings.yaml")
        self.config = load_config(self.config_file)
        self.run_config = self.config.get("run", {})

        self.logger = get_logger(
            name=self.run_config["logging"]["name"],
            level=self.run_config["logging"]["level"],
            tracing_enabled=self.run_config["logging"]["enable_tracing"],
        )


    def _instantiate_context(self, context_mapping: dict):
        """
        Instantiates a context object from a mapping.
        Expects a mapping of the form:
          { "src.pipeline.promptEngineering.models:ClinicalInformation": { ... } }
        Returns the instantiated object or None if instantiation fails.
        """
        for key, config in context_mapping.items():
            try:
                module_path, class_name = key.split(":", 1)
                mod = importlib.import_module(module_path)
                context_class = getattr(mod, class_name)
                return context_class(**config)
            except Exception as e:
                self.logger.error(f"Error instantiating context for key '{key}': {e}")
                return None
        return None

    async def preprocess(self):
        """
        Preprocessing step:
          - Loads YAML test case definitions.
          - Validates the pipeline configuration and sets parameters (case_id, scenario).
          - Instantiates evaluators for each test case individually.
          - For each test case:
              * Creates a Case instance.
              * Instantiates a ClinicalInformation object from the provided clinical info or context.
              * Generates a response via AgenticRAG.
              * Processes the generated output and creates Evaluation records.
        """
        case_files = glob.glob(os.path.join(self.cases_dir, "*.yaml"))
        for file_path in case_files:
            config = self._load_yaml(file_path)
            if not config:
                continue

            file_id = os.path.splitext(os.path.basename(file_path))[0]
            if file_id not in config:
                self.logger.warning(f"Expected root key '{file_id}' not found in {file_path}. Skipping.")
                continue

            root_obj = config[file_id]
            pipeline_config = self._get_pipeline_config(root_obj, file_path)
            if not pipeline_config:
                continue

            # Set pipeline parameters.
            self.case_id = pipeline_config.get("case_id")
            self.scenario = pipeline_config.get("scenario")
            # Instantiate the runner for this pipeline.
            self.agentic_rag = AgenticRAG(caseId=self.case_id)

            cases_list = root_obj.get("cases", [])
            if not cases_list:
                self.logger.warning(f"No cases found under root key '{file_id}' in {file_path}. Skipping.")
                continue

            for case_id in cases_list:
                if case_id not in config:
                    self.logger.warning(f"Test case '{case_id}' not found in {file_path}. Skipping.")
                    continue

                test_case_obj = config[case_id]
                self.cases[case_id] = Case(case_name=case_id)

                # Instantiate evaluators for this case.
                # If the test case defines its own evaluators, use them;
                # otherwise, fall back to those defined in the pipeline config.
                if "evaluators" in test_case_obj:
                    case_evaluators = self._instantiate_evaluators(test_case_obj)
                else:
                    case_evaluators = self._instantiate_evaluators(root_obj)
                # Store the evaluators on the case so they can be used later.
                self.cases[case_id].evaluators = case_evaluators

                # Process clinical information.
                clinical_info_obj = None
                clinical_info_data = test_case_obj.get("clinical_info")
                if clinical_info_data:
                    if isinstance(clinical_info_data, dict):
                        clinical_info_obj = ClinicalInformation(**clinical_info_data)
                    else:
                        clinical_info_obj = clinical_info_data
                elif "context" in test_case_obj:
                    clinical_info_obj = self._instantiate_context(test_case_obj["context"])
                else:
                    for eval_item in test_case_obj.get("evaluations", []):
                        if "context" in eval_item:
                            clinical_info_obj = self._instantiate_context(eval_item["context"])
                            break

                if not clinical_info_obj:
                    self.logger.error(f"No clinical information provided for test case '{case_id}'. Skipping this case.")
                    continue

                # Generate response using the instantiated clinical_info_obj.
                response = await self.generate_responses(clinical_info_obj)
                processed_output = self.process_generated_output(response.get("generated_output", {}))

                # Determine default context for evaluations.
                context_obj = None
                if "context" in test_case_obj:
                    context_obj = self._instantiate_context(test_case_obj["context"])
                else:
                    for eval_item in test_case_obj.get("evaluations", []):
                        if "context" in eval_item:
                            context_obj = self._instantiate_context(eval_item["context"])
                            break

                for eval_item in test_case_obj.get("evaluations", []):
                    query = eval_item.get("query")
                    expected_val = eval_item.get("ground_truth")
                    evaluation_record = Evaluation(
                        query=query,
                        response=processed_output,
                        ground_truth=expected_val,
                        context=json.dumps(context_obj.model_dump()) if context_obj else None,
                        conversation=None,
                        scores=None
                    )
                    self.cases[case_id].evaluations.append(evaluation_record)
                    self.results.append({
                        "case": case_id,
                        "query": evaluation_record.query,
                        "agentic_rag_response": processed_output,
                        "ground_truth": expected_val,
                        "context": evaluation_record.context,
                    })
        self.logger.info(f"AgenticRagEvaluator initialized with case_id: {self.case_id}, scenario: {self.scenario}")

    async def generate_responses(self, clinical_info: object) -> dict:
        """
        Uses the AgenticRAG runner to generate a response.
        Passes the instantiated ClinicalInformation object to the runner.
        Returns a dict with generated output and timing information.
        """
        dt_started = datetime.now().isoformat()
        try:
            result = await self.agentic_rag.run(clinical_info=clinical_info, max_retries=3)
            dt_completed = datetime.now().isoformat()
            return {"generated_output": result, "dt_started": dt_started, "dt_completed": dt_completed}
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            dt_completed = datetime.now().isoformat()
            return {"generated_output": {}, "dt_started": dt_started, "dt_completed": dt_completed, "error": str(e)}

    def process_generated_output(self, generated_output: dict) -> str:
        """
        Processes the generated output before evaluation.
        Currently, processes output based on the scenario.
        """
        self.logger.info("Processing generated output.")
        # Example for "policy" scenario.
        if self.scenario == "policy":
            policies = ['/'.join(x.split('/')[-2:]) for x in generated_output.get('policies', [])]
            return "\n".join(policies)
        # Example for "reasoning" scenario.
        elif self.scenario == "reasoning":
            reasoning = generated_output.get('evaluation', {}).get('reasoning', [])
            return "\n".join(reasoning)
        else:
            msg = f"Scenario not implemented: {self.scenario}"
            self.logger.error(msg)
            raise ValueError(msg)

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
            for evaluator_name in evaluators.keys():
                evaluator_config[evaluator_name] = {
                    "column_mapping": {
                        "query": "${data.query}",
                        "ground_truth": "${data.ground_truth}",
                        "response": "${data.response}",
                        "context": "${data.context}"
                    }
                }
            with case_obj.create_evaluation_dataset() as dataset_path:
                azure_result = evaluate(
                    evaluation_name=f"{case_id}#{git_hash}",
                    data=dataset_path,
                    evaluators=evaluators,
                    evaluator_config=evaluator_config,
                    azure_ai_project=self.ai_foundry_manager.project_config,
                )
                case_obj.azure_eval_result = azure_result

    def post_processing(self) -> str:
        summary = {"cases": []}
        for case_id, case_obj in self.cases.items():
            summary["cases"].append({
                "case": case_obj.case_name,
                "results": case_obj.azure_eval_result
            })
        return json.dumps(summary, indent=3)

    def cleanup_temp_dir(self) -> None:
        """
        Cleans up the temporary directory.
        """
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.logger.info(f"Cleaned up temporary directory: {self.temp_dir}")

if __name__ == "__main__":
    evaluator = AgenticRagEvaluator(cases_dir="./evals/cases")
    try:
        summary = asyncio.run(evaluator.run_pipeline())
        print(summary)
    except Exception as e:
        import traceback
        formatted_tb = ''.join(traceback.format_tb(e.__traceback__))
        print(f"Pipeline failed: {e}\nStack trace:\n{formatted_tb}")
        exit(1)