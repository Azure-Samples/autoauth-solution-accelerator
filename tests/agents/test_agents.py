import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.agents.criteria_agent import CriteriaAgent
from src.agents.determination_agent import DeterminationAgent, normalize_decision
from src.agents.llm import ContextLengthExceeded, LLMError, parse_json_object
from src.agents.policy_agent import PolicyAgent
from src.agents.state import CaseState, Freshness, PolicyMatch

from tests.agents.fakes import (
    CLINICAL,
    PATIENT,
    PHYSICIAN,
    FakeLLM,
    FakePrompts,
    determination_llm,
)

POLICY_URL = "https://st.blob.core.windows.net/pre-auth-policies/policies/crohns.pdf"


def run(coro):
    return asyncio.run(coro)


def case(**kw):
    return CaseState(
        case_id="case-1",
        patient_information=PATIENT,
        physician_information=PHYSICIAN,
        clinical_information=CLINICAL,
        policies=[PolicyMatch.from_text("Adalimumab is covered when ...", POLICY_URL)],
        **kw,
    )


async def decide(llm, state):
    state = await CriteriaAgent(llm).run(state)
    return await DeterminationAgent(llm).run(state)


# --- llm ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ['{"a": 1}', '```json\n{"a": 1}\n```', 'Here you go: {"a": 1} thanks', {"a": 1}],
)
def test_parse_json_object(raw):
    assert parse_json_object(raw) == {"a": 1}


@pytest.mark.parametrize("raw", ["[1, 2]", "no json here"])
def test_parse_json_object_rejects_non_objects(raw):
    with pytest.raises(LLMError):
        parse_json_object(raw)


# --- criteria agent ----------------------------------------------------------


def test_criteria_missing_assessment_is_not_met():
    llm = determination_llm("Fully Met")  # only the first criterion is assessed
    state = run(CriteriaAgent(llm).run(case()))
    assert [c.id for c in state.criteria] == ["diagnosis", "step-therapy"]
    by_id = {a.criterion_id: a for a in state.assessments}
    assert by_id["diagnosis"].status == "Fully Met"
    assert by_id["step-therapy"].status == "Not Met"
    assert "No assessment returned" in by_id["step-therapy"].notes


def test_criteria_without_policy_text_makes_no_calls():
    llm = FakeLLM({})
    state = CaseState(case_id="c", policies=[PolicyMatch(blob_url=POLICY_URL)])
    state = run(CriteriaAgent(llm).run(state))
    assert state.criteria == [] and llm.calls == []


def test_criteria_summarizes_on_context_overflow():
    llm = determination_llm("Fully Met", "Fully Met")
    llm.replies["policy analyst"] = [ContextLengthExceeded("too long"), llm.replies["policy analyst"]]
    summarized = []

    async def summarize(text):
        summarized.append(text)
        return "short policy"

    state = run(CriteriaAgent(llm, summarize_policy=summarize).run(case()))
    assert summarized and len(state.criteria) == 2
    assert "short policy" in llm.calls[1]["user"]


# --- determination agent -----------------------------------------------------


def test_rule_blocks_approval_with_unmet_criterion():
    state = run(decide(determination_llm("Fully Met", "Partially Met"), case()))
    assert state.determination.decision == "Rejected"
    assert "[Decision rule applied: Approved -> Rejected.]" in state.determination.rationale


def test_model_decision_stands_when_all_met():
    state = run(decide(determination_llm("Fully Met", "Fully Met"), case()))
    assert state.determination.decision == "Approved"
    assert "Decision rule applied" not in state.determination.rationale


def test_no_policy_needs_more_information():
    state = case()
    state.policies = []
    llm = FakeLLM({"final recommendation": {"decision": "Approved", "rationale": "r"}})
    state = run(DeterminationAgent(llm).run(state))
    assert state.determination.decision == "Needs More Information"
    needed = [m.information_needed for m in state.determination.missing_information]
    assert "Applicable coverage policy" in needed


@pytest.mark.parametrize(
    "raw,expected",
    [("denied", "Rejected"), ("APPROVE", "Approved"), ("maybe", "Needs More Information")],
)
def test_normalize_decision(raw, expected):
    assert normalize_decision(raw) == expected


def test_freshness_warnings_are_advisory_only():
    stale_policy = Freshness(
        kind="policy",
        subject=POLICY_URL,
        as_of=datetime.now(timezone.utc) - timedelta(days=800),
        source="test",
    )
    fresh_case = case()
    stale_case = case()
    stale_case.policies[0].freshness = stale_policy

    a = run(decide(determination_llm("Fully Met", "Fully Met"), fresh_case))
    b = run(decide(determination_llm("Fully Met", "Fully Met"), stale_case))

    assert a.determination.decision == b.determination.decision == "Approved"
    assert a.determination.rationale == b.determination.rationale
    assert any(w.startswith("policy (stale)") for w in b.determination.warnings)
    assert not any(w.startswith("policy") for w in a.determination.warnings)
    kinds = {w.split(" ")[0] for w in a.determination.warnings}
    assert kinds == {"provider_affiliation", "member_eligibility", "clinical_evidence"}
    assert "warnings" not in b.to_legacy_determination()
    assert "Warnings" not in b.to_legacy_determination()


# --- policy agent ------------------------------------------------------------


def hit(url, last_modified=None):
    return {
        "chunk_id": "c1",
        "parent_path": url,
        "chunk": "policy text",
        "caption": "covered when",
        "score": 2.5,
        "last_modified": last_modified,
    }


def test_policy_agent_retries_with_judge_feedback():
    llm = FakeLLM(
        {
            "formulator_user_prompt": [
                {"optimized_query": "q1"},
                {"optimized_query": "q2"},
            ],
            "evaluator_user_prompt": [
                {"policies": [], "reasoning": ["wrong drug class"], "retry": True},
                {"policies": [POLICY_URL], "reasoning": [f"{POLICY_URL} matches"], "retry": False},
            ],
        }
    )
    searched = []

    def search(query):
        searched.append(query)
        return [hit(POLICY_URL, "2026-01-15T00:00:00Z")]

    agent = PolicyAgent(llm=llm, search=search, prompts=FakePrompts())
    state = run(agent.run(CaseState(case_id="c", clinical_information=CLINICAL)))

    assert searched == ["q1", "q2"]
    assert "wrong drug class" in llm.calls[2]["user"]
    assert state.expanded_query == "q2"
    [match] = state.policies
    assert match.blob_url == POLICY_URL and match.reasoning == f"{POLICY_URL} matches"
    assert match.freshness.source == "search.last_modified"
    assert match.freshness.as_of is not None


def test_policy_agent_gives_up_after_max_attempts():
    llm = FakeLLM({"formulator_user_prompt": {"optimized_query": "q"}})
    agent = PolicyAgent(llm=llm, search=lambda q: [], prompts=FakePrompts(), max_attempts=2)
    state = run(agent.run(CaseState(case_id="c", clinical_information=CLINICAL)))
    assert state.policies == [] and state.expanded_query is None
    assert len(llm.calls) == 2


def test_matches_without_last_modified_is_unknown():
    [match] = PolicyAgent._matches([POLICY_URL], [], [hit(POLICY_URL)])
    assert match.freshness.status() == "unknown"
    assert "last-modified" in match.freshness.note
