"""Indexed-documents API: simulated policy index built from the repo PDFs."""

import pytest
from fastapi.testclient import TestClient

from app.backend.api.app import app
from app.backend.api.demo_data import store
from app.backend.api.indexes import split_page

pytest.importorskip("pymupdf")


@pytest.fixture()
def client():
    store.reset()
    with TestClient(app) as c:
        yield c
    store.reset()


def test_split_page_overlaps_and_covers_text():
    text = " ".join(f"word{i}" for i in range(2000))
    spans = split_page(text, 3000, 500)
    assert spans[0][0] == 0 and spans[-1][1] == len(text)
    for (_, prev_end), (start, end) in zip(spans, spans[1:]):
        assert start < prev_end, "consecutive chunks share text"
        assert end - start <= 3000
    assert split_page("   ", 3000, 500) == []


def test_catalog_explains_prior_runtime_and_persistence(client):
    body = client.get("/api/indexes").json()
    docs = {d["name"]: d for d in body["prior"]["documents"]}
    assert sorted(docs) == ["001.pdf", "002.pdf", "003.pdf", "004.pdf", "005.pdf"]
    assert body["prior"]["expected_chunks"] == sum(d["chunks"] for d in docs.values()) > 0
    assert docs["001.pdf"]["title"].startswith("Inflammatory Conditions")
    assert docs["001.pdf"]["payer"] == "Cigna"
    assert docs["003.pdf"]["effective"] == "2018-09-01"
    assert docs["004.pdf"]["title"] == "Dupixent (dupilumab)"
    assert all("\ufffd" not in d["title"] for d in docs.values())
    assert {row["tier"] for row in body["persistence"]} == {"prior", "runtime", "persists"}
    assert body["live"]["status"] in {"healthy", "degraded"}

    cases = {c["case_id"]: c for c in body["runtime"]["cases"]}
    proto = cases["CASE-001A"]
    assert proto["policy"] == "001.pdf"
    assert proto["query"]
    assert all(d["raw_blob"].startswith(proto["blob_prefix"]) for d in proto["documents"])


def test_policy_detail_lists_overlapping_chunks(client):
    body = client.get("/api/indexes/policies/002.pdf").json()
    chunks = body["chunk_list"]
    assert len(chunks) == body["chunks"] > 0
    assert chunks[0]["overlap_chars"] == 0
    assert any(c["overlap_chars"] > 0 for c in chunks)
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)


def test_policy_file_and_unknown_names(client):
    resp = client.get("/api/indexes/policies/001.pdf/file")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert client.get("/api/indexes/policies/999.pdf").status_code == 404
    assert client.get("/api/indexes/policies/..%2Fdemo_data.py/file").status_code == 404


def test_search_ranks_matching_policy_first(client):
    body = client.get("/api/indexes/search", params={"q": "adalimumab Crohn's disease", "top": 3}).json()
    assert body["mode"].startswith("keyword")
    assert body["results"][0]["policy"] == "001.pdf"
    assert body["results"][0]["score"] == 1.0
    assert client.get("/api/indexes/search", params={"q": ""}).status_code == 422
