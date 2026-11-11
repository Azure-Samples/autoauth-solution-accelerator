"""Test doubles for the agents: a scripted JsonLLM and a prompt manager stub."""

from __future__ import annotations

from typing import Any, Dict, List


class FakeLLM:
    """Returns the scripted reply whose key appears in the system or user prompt.
    A list reply is consumed one item per call; an Exception item is raised."""

    def __init__(self, replies: Dict[str, Any]) -> None:
        self.replies = replies
        self.calls: List[Dict[str, Any]] = []

    async def __call__(self, *, system: str, user: str, **params: Any) -> Dict[str, Any]:
        self.calls.append({"system": system, "user": user, **params})
        prompt = system + "\n" + user
        for key, reply in self.replies.items():
            if key in prompt:
                value = reply.pop(0) if isinstance(reply, list) else reply
                if isinstance(value, Exception):
                    raise value
                return value
        raise AssertionError(f"No scripted reply for system prompt: {system[:80]!r}")


class FakePrompts:
    """Names the template in the rendered prompt so FakeLLM can route on it."""

    def get_prompt(self, name: str, **kwargs: Any) -> str:
        return f"[{name}] " + " ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


CLINICAL = {
    "diagnosis": "Crohn's disease",
    "treatment_request": {"name_of_medication_or_procedure": "Adalimumab"},
    "prior_treatments_and_results": "Failed mesalamine",
}
PATIENT = {"patient_name": "Jane Doe"}
PHYSICIAN = {"physician_name": "Dr. Smith", "specialty": "Gastroenterology"}

CRITERIA_REPLY = {
    "criteria": [
        {"id": "diagnosis", "text": "Confirmed Crohn's diagnosis", "policy_reference": "1.a"},
        {"id": "step-therapy", "text": "Failed one conventional therapy", "policy_reference": "1.b"},
    ]
}


def assessments(*statuses: str) -> Dict[str, Any]:
    ids = ["diagnosis", "step-therapy"]
    return {
        "assessments": [
            {
                "criterion_id": cid,
                "status": status,
                "evidence": f"evidence for {cid}",
                "source_fields": ["clinical_information.diagnosis"],
            }
            for cid, status in zip(ids, statuses)
        ]
    }


def determination_llm(*statuses: str, decision: str = "Approved") -> FakeLLM:
    return FakeLLM(
        {
            "policy analyst": CRITERIA_REPLY,
            "clinical reviewer": assessments(*statuses),
            "final recommendation": {
                "decision": decision,
                "rationale": "Model rationale.",
                "missing_information": [],
            },
        }
    )
