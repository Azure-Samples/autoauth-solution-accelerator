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


def test_prototype_cases_load_from_case_pdfs(client):
    cases = {c["case_id"]: c for c in client.get("/api/cases").json()["cases"]}
    proto = {k: v for k, v in cases.items() if v["prototype"]}
    assert len(proto) == 10
    assert cases["CASE-001A"]["recommendation"]["decision"] == "Rejected"
    assert cases["CASE-001A"]["recommendation"]["confidence"] is None

    detail = client.get("/api/cases/CASE-001A").json()
    assert detail["patient_information"]["patient_name"] == "Sarah Sample"
    assert any("label conflict" in w for w in detail["determination"]["warnings"])
    page_text = [line for doc in detail["documents"].values() for page in doc for line in page]
    for cites in detail["field_citations"].values():
        assert all(c["quote"] in page_text for c in cites)


def test_parity_scores_against_md_ground_truth(client):
    body = client.get("/api/parity").json()
    assert len(body["cases"]) == 10
    assert set(body["label_conflicts"]) == {"001_a", "001_b", "002_b"}
    assert {"legacy", "agents"} <= set(body["runners"])
    assert all(r["ui_case_id"] for r in body["cases"])


def test_reset_restores_seed(client):
    client.post("/api/cases/PA-1042/decision", json={"decision": "approve"})
    client.post("/api/demo/reset")
    assert client.get("/api/cases/PA-1042").json()["status"] == "ready"


def _pdf(lines):
    import pymupdf

    doc = pymupdf.open()
    for page_lines in lines:
        page = doc.new_page()
        page.insert_textbox(page.rect + (36, 36, -36, -36), "\n".join(page_lines), fontsize=6)
    data = doc.tobytes()
    doc.close()
    return data


def _upload(client, files, **form):
    parts = [("files", (name, data, "application/pdf")) for name, data in files]
    created = client.post("/api/cases/upload", files=parts, data=form)
    assert created.status_code == 201, created.text
    return client.get(f"/api/cases/{created.json()['case_id']}").json()


@pytest.fixture()
def sample(client):
    samples = client.get("/api/samples").json()["samples"]
    assert len(samples) == 10
    s = next(s for s in samples if s["key"] == "003_a")
    s["blobs"] = {f["name"]: client.get(f"/api/samples/003_a/files/{f['name']}").content for f in s["files"]}
    return s


def test_uploaded_scenario_packet_finishes_with_md_ground_truth(client, sample, monkeypatch):
    monkeypatch.setenv("AUTOAUTH_DEMO_STAGE_SECONDS", "0")
    case = _upload(client, list(sample["blobs"].items()), urgency="expedited")
    assert case["status"] == "ready" and case["urgency"] == "expedited"
    assert case["runner"] == "ground_truth"
    assert case["patient_name"] == sample["patient_name"]
    assert case["prototype"]["case_key"] == "003_a"
    assert {f["matched_by"] for f in case["upload"]["files"]} == {"sha256"}
    expected = {"Approved": "Approved", "Denied": "Rejected"}.get(sample["ground_truth"], sample["ground_truth"])
    assert case["determination"]["decision"] == expected
    assert not any(w.startswith("partial upload") for w in case["determination"]["warnings"])
    assert len(client.get("/api/parity").json()["cases"]) == 10


def test_rescanned_partial_upload_matches_by_text(client, sample, monkeypatch):
    monkeypatch.setenv("AUTOAUTH_DEMO_STAGE_SECONDS", "0")
    from app.backend.api.real_cases import extract_pages

    name, data = next(iter(sample["blobs"].items()))
    case = _upload(client, [("scan_0001.pdf", _pdf(extract_pages(data)))])
    assert case["upload"]["files"][0]["matched_by"] == "text"
    assert case["prototype"]["case_key"] == "003_a"
    if len(sample["files"]) > 1:
        assert case["determination"]["warnings"][0].startswith("partial upload")


def test_unknown_upload_needs_more_information(client, monkeypatch):
    monkeypatch.setenv("AUTOAUTH_DEMO_STAGE_SECONDS", "0")
    case = _upload(client, [("lunch-menu.pdf", _pdf([["Soup of the day", "Grilled cheese sandwich"]]))])
    assert case["upload"]["case_key"] is None
    assert case["determination"]["decision"] == "Needs More Information"
    assert case["documents"]["lunch-menu.pdf"][0][0] == "Soup of the day"
    bad = client.post("/api/cases/upload", files=[("files", ("x.pdf", b"not a pdf", "application/pdf"))])
    assert bad.status_code == 400


def test_sample_download_rejects_foreign_names(client):
    samples = {s["key"]: s for s in client.get("/api/samples").json()["samples"]}
    foreign = {f["name"] for f in samples["001_a"]["files"]} - {f["name"] for f in samples["003_a"]["files"]}
    assert client.get(f"/api/samples/003_a/files/{foreign.pop()}").status_code == 404
    assert client.get("/api/samples/003_a/files/..%2F..%2Fground_truth.json").status_code == 404
    assert client.get("/api/samples/999_z/files/a.pdf").status_code == 404


def test_api_does_not_load_azure_sdks():
    assert not [m for m in sys.modules if m.split(".")[0] in ("azure", "openai", "streamlit")]
