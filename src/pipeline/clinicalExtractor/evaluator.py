import asyncio
import glob
import os
import yaml
import importlib
from typing import Any, Dict, List, Tuple


class EvaluatorPipeline:
    def __init__(self, cases_dir: str):
        """
        Initialize the pipeline with the directory containing the case YAML files.

        Args:
            cases_dir: Path to the folder containing case YAML configuration files.
        """
        self.cases_dir = cases_dir
        # List of tuples: (file_path, case_id, evaluator_class_path, evaluator_args)
        self.case_configs: List[Tuple[str, str, str, Dict[str, Any]]] = []
        # List of evaluation results (one per test case)
        self.results: List[Dict[str, Any]] = []

    def aggregate_data(self) -> None:
        """
        Aggregates the data by scanning the cases directory for YAML files and loading their configurations.

        Each YAML file is expected to have:
          - A root key matching the file name (without extension) that contains metadata including a "cases" array.
          - For each test case ID in the "cases" array, a sibling key whose value is an object containing:
              - "class": The evaluator class (in the form "module.submodule:ClassName").
              - "args": A mapping of keyword arguments to be passed to the evaluator.
        """
        # Search for all YAML files in the provided directory.
        case_files = glob.glob(os.path.join(self.cases_dir, "*.yaml"))
        for file_path in case_files:
            with open(file_path, "r") as f:
                config = yaml.safe_load(f)

            # Derive the expected root key from the file name (without extension)
            file_id = os.path.splitext(os.path.basename(file_path))[0]
            if file_id not in config:
                print(f"Warning: Expected root key '{file_id}' not found in {file_path}. Skipping.")
                continue

            root_obj = config[file_id]
            cases_list = root_obj.get("cases", [])
            if not cases_list:
                print(f"Warning: No cases found under root key '{file_id}' in {file_path}. Skipping.")
                continue

            # For each test case ID listed in the "cases" array, look up its definition.
            for case_id in cases_list:
                if case_id not in config:
                    print(f"Warning: Test case '{case_id}' not found in file {file_path}. Skipping this test case.")
                    continue

                test_case_obj = config[case_id]
                evaluator_class_path = test_case_obj.get("class")
                if not evaluator_class_path:
                    print(f"Warning: No 'class' defined for test case '{case_id}' in file {file_path}. Skipping.")
                    continue

                evaluator_args = test_case_obj.get("args", {})
                self.case_configs.append((file_path, case_id, evaluator_class_path, evaluator_args))

    async def run_evaluations(self) -> None:
        """
        Runs the evaluation step for each test case configuration asynchronously.

        For each test case, dynamically import the evaluator class, instantiate it with its arguments,
        and schedule its asynchronous run() method.

        If any evaluator fails, the exception will be propagated and the pipeline will fail.
        """
        tasks = []
        for file_path, case_id, evaluator_class_path, evaluator_args in self.case_configs:
            try:
                # Expect evaluator_class_path to be in the form "module.submodule:ClassName"
                module_path, class_name = evaluator_class_path.split(":")
                module = importlib.import_module(module_path)
                evaluator_class = getattr(module, class_name)
            except Exception as e:
                raise ImportError(
                    f"Error importing evaluator class from '{evaluator_class_path}' in {file_path} for case '{case_id}': {e}"
                )

            # Instantiate the evaluator by passing the args dictionary as is.
            try:
                evaluator = evaluator_class(args=evaluator_args)
            except Exception as e:
                raise Exception(
                    f"Error instantiating evaluator for test case '{case_id}' in {file_path} with args {evaluator_args}: {e}"
                )

            # Schedule its asynchronous run() method.
            tasks.append(asyncio.create_task(evaluator.run()))

        # Await all tasks.
        # Without return_exceptions=True, if any task fails, an exception will be raised.
        self.results = await asyncio.gather(*tasks)

    def summarize(self) -> Dict[str, Any]:
        """
        Summarizes the results of all evaluations into a JSON-like dictionary.

        The summary includes:
            - case: the test case ID,
            - input: the input provided (e.g. "uploaded_files" from args),
            - expected_output: the expected output (from args),
            - generated_output: the evaluator's full output,
            - evaluations: the detailed comparison entries with metrics,
            - pass: the overall pass/fail status,
            - dt_started: timestamp when evaluation started,
            - dt_completed: timestamp when evaluation completed.

        Returns:
            A dictionary summarizing the evaluation results for each test case.
        """
        summary: Dict[str, Any] = {"cases": []}
        for idx, result in enumerate(self.results):
            file_path, case_id, evaluator_class_path, evaluator_args = self.case_configs[idx]
            case_summary = {
                "case": case_id,
                "input": evaluator_args.get("uploaded_files"),
                "expected_output": evaluator_args.get("expected_output"),
                "generated_output": result,  # full evaluator output
                "evaluations": result.get("evaluations", []),
                "pass": result.get("pass", False),
                "dt_started": result.get("dt_started"),
                "dt_completed": result.get("dt_completed")
            }
            summary["cases"].append(case_summary)
        return summary

    async def run_pipeline(self) -> Dict[str, Any]:
        """
        Executes the complete pipeline:
          1. Aggregates data from the YAML cases.
          2. Runs the evaluations asynchronously.
          3. Summarizes and returns the final output.

        Returns:
            A dictionary containing the summary of evaluations across all test cases.

        Raises:
            Exception: Propagates any exception encountered during evaluations.
        """
        self.aggregate_data()
        await self.run_evaluations()
        return self.summarize()


# Example usage when running this module directly.
if __name__ == "__main__":
    pipeline = EvaluatorPipeline(cases_dir="./src/evals/cases")
    try:
        summary = asyncio.run(pipeline.run_pipeline())
        print(summary)
    except Exception as e:
        print(f"Pipeline failed: {e}")
        exit(1)