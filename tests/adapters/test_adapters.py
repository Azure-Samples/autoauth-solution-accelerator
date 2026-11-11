import asyncio
import json

import pytest

from src.agents.state import CaseState, Criterion, CriterionAssessment, Determination, PolicyMatch, ReviewerAction
from src.evals.adapters.runners import (
    DeterminationAgentAdapter,
    PolicyAgentAdapter,
    get_runner,
    resolve_stage,
    runner_mode,
)
from src.evals.adapters.traces import TraceToEvaluation
from src.pipeline.paprocessing.progress import CallbackReporter, NullReporter, make_reporter

from tests.agents.fakes import CLINICAL, PATIENT, PHYSICIAN, FakeLLM, FakePrompts, determination_llm

URL = "https://st.blob.core.windows.net/pre-auth-policies/policies/crohns.pdf"


# --- runner selection --------------------------------------------------------


def test_runner_mode_defaults_to_legacy(monkeypatch):
    monkeypatch.delenv("AUTOAUTH_RUNNER", raising=False)
    assert runner_mode() == "legacy"
    monkeypatch.setenv("AUTOAUTH_RUNNER", " Agents ")
    assert runner_mode() == "agents"


def test_runner_mode_rejects_unknown(monkeypatch):
    monkeypatch.setenv("AUTOAUTH_RUNNER", "langchain")
    with pytest.raises(ValueError):
        runner_mode()


@pytest.mark.parametrize(
    "alias,stage",
    [("AgenticRAG", "policy"), ("rag", "policy"), ("determination", "determine"), ("clinical", "extract")],
)
def test_resolve_stage_aliases(alias, stage):
    assert resolve_stage(alias) == stage


def test_resolve_stage_unknown():
    with pytest.raises(ValueError):
        resolve_stage("summarize")


def test_get_runner_agents_mode_builds_adapters():
    llm = FakeLLM({})
    policy = get_runner("rag", mode="agents", llm=llm, search=lambda q: [], prompt_manager=FakePrompts())
    determine = get_runner("determination", mode="agents", llm=llm, use_o1=True)
    assert isinstance(policy, PolicyAgentAdapter)
    assert isinstance(determine, DeterminationAgentAdapter)


# --- adapter output shapes (what the legacy evaluators consume) -------------


def test_determination_adapter_matches_legacy_schema():
    adapter = DeterminationAgentAdapter(llm=determination_llm("Fully Met", "Not Met"), caseId="c9")
    text, extra = asyncio.run(adapter.run(PATIENT, PHYSICIAN, CLINICAL, "policy text"))
    out = json.loads(text)
    assert extra == []
    assert out["Determination"] == "Rejected"
    assessments = out["DetailedAnalysis"]["PolicyCriteriaAssessment"]
    assert [a["Assessment"] for a in assessments] == ["Fully Met", "Not Met"]
    assert adapter.last_state.case_id == "c9"
    assert adapter.last_state.determination.warnings  # unverified provider/member data


def test_determination_adapter_without_policy_text():
    llm = FakeLLM({"final recommendation": {"decision": "Approved", "rationale": "r"}})
    text, _ = asyncio.run(DeterminationAgentAdapter(llm=llm).run(PATIENT, PHYSICIAN, CLINICAL, ""))
    assert json.loads(text)["Determination"] == "Needs More Information"


def test_policy_adapter_matches_agentic_rag_shape():
    llm = FakeLLM(
        {
            "formulator_user_prompt": {"optimized_query": "adalimumab crohns"},
            "evaluator_user_prompt": {"policies": [URL], "reasoning": ["matches"], "retry": False},
        }
    )
    hit = {"chunk_id": "c1", "parent_path": URL, "chunk": "text"}
    adapter = PolicyAgentAdapter(llm=llm, search=lambda q: [hit], prompt_manager=FakePrompts())
    out = asyncio.run(adapter.run(CLINICAL, max_retries=2))
    assert out == {
        "query": "adalimumab crohns",
        "policies": [URL],
        "evaluation": {"policies": [URL], "reasoning": ["matches"], "retry": False},
    }


def test_policy_adapter_no_match_shape():
    llm = FakeLLM({"formulator_user_prompt": {"optimized_query": "q"}})
    adapter = PolicyAgentAdapter(llm=llm, search=lambda q: [], prompt_manager=FakePrompts())
    assert asyncio.run(adapter.run(CLINICAL, max_retries=1)) == {
        "query": None,
        "policies": [],
        "evaluation": None,
    }


# --- traces ------------------------------------------------------------------


def decided_state():
    return CaseState(
        case_id="c1",
        trace_id="abcdef1234567890",
        patient_information=PATIENT,
        policies=[PolicyMatch(blob_url=URL)],
        policy_search_reasoning=["r1", "r2"],
        criteria=[Criterion(id="dx", text="Diagnosis confirmed")],
        assessments=[CriterionAssessment(criterion_id="dx", status="Fully Met")],
        determination=Determination(decision="Approved", rationale="ok"),
    )


@pytest.mark.parametrize(
    "query,scenario,expected",
    [
        ("Associated Policies", "policy", "policies/crohns.pdf"),
        ("Reasoning", "reasoning", "r1\nr2"),
        ("patient_information.patient_name", None, "Jane Doe"),
        (".Determination", None, "Approved"),
        (".DetailedAnalysis.PolicyCriteriaAssessment[0].CriterionName", None, "Diagnosis confirmed"),
    ],
)
def test_resolve(query, scenario, expected):
    assert TraceToEvaluation.resolve(decided_state(), query, scenario) == expected


def test_resolve_missing_path():
    with pytest.raises(KeyError):
        TraceToEvaluation.resolve(decided_state(), "patient_information.dob")


def test_reviewer_actions_become_eval_case():
    state = decided_state()
    state.reviewer_actions = [
        ReviewerAction(field="patient_information.patient_name", action="accept"),
        ReviewerAction(field="decision", action="edit", original="Approved", corrected="Rejected", note="step therapy"),
        ReviewerAction(field="clinical_information.diagnosis", action="reject", corrected="UC"),
    ]
    case = TraceToEvaluation.from_reviewer_actions(state)
    [(name, body)] = case.items()
    assert name == "reviewer-c1-abcdef12.v0"
    assert body["metrics"] == ["FuzzyEvaluator"]
    assert body["evaluations"] == [
        {"query": ".Determination", "ground_truth": "Rejected", "note": "step therapy"},
        {"query": "clinical_information.diagnosis", "ground_truth": "UC"},
    ]


# --- progress ----------------------------------------------------------------


def test_callback_reporter_and_factory():
    events = []
    reporter = make_reporter(streamlit=True, progress_callback=lambda *e: events.append(e))
    assert isinstance(reporter, CallbackReporter)
    reporter.step("extracting", 0.25)
    reporter.success("done")
    reporter.error("boom")
    assert events == [("step", "extracting", 0.25), ("success", "done", 1.0), ("error", "boom", None)]
    assert isinstance(make_reporter(), NullReporter)


# --- Agent Framework binding (optional dependency) ---------------------------


def test_af_binding_round_trip():
    pytest.importorskip("agent_framework")
    from src.agents.af_binding import AFJsonLLM, JsonLLMChatClient

    inner = FakeLLM({"reviewer": {"decision": "Approved"}})
    llm = AFJsonLLM(JsonLLMChatClient(inner))
    out = asyncio.run(llm(system="You are a reviewer.", user="Decide.", max_tokens=10, temperature=0, top_p=1))
    assert out == {"decision": "Approved"}
    assert "reviewer" in inner.calls[0]["system"]
    assert "Decide." in inner.calls[0]["user"]
