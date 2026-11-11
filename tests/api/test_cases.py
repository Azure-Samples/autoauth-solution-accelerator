"""Reviewer UI API: runs offline against the in-memory demo store."""

import sys

import pytest
import yaml
from fastapi.testclient import TestClient

from app.backend.api.app import app
from app.backend.api.demo_data import store


@pytest.fixture()
def client():
    store.reset()
    with TestClient(app) as c:
        yield c
    store.reset()


def _statuses(report):
    return {item["kind"]: item["status"] for item in report}


def test_queue_sorted_by_sla_with_freshness_summary(client):
    cases = client.get("/api/cases").json()["cases"]
    assert [c["case_id"] for c in cases][0] == "PA-1042"
    assert [c["sla_left_hours"] for c in cases] == sorted(c["sla_left_hours"] for c in cases)
    by_id = {c["case_id"]: c for c in cases}
    assert by_id["PA-1042"]["freshness"]["overall"] == "stale"
    assert by_id["PA-1031"]["freshness"]["label"] == "all fresh"
    assert by_id["PA-1037"]["status"] == "running"
    assert by_id["PA-1037"]["recommendation"] is None

    flagged = client.get("/api/cases", params={"freshness": "flagged"}).json()["cases"]
    assert "PA-1031" not in {c["case_id"] for c in flagged}


def test_case_detail_has_cited_fields_and_freshness(client):
    case = client.get("/api/cases/PA-1042").json()
    assert case["recommendation"]["label"] == "Approve"
    assert case["recommendation"]["criteria_met"] == 3
    assert _statuses(case["freshness_report"]) == {
        "clinical_evidence": "aging",
        "provider_affiliation": "stale",
        "member_eligibility": "unknown",
        "policy": "fresh",
    }
    quote = case["field_citations"]["patient_information.patient_id"][0]["quote"]
    pages = case["documents"]["form.pdf"]
    assert any(quote in line for page in pages for line in page)
    assert [s["state"] for s in case["workflow"]][5] == "current"
    assert client.get("/api/cases/PA-9999").status_code == 404


def test_reverify_clears_stale_warning_but_keeps_recommendation(client):
    before = client.get("/api/cases/PA-1042").json()
    body = client.post("/api/cases/PA-1042/reverify/provider_affiliation").json()
    assert _statuses(body["freshness_report"])["provider_affiliation"] == "fresh"
    assert not any(w.startswith("provider_affiliation") for w in body["warnings"])
    after = client.get("/api/cases/PA-1042").json()
    assert after["recommendation"]["decision"] == before["recommendation"]["decision"]
    assert client.post("/api/cases/PA-1042/reverify/nope").status_code == 400


def test_reviewer_edit_becomes_eval_case(client):
    client.post(
        "/api/cases/PA-1042/actions",
        json={
            "field": "clinical_information.diagnosis",
            "action": "edit",
            "original": "Crohn's disease",
            "corrected": "Crohn's disease, ileocolonic (K50.90)",
        },
    )
    client.post("/api/cases/PA-1042/actions", json={"field": "patient_information.patient_name", "action": "accept"})
    case = client.get("/api/cases/PA-1042").json()
    assert case["clinical_information"]["diagnosis"] == "Crohn's disease, ileocolonic (K50.90)"

    saved = client.post("/api/cases/PA-1042/eval-case").json()
    assert saved["evaluations"] == 1
    parsed = yaml.safe_load(saved["yaml"])
    evaluation = parsed[saved["name"]]["evaluations"][0]
    assert evaluation["ground_truth"] == "Crohn's disease, ileocolonic (K50.90)"


def test_deny_routes_to_medical_director(client):
    body = client.post("/api/cases/PA-1042/decision", json={"decision": "deny", "note": "TB screen missing"}).json()
    assert body["status"] == "md_review"
    case = client.get("/api/cases/PA-1042").json()
    assert case["reviewer_actions"][-1]["field"] == "determination"
    assert case["reviewer_actions"][-1]["action"] == "reject"
    assert client.post("/api/cases/PA-1037/decision", json={"decision": "approve"}).status_code == 409


def test_submitted_case_runs_to_a_recommendation(client, monkeypatch):
    monkeypatch.setenv("AUTOAUTH_DEMO_STAGE_SECONDS", "0")
    created = client.post(
        "/api/cases",
        json={"patient_name": "Test Person", "member_id": "X1", "drug": "Humira 40mg", "urgency": "expedited"},
    )
    assert created.status_code == 201
    case_id = created.json()["case_id"]
    case = client.get(f"/api/cases/{case_id}").json()
    assert case["status"] == "ready"
    assert case["recommendation"]["decision"] == "Approved"

    with client.stream("GET", f"/api/cases/{case_id}/events") as events:
        text = "".join(events.iter_text())
    assert "event: progress" in text and "event: done" in text


def test_chat_answers_only_from_case(client):
    reply = client.post("/api/cases/PA-1042/chat", json={"message": "Why is C3 only partial?"}).json()["reply"]
    assert "Partially Met" in reply["text"]
    assert reply["citations"]
    fallback = client.post("/api/cases/PA-1042/chat", json={"message": "What's the weather?"}).json()["reply"]
    assert fallback["citations"] == []
    assert "only answer" in fallback["text"]


def test_quality_reads_existing_eval_yaml(client):
    body = client.get("/api/quality").json()
    families = {f["family"] for f in body["families"]}
    assert {"ocr-ner", "autodetermination-decision"} <= families
    assert body["illustrative_scores"]["note"].startswith("Illustrative")


def test_reset_restores_seed(client):
    client.post("/api/cases/PA-1042/decision", json={"decision": "approve"})
    client.post("/api/demo/reset")
    assert client.get("/api/cases/PA-1042").json()["status"] == "ready"


def test_api_does_not_load_azure_sdks():
    assert not [m for m in sys.modules if m.split(".")[0] in ("azure", "openai", "streamlit")]
