import asyncio
import json
import operator

import pytest

from src.pipeline.autoDetermination.evaluator import AutoDeterminationEvaluator


def check_case_metric(
    summary, test_case: str, metric_key: str, expected_value, comparator=operator.eq
):
    """
    Helper function to verify that a given test case in the summary satisfies a metric condition.

    Parameters:
      summary (dict): The summary output from the evaluator.
      test_case (str): A substring to identify the specific test case.
      metric_key (str): The key for the metric to check (e.g. "FuzzyEvaluator.indel_similarity").
      expected_value: The expected value for the metric.
      comparator (callable): A function that takes two arguments and returns a boolean.
                             Defaults to operator.eq for equality.
    """
    # Find the case by matching the provided substring
    case = next((c for c in summary["cases"] if test_case in c["case"]), None)
    assert case is not None, f"Case '{test_case}' not found in summary."
    metrics = case.get("results", {}).get("metrics")
    assert metrics is not None, f"Metrics not found for case '{test_case}'."
    actual = metrics.get(metric_key)
    assert (
        actual is not None
    ), f"Metric '{metric_key}' not found for case '{test_case}'."
    assert comparator(
        actual, expected_value
    ), f"Case '{test_case}': expected {metric_key} {comparator.__name__} {expected_value}, got {actual}."


@pytest.fixture(scope="session")
def autodetermination_summary():
    """
    Runs the AgenticRagEvaluator pipeline once and yields its parsed summary output.
    After tests complete, cleans up the temporary directory.
    """
    evaluator = AutoDeterminationEvaluator(
        cases_dir="./evals/cases", temp_dir="./temp_evaluation_rag"
    )
    loop = asyncio.get_event_loop()
    summary_json = loop.run_until_complete(evaluator.run_pipeline())
    summary = (
        json.loads(summary_json) if isinstance(summary_json, str) else summary_json
    )
    yield summary
    evaluator.cleanup_temp_dir()


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_summary_structure(autodetermination_summary):
    """
    Test that the summary has the expected structure:
      - Must be a dict.
      - Must contain a "cases" key.
      - "cases" must be a list.
    """
    assert isinstance(
        autodetermination_summary, dict
    ), "Summary output should be a dictionary."
    assert (
        "cases" in autodetermination_summary
    ), "Summary output must have a 'cases' key."
    assert isinstance(
        autodetermination_summary["cases"], list
    ), "'cases' must be a list."


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_metrics_present_for_all_cases(autodetermination_summary):
    """
    Confirm that every case in the summary contains evaluated output metrics.
    """
    cases = autodetermination_summary["cases"]
    for case in cases:
        results = case.get("results")
        assert results is not None, f"Case {case['case']} must include 'results'."
        metrics = results.get("metrics")
        assert (
            metrics is not None
        ), f"Case {case['case']} must include 'metrics' in its results."


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_001_positive_determination(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-001-positive-determination.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_001_positive_fully_met_criteria(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-001-positive-fully-met-criteria.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_001_negative_determination(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-001-negative-determination.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_001_negative_partial_met_criteria(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-001-negative-partial-criteria.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_001_positive_rationale(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-001-positive-rationale.v0",
        metric_key="FactualCorrectnessEvaluator.factual_correctness",
        expected_value=0.33,
        comparator=operator.ge,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_001_negative_rationale(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-001-negative-rationale.v0",
        metric_key="FactualCorrectnessEvaluator.factual_correctness",
        expected_value=0.60,
        comparator=operator.ge,
    )


#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_002_positive_determination(autodetermination_summary):
#     check_case_metric(
#         summary=autodetermination_summary,
#         test_case="autodetermination-decision-002-positive-determination.v0",
#         metric_key="FuzzyEvaluator.indel_similarity",
#         expected_value=100,
#         comparator=operator.eq
#     )
#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_002_positive_fully_met_criteria(autodetermination_summary):
#     check_case_metric(
#         summary=autodetermination_summary,
#         test_case="autodetermination-decision-002-positive-fully-met-criteria.v0",
#         metric_key="FuzzyEvaluator.indel_similarity",
#         expected_value=100,
#         comparator=operator.eq
#     )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_002_negative_determination(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-002-negative-determination.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_002_negative_partial_met_criteria(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-002-negative-partial-criteria.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_002_positive_rationale(autodetermination_summary):
#     check_case_metric(
#         summary=autodetermination_summary,
#         test_case="autodetermination-decision-002-positive-rationale.v0",
#         metric_key="FactualCorrectnessEvaluator.factual_correctness",
#         expected_value=0.60,
#         comparator=operator.ge
#     )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_002_negative_rationale(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-002-negative-rationale.v0",
        metric_key="FactualCorrectnessEvaluator.factual_correctness",
        expected_value=0.60,
        comparator=operator.ge,
    )


# --- Test cases for 003 ---


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_003_positive_determination(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-003-positive-determination.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


# @TODO: need to re-evaluate for situations were not fully met but policy calls for it.
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_003_positive_fully_met_criteria(autodetermination_summary):
#     check_case_metric(
#         summary=autodetermination_summary,
#         test_case="autodetermination-decision-003-positive-fully-met-criteria.v0",
#         metric_key="FuzzyEvaluator.indel_similarity",
#         expected_value=100,
#         comparator=operator.eq,
#     )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_003_negative_determination(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-003-negative-determination.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_003_negative_partial_met_criteria(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-003-negative-partial-criteria.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_003_positive_rationale(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-003-positive-rationale.v0",
        metric_key="FactualCorrectnessEvaluator.factual_correctness",
        expected_value=0.40,
        comparator=operator.ge,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_003_negative_rationale(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-003-negative-rationale.v0",
        metric_key="FactualCorrectnessEvaluator.factual_correctness",
        expected_value=0.60,
        comparator=operator.ge,
    )


# --- Test cases for 004 ---


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_004_positive_determination(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-004-positive-determination.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_004_positive_fully_met_criteria(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-004-positive-fully-met-criteria.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_004_negative_determination(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-004-negative-determination.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_004_negative_partial_met_criteria(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-004-negative-partial-criteria.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_004_positive_rationale(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-004-positive-rationale.v0",
        metric_key="FactualCorrectnessEvaluator.factual_correctness",
        expected_value=0.33,
        comparator=operator.ge,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_004_negative_rationale(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-004-negative-rationale.v0",
        metric_key="FactualCorrectnessEvaluator.factual_correctness",
        expected_value=0.33,
        comparator=operator.ge,
    )


# --- Test cases for 005 ---


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_005_positive_determination(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-005-positive-determination.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_005_positive_fully_met_criteria(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-005-positive-fully-met-criteria.v0",
        metric_key="FuzzyEvaluator.indel_similarity",
        expected_value=100,
        comparator=operator.eq,
    )


# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_005_negative_determination(autodetermination_summary):
#     check_case_metric(
#         summary=autodetermination_summary,
#         test_case="autodetermination-decision-005-negative-determination.v0",
#         metric_key="FuzzyEvaluator.indel_similarity",
#         expected_value=100,
#         comparator=operator.eq,
#     )
#
#
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_005_negative_partial_met_criteria(autodetermination_summary):
#     check_case_metric(
#         summary=autodetermination_summary,
#         test_case="autodetermination-decision-005-negative-partial-criteria.v0",
#         metric_key="FuzzyEvaluator.indel_similarity",
#         expected_value=100,
#         comparator=operator.eq,
#     )


@pytest.mark.evaluation
@pytest.mark.usefixtures("evaluation_setup")
def test_policies_005_positive_rationale(autodetermination_summary):
    check_case_metric(
        summary=autodetermination_summary,
        test_case="autodetermination-decision-005-positive-rationale.v0",
        metric_key="FactualCorrectnessEvaluator.factual_correctness",
        expected_value=0.50,
        comparator=operator.ge,
    )


# @ TODO: This test case is commented out for performance.
# @pytest.mark.evaluation
# @pytest.mark.usefixtures("evaluation_setup")
# def test_policies_005_negative_rationale(autodetermination_summary):
#     check_case_metric(
#         summary=autodetermination_summary,
#         test_case="autodetermination-decision-005-negative-rationale.v0",
#         metric_key="FactualCorrectnessEvaluator.factual_correctness",
#         expected_value=0.40,
#         comparator=operator.ge
#     )
