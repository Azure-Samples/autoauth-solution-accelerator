# import asyncio
# import json
# import operator
#
# import pytest
#
# from src.pipeline.agenticRag.evaluator import AgenticRagEvaluator
#
#
# def check_case_metric(summary, test_case: str, metric_key: str, expected_value, comparator=operator.eq):
#     """
#     Helper function to verify that a given test case in the summary satisfies a metric condition.
#
#     Parameters:
#       summary (dict): The summary output from the evaluator.
#       test_case (str): A substring to identify the specific test case.
#       metric_key (str): The key for the metric to check (e.g. "FuzzyEvaluator.indel_similarity").
#       expected_value: The expected value for the metric.
#       comparator (callable): A function that takes two arguments and returns a boolean.
#                              Defaults to operator.eq for equality.
#     """
#     # Find the case by matching the provided substring
#     case = next((c for c in summary["cases"] if test_case in c["case"]), None)
#     assert case is not None, f"Case '{test_case}' not found in summary."
#     metrics = case.get("results", {}).get("metrics")
#     assert metrics is not None, f"Metrics not found for case '{test_case}'."
#     actual = metrics.get(metric_key)
#     assert actual is not None, f"Metric '{metric_key}' not found for case '{test_case}'."
#     assert comparator(actual, expected_value), (
#         f"Case '{test_case}': expected {metric_key} {comparator.__name__} {expected_value}, got {actual}."
#     )
#
# @pytest.fixture(scope="function")
# def agentic_rag_summary():
#     """
#     Runs the AgenticRagEvaluator pipeline once and yields its parsed summary output.
#     After tests complete, cleans up the temporary directory.
#     """
#     evaluator = AgenticRagEvaluator(cases_dir="./evals/cases", temp_dir="./temp_evaluation_rag")
#     loop = asyncio.get_event_loop()
#     summary_json = loop.run_until_complete(evaluator.run_pipeline())
#     summary = json.loads(summary_json) if isinstance(summary_json, str) else summary_json
#     yield summary
#     evaluator.cleanup_temp_dir()
#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_summary_structure(agentic_rag_summary):
#     """
#     Test that the summary has the expected structure:
#       - Must be a dict.
#       - Must contain a "cases" key.
#       - "cases" must be a list.
#     """
#     assert isinstance(agentic_rag_summary, dict), "Summary output should be a dictionary."
#     assert "cases" in agentic_rag_summary, "Summary output must have a 'cases' key."
#     assert isinstance(agentic_rag_summary["cases"], list), "'cases' must be a list."
#
#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_reasoning_and_policies_cases_present(agentic_rag_summary):
#     """
#     Verify that the summary contains both reasoning and policies cases.
#     This assumes:
#       - Reasoning cases include 'reasoning' in the case name.
#       - Policies cases include 'policies' in the case name.
#     """
#     cases = agentic_rag_summary["cases"]
#     reasoning_found = any("reasoning" in case["case"] for case in cases)
#     policies_found = any("policies" in case["case"] for case in cases)
#     assert reasoning_found, "At least one reasoning test case must be present in the summary."
#     assert policies_found, "At least one policies test case must be present in the summary."
#
#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_metrics_present_for_all_cases(agentic_rag_summary):
#     """
#     Confirm that every case in the summary contains evaluated output metrics.
#     """
#     cases = agentic_rag_summary["cases"]
#     for case in cases:
#         results = case.get("results")
#         assert results is not None, f"Case {case['case']} must include 'results'."
#         metrics = results.get("metrics")
#         assert metrics is not None, f"Case {case['case']} must include 'metrics' in its results."
#
# # Now each test is decorated with the evaluation markers and uses the evaluation_setup fixture.
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_001_negative_policies(agentic_rag_summary):
#     """
#     Verify that in the case 'agentic-rag-policies-001-negative.v0', the
#     FuzzyEvaluator.indel_similarity metric equals 100.
#     """
#     check_case_metric(
#         summary=agentic_rag_summary,
#         test_case="agentic-rag-policies-001-negative.v0",
#         metric_key="FuzzyEvaluator.indel_similarity",
#         expected_value=100,
#         comparator=operator.eq
#     )
#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_001_positive_policies(agentic_rag_summary):
#     """
#     Verify that in the case 'agentic-rag-policies-001-negative.v0', the
#     FuzzyEvaluator.indel_similarity metric equals 100.
#     """
#     check_case_metric(
#         summary=agentic_rag_summary,
#         test_case="agentic-rag-policies-001-positive.v0",
#         metric_key="FuzzyEvaluator.indel_similarity",
#         expected_value=60,
#         comparator=operator.ge
#     )
#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_001_positive_reasoning(agentic_rag_summary):
#     check_case_metric(
#         summary=agentic_rag_summary,
#         test_case="agentic-rag-reasoning-001-positive.v0",
#         metric_key="SemanticSimilarityEvaluator.semantic_similarity",
#         expected_value=0.90,
#         comparator=operator.ge
#     )
#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_001_negative_reasoning(agentic_rag_summary):
#     check_case_metric(
#         summary=agentic_rag_summary,
#         test_case="agentic-rag-reasoning-001-negative.v0",
#         metric_key="FuzzyEvaluator.indel_similarity",
#         expected_value=100,
#         comparator=operator.ge
#     )