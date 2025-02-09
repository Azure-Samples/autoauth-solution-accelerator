import asyncio
import glob
import os
import yaml
import importlib

from src.evals.case import Case, Evaluation
from azure.ai.evaluation import evaluate

# ------------------------------------------------------------------------------
# Dummy evaluator functions and project configuration for demonstration.
# Replace these with your actual evaluator implementations and Azure AI project details.
groundedness_eval = lambda data: data  # Placeholder evaluator
answer_length = lambda data: data       # Placeholder evaluator
azure_ai_project = "my_azure_ai_project"
# ------------------------------------------------------------------------------

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

    async def preprocess(self):
        """
        Asynchronous preprocessing step:
          - Loads YAML case files and populates self.case_configs.
          - For each test case, creates a Case instance.
          - For OCRNEREvaluator cases, immediately generates NER output and populates evaluations.
            (Here, the "response" is generated and stored but the scores are left as None.
             The similarity will be computed later in run_evaluations.)
        """
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
                # Create a Case instance for this test case.
                self.cases[case_id] = Case(case_name=case_id, case_class=evaluator_class_path)

                # For OCRNEREvaluator cases, generate NER responses and populate evaluations.
                if "OCRNEREvaluator" in evaluator_class_path:
                    # Ensure evaluator_class_path contains a colon.
                    if ":" not in evaluator_class_path:
                        print(f"Error: Evaluator class path '{evaluator_class_path}' is not in the format 'module:ClassName'.")
                        continue
                    # Initialize a global instance of OCRNEREvaluator if not already done.
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
                        # Generate NER responses asynchronously.
                        ner_response_result = await evaluator_instance.generate_ner_responses()
                    except Exception as e:
                        print(f"Error generating NER responses for case '{case_id}': {e}")
                        ner_response_result = {}
                    # Extract the generated output dictionary.
                    generated_output = ner_response_result.get("generated_output", {})
                    # Retrieve the expected output dictionary from YAML.
                    expected_ocr_output = evaluator_args.get("expected_output", {}).get("ocr_ner_results", {})

                    # Iterate over each top-level key (e.g. "patient_info", "physician_info", etc.)
                    for top_key, sub_dict in expected_ocr_output.items():
                        # For each sub-key, create an evaluation record.
                        for sub_key, expected_val in sub_dict.items():
                            query = f"{top_key}.{sub_key}"
                            actual_val = generated_output.get(top_key, {}).get(sub_key, "")
                            # Do not compute the similarity here; set scores to None.
                            evaluation_record = Evaluation(
                                query=query,
                                response=actual_val,
                                ground_truth=expected_val,
                                context=None,
                                conversation=None,
                                scores=None  # Leave scores as None until run_evaluations
                            )
                            self.cases[case_id].evaluations.append(evaluation_record)
                            self.results.append({
                                "case": case_id,
                                "query": query,
                                "ner_response": actual_val
                            })

    async def run_evaluations(self):
        """
        run_evaluations step:
          - Loops through each Case.
          - For each Case, uses its helper method to generate a temporary JSONL file from its evaluations.
          - Calls the Azure evaluation API (via evaluate()) with the temporary file.
          - Saves the returned evaluation result in the Case.
        """

        for case_id, case_obj in self.cases.items():
            with case_obj.create_evaluation_dataset() as dataset_path:
                azure_result = evaluate(
                    data=dataset_path,  # The temporary JSONL file path
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
                    # azure_ai_project=azure_ai_project,
                    # output_path="./myevalresults.json"
                )
                case_obj.azure_eval_result = azure_result
                print(azure_result)

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
        """
        Executes the complete pipeline in three steps:
          1. Preprocessing
          2. Running evaluations
          3. Post-processing
        """
        await self.preprocess()
        await self.run_evaluations()
        ### NEED TO ADDITIONALLY CHECK WHY RESPONSES != GENERATED ANSWERS FOR NER, AND FIX.
        return self.cases['ocr-ner-001-a.v0'].evaluations[0].to_dict()
        return self.post_processing()

# ------------------------------------------------------------------------------
# Example usage when running this module directly.
if __name__ == "__main__":
    pipeline = EvaluatorPipeline(cases_dir="./src/evals/cases")
    try:
        summary = asyncio.run(pipeline.run_pipeline())
        print(summary)
    except Exception as e:
        print(f"Pipeline failed: {e}")
        exit(1)