import asyncio
import glob
import os
import yaml
import importlib
import traceback

from src.aifoundry.aifoundry_helper import AIFoundryManager
from src.evals.case import Case, Evaluation
from azure.ai.evaluation import evaluate
import subprocess

# -------------------------------------------------------------------------------
# Initialize the Azure AI project client.
# It will check for the connection string in the environment variable.
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# -------------------------------------------------------------------------------
class EvaluatorPipeline:
    def __init__(self, cases_dir: str):
        """
        Initialize the pipeline with the directory containing YAML case definitions.
        Sets up an object (self.cases) to hold Case instances.
        Also prepares a global evaluators dictionary to hold shared evaluator instances.
        """
        self.cases_dir = cases_dir
        self.case_configs = []  # List of tuples: (file_path, case_id, evaluator_class_path, evaluator_args)
        self.cases = {}         # Dictionary mapping case_id to Case instance
        self.results = []       # For logging raw NER or evaluator responses
        self.global_evaluators = {}  # For example: {"OCRNEREvaluator": instance}
        self.ai_foundry_manager = AIFoundryManager()

    def get_git_hash(self) -> str:
        """
        Retrieves the current Git commit hash (short version).
        If unable to retrieve it, returns "unknown".
        """
        try:
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.STDOUT
            ).decode().strip()
            return git_hash
        except Exception as e:
            print(f"Error retrieving Git hash: {e}")
            return "unknown"

    async def preprocess(self):
        def flatten_fields(expected: dict, generated: dict, prefix: str = "") -> list:
            evaluations = []
            for key, expected_val in expected.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                if isinstance(expected_val, dict):
                    generated_sub = generated.get(key, {}) if isinstance(generated, dict) else {}
                    evaluations.extend(flatten_fields(expected_val, generated_sub, prefix=new_prefix))
                else:
                    actual_val = generated.get(key, "") if isinstance(generated, dict) else ""
                    # Convert both leaf values to string to be safe.
                    evaluations.append((new_prefix, str(expected_val), str(actual_val)))
            return evaluations

        case_files = glob.glob(os.path.join(self.cases_dir, "*.yaml"))
        for file_path in case_files:
            with open(file_path, "r") as f:
                config = yaml.safe_load(f)
            file_id = os.path.splitext(os.path.basename(file_path))[0]
            if file_id not in config:
                print(f"Warning: Expected root key '{file_id}' not found in {file_path}. Skipping.")
                continue
            root_obj = config[file_id]
            cases_list = root_obj.get("cases", [])
            if not cases_list:
                print(f"Warning: No cases found under root key '{file_id}' in {file_path}. Skipping.")
                continue
            for case_id in cases_list:
                if case_id not in config:
                    print(f"Warning: Test case '{case_id}' not found in file {file_path}. Skipping.")
                    continue
                test_case_obj = config[case_id]
                evaluator_class_path = test_case_obj.get("class")
                if not evaluator_class_path:
                    print(f"Warning: No 'class' defined for test case '{case_id}' in file {file_path}. Skipping.")
                    continue
                evaluator_args = test_case_obj.get("args", {})
                self.case_configs.append((file_path, case_id, evaluator_class_path, evaluator_args))
                self.cases[case_id] = Case(case_name=case_id, case_class=evaluator_class_path)
                if "OCRNEREvaluator" in evaluator_class_path:
                    if ":" not in evaluator_class_path:
                        print(
                            f"Error: Evaluator class path '{evaluator_class_path}' is not in the format 'module:ClassName'.")
                        continue
                    if "OCRNEREvaluator" not in self.global_evaluators:
                        try:
                            module_path, class_name = evaluator_class_path.split(":")
                            module = importlib.import_module(module_path)
                            evaluator_class = getattr(module, class_name)
                            evaluator_instance = evaluator_class(args=evaluator_args)
                            self.global_evaluators["OCRNEREvaluator"] = evaluator_instance
                        except Exception as e:
                            print(f"Error initializing OCRNEREvaluator for case '{case_id}': {e}")
                            continue
                    else:
                        evaluator_instance = self.global_evaluators["OCRNEREvaluator"]

                    try:
                        ner_response_result = await evaluator_instance.generate_ner_responses()
                    except Exception as e:
                        print(f"Error generating NER responses for case '{case_id}': {e}")
                        ner_response_result = {}
                    generated_output = ner_response_result.get("generated_output", {})
                    expected_ocr_output = evaluator_args.get("expected_output", {}).get("ocr_ner_results", {})
                    flattened = flatten_fields(expected_ocr_output, generated_output, prefix="")
                    for query, expected_val, actual_val in flattened:
                        evaluation_record = Evaluation(
                            query=query,
                            response=actual_val,
                            ground_truth=expected_val,
                            context=None,
                            conversation=None,
                            scores=None
                        )
                        self.cases[case_id].evaluations.append(evaluation_record)
                        self.results.append({
                            "case": case_id,
                            "query": query,
                            "ner_response": actual_val
                        })

    async def run_evaluations(self):
        git_hash = self.get_git_hash()
        for case_id, case_obj in self.cases.items():
            with case_obj.create_evaluation_dataset() as dataset_path:
                azure_result = evaluate(
                    evaluation_name=f"{case_id}::{git_hash}",
                    data=dataset_path,
                    evaluators={
                        "OCRNEREvaluator": self.global_evaluators.get("OCRNEREvaluator")
                    },
                    evaluator_config={
                        "OCRNEREvaluator": {
                            "column_mapping": {
                                "query": "${data.query}",
                                "ground_truth": "${data.ground_truth}",
                                "response": "${data.response}"
                            }
                        }
                    },
                    azure_ai_project=self.ai_foundry_manager.project_config,
                    fail_on_evaluator_errors=True,
                )
                case_obj.azure_eval_result = azure_result

    def post_processing(self) -> dict:
        """
        Post-processing step: Summarizes results for each Case,
        including evaluations and Azure evaluation results.
        """
        summary = {"cases": []}
        for case_id, case_obj in self.cases.items():
            summary["cases"].append({
                "case": case_obj.case_name,
                "case_class": case_obj.case_class,
                "evaluations": [ev.to_dict() for ev in case_obj.evaluations],
                "azure_eval_result": case_obj.azure_eval_result
            })
        summary["raw_results"] = self.results
        return summary

    async def run_pipeline(self) -> dict:
        await self.preprocess()
        # for evaluation in self.cases['ocr-ner-001-a.v0'].evaluations:
        #     import json
        #     print(json.dumps(evaluation.to_dict()))
        await self.run_evaluations()
        # return {"status": "success"}
        # # import json
        # # print(json.dumps(self.post_processing(), indent=3))
        return self.post_processing()

# ------------------------------------------------------------------------------
# Example usage when running this module directly.
if __name__ == "__main__":
    pipeline = EvaluatorPipeline(cases_dir="./src/evals/cases")
    try:
        summary = asyncio.run(pipeline.run_pipeline())
        print(summary)
    except Exception as e:
        formatted_tb = ''.join(traceback.format_tb(e.__traceback__))
        print(f"Pipeline failed: {e}, stack trace: {formatted_tb}")
        exit(1)