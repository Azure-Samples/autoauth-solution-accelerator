"""Index catalog for the reviewer UI.

Explains what the policy search index holds and when each artifact is written:

* **Prior** (deploy time): policy PDFs are OCR'd, split, embedded and pushed to
  ``ai-policies-index`` by ``src/pipeline/policyIndexer`` (settings.yaml).
* **Run time**: each case's attachments are uploaded and read, then used to
  *query* the policy index. Case documents are never added to the index.
* **Persists**: which artifacts outlive a run, and where.

Chunks are previewed by splitting the local PDF text layer the way the
skillset's SplitSkill does (per page, 3000 characters, 500 overlap). The Azure
OCR text can differ slightly. No Azure SDK is imported here.
"""

from __future__ import annotations

import functools
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from . import real_cases
from .demo_data import store, utcnow

router = APIRouter(prefix="/api/indexes", tags=["reviewer-ui"])

REPO_ROOT = Path(__file__).resolve().parents[3]
INDEXER_SETTINGS = REPO_ROOT / "src" / "pipeline" / "policyIndexer" / "settings.yaml"
RAG_SETTINGS = REPO_ROOT / "src" / "pipeline" / "agenticRag" / "settings.yaml"
PROCESSING_SETTINGS = REPO_ROOT / "src" / "pipeline" / "paprocessing" / "settings.yaml"
EMBEDDING_DIMENSIONS_FALLBACK = 3072
PREVIEW_CHARS = 280

# Read-only probe of the deployed search service (nonprod). The offline API
# cannot reach Azure, so this is a dated snapshot rather than a live call.
LIVE_SNAPSHOT: Dict[str, Any] = {
    "as_of": "2026-11-11",
    "environment": "nonprod (AutoAuth subscription)",
    "service": "searchautoauthmmzwfy2",
    "status": "degraded",
    "summary": (
        "The deployed index holds 5 whole-PDF entries with no chunk text and no vectors, "
        "so hybrid retrieval has nothing to match. Re-run the policy indexer job to rebuild it."
    ),
    "findings": [
        "ai-policies-index: 5 documents, vector index size 0; only chunk_id is populated.",
        "indexer-1770654880147 (no skillset) indexed 5 PDFs on 2026-02-09 without OCR, chunking or embeddings.",
        "indexer-testestestset uses ai-policies-skillset; last run 2026-02-17 ended in transientFailure (0 items).",
        "The configured indexer ai-policies-indexer does not exist on the service.",
    ],
    "fix": "Re-run the policy indexer deploy job (pe-be-autoauth-mmzwfy2-job), then confirm the chunk count matches the expected count below.",
}


def _yaml(path: Path) -> Dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _policy_dir() -> Path:
    return real_cases.CASES_ROOT / "policies"


def _policy_paths() -> Dict[str, Path]:
    folder = _policy_dir()
    if not folder.is_dir():
        return {}
    return {p.name: p for p in sorted(folder.glob("*.pdf"))}


def split_page(text: str, size: int, overlap: int) -> List[Tuple[int, int]]:
    """Approximate SplitSkill ``pages`` mode for one page; returns (start, end) offsets."""
    if not text.strip():
        return []
    if len(text) <= size:
        return [(0, len(text))]
    spans, start, step = [], 0, max(1, size - overlap)
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            cut = text.rfind(" ", start + step, end)
            end = cut if cut > start else end
        spans.append((start, end))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return spans


def _split_settings() -> Dict[str, int]:
    split = (_yaml(INDEXER_SETTINGS).get("skills") or {}).get("split_skill") or {}
    return {
        "size": int(split.get("maximum_page_length", 3000)),
        "overlap": int(split.get("page_overlap_length", 500)),
    }


@functools.lru_cache(maxsize=16)
def _chunks(path: str, mtime: float, size: int, overlap: int) -> tuple:
    out = []
    for page_no, lines in enumerate(real_cases.pdf_pages(Path(path)), start=1):
        text = " ".join(ln for ln in lines if ln != real_cases.SCANNED)
        prev_end = None
        for i, (start, end) in enumerate(split_page(text, size, overlap)):
            shared = max(0, prev_end - start) if prev_end is not None else 0
            out.append((page_no, i, text[start:end], shared))
            prev_end = end
    return tuple(out)


def policy_chunks(path: Path) -> List[Dict[str, Any]]:
    s = _split_settings()
    return [
        {
            "chunk_id": f"{path.stem}_p{page}_c{i}",
            "page_number": page,
            "chars": len(text),
            "overlap_chars": shared,
            "text": text,
        }
        for page, i, text, shared in _chunks(str(path), path.stat().st_mtime, s["size"], s["overlap"])
    ]


_STOP = frozenset(
    "the and for with that this from are was were has have had not but all any can may must will shall "
    "who whom which when what where how its into than then such per via use used also other more most "
    "patient patients policy request".split()
)


def _terms(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOP]


def search_chunks(query: str, top: int) -> List[Dict[str, Any]]:
    """Keyword (TF-IDF) ranking over the simulated chunks.

    Stands in for the keyword half of Azure's hybrid query; vectors and the
    semantic ranker are not simulated.
    """
    q = list(dict.fromkeys(_terms(query)))
    if not q:
        return []
    rows = [(name, c) for name, path in _policy_paths().items() for c in policy_chunks(path)]
    bags = [Counter(_terms(c["text"])) for _, c in rows]
    df = {t: sum(1 for b in bags if t in b) for t in q}
    n = len(rows)
    scored = []
    for (name, c), bag in zip(rows, bags):
        hits = [t for t in q if bag.get(t)]
        if not hits:
            continue
        length = math.sqrt(sum(bag.values()) or 1)
        score = sum((1 + math.log(bag[t])) * math.log(1 + n / df[t]) for t in hits) / length
        scored.append((score, name, c, hits))
    scored.sort(key=lambda r: r[0], reverse=True)
    best = scored[0][0] if scored else 1.0
    out = []
    for score, name, c, hits in scored[:top]:
        low = c["text"].lower()
        at = min((low.find(t) for t in hits if low.find(t) >= 0), default=0)
        start = max(0, at - 90)
        out.append(
            {
                "policy": name,
                "chunk_id": c["chunk_id"],
                "page_number": c["page_number"],
                "score": round(score / best, 3),
                "matched": hits,
                "snippet": ("…" if start else "") + c["text"][start : start + PREVIEW_CHARS].strip() + "…",
            }
        )
    return out


_DATE_FORMATS = ("%m/%d/%Y", "%m/%d/%y", "%m.%d.%y", "%m.%d.%Y", "%m-%d-%Y")


def _policy_title(first: List[str], fallback: str) -> str:
    """Pull the policy name out of the payer header (Cigna, Centene, UHC layouts)."""
    for i, line in enumerate(first):
        if line.strip().upper() == "POLICY:" and i + 1 < len(first):
            return " ".join(first[i + 1].replace("\u2013", "-").split())
        if line.startswith("Clinical Policy:"):
            return line.split(":", 1)[1].strip()
        if line.strip() in ("Medication", "Medications") and i + 1 < len(first):
            return first[i + 1].replace("\u00ae", "").strip()
    skip = ("page ", "\u00a9", "©")
    return next((ln for ln in first if len(ln) > 12 and not ln.lower().startswith(skip)), fallback)


def _effective_date(first: List[str]) -> Optional[datetime]:
    for i, line in enumerate(first):
        if "effective date" not in line.lower():
            continue
        for cand in (line.split(":", 1)[-1], first[i + 1] if i + 1 < len(first) else ""):
            token = cand.strip().split(" ")[0]
            for fmt in _DATE_FORMATS:
                try:
                    return datetime.strptime(token, fmt)
                except ValueError:
                    continue
    return None


def _payer(first: List[str]) -> Optional[str]:
    text = " ".join(first[:12])
    for payer in ("Cigna", "UnitedHealthcare", "Aetna", "Humana", "Anthem"):
        if payer.lower() in text.lower():
            return payer
    return "Centene (Envolve)" if "ERX." in text else None


def _policy_summary(name: str, path: Path) -> Dict[str, Any]:
    pages = real_cases.pdf_pages(path)
    first = pages[0] if pages else []
    title = _policy_title(first, name)
    effective = real_cases._policy_date(pages[: real_cases.POLICY_PAGES]) or _effective_date(first)
    chunks = policy_chunks(path)
    linked = sorted(k for k, c in real_cases.scenarios().items() if c.policy is not None and c.policy.name == name)
    return {
        "name": name,
        "title": title,
        "payer": _payer(first),
        "size": path.stat().st_size,
        "pages": len(pages),
        "chunks": len(chunks),
        "chars": sum(c["chars"] for c in chunks),
        "effective": effective.date().isoformat() if effective else None,
        "scenarios": linked,
        "blob_path": f"{_container()}/{_prefix()}/{name}",
    }


def _container() -> str:
    return (_yaml(INDEXER_SETTINGS).get("azure_search_indexer_settings") or {}).get(
        "azure_blob_storage_container_name", "pre-auth-policies"
    )


def _prefix() -> str:
    return (_yaml(INDEXER_SETTINGS).get("azure_search_indexer_settings") or {}).get("blob_prefix", "policies_ocr")


def index_definition() -> Dict[str, Any]:
    cfg = _yaml(INDEXER_SETTINGS)
    rag = _yaml(RAG_SETTINGS).get("retrieval") or {}
    settings = cfg.get("azure_search_indexer_settings") or {}
    skills = cfg.get("skills") or {}
    hnsw = ((cfg.get("vector_search") or {}).get("algorithms") or [{}])[0]
    params = hnsw.get("parameters") or {}
    split = _split_settings()
    dims = (skills.get("embedding_skill") or {}).get("dimensions", EMBEDDING_DIMENSIONS_FALLBACK)
    return {
        "name": (cfg.get("azure_search") or {}).get("index_name", "ai-policies-index"),
        "indexer": settings.get("indexer_name"),
        "skillset": settings.get("skillset_name"),
        "data_source": settings.get("data_source_name"),
        "container": _container(),
        "prefix": _prefix(),
        "semantic_config": rag.get("semantic_configuration_name", "my-semantic-config"),
        "fields": [
            {"name": "chunk_id", "type": "String", "role": "key", "note": "One row per chunk (keyword analyzer)."},
            {"name": "parent_id", "type": "String", "role": "filter", "note": "Links chunks back to their source PDF."},
            {"name": "title", "type": "String", "role": "searchable", "note": "Blob file name."},
            {"name": "parent_path", "type": "String", "role": "retrievable", "note": "Blob URL used to open the full policy."},
            {"name": "chunk", "type": "String", "role": "searchable", "note": "OCR text of the chunk; semantic ranker content field."},
            {"name": "vector", "type": f"Collection(Single) x{dims}", "role": "vector", "note": "Azure OpenAI embedding of the chunk."},
            {"name": "page_number", "type": "Int32", "role": "filter", "note": "Source page in the PDF."},
        ],
        "vector": {
            "algorithm": hnsw.get("name", "myHnsw"),
            "m": params.get("m"),
            "ef_construction": params.get("ef_construction"),
            "ef_search": params.get("ef_search"),
            "vectorizer": "myOpenAI",
            "dimensions": dims,
        },
        "pipeline": [
            {"step": "Crack", "detail": "Blob indexer renders one normalized image per PDF page."},
            {"step": "OCR", "detail": "OcrSkill reads text from every page image."},
            {"step": "Split", "detail": f"SplitSkill cuts each page into chunks of {split['size']} characters with {split['overlap']} overlap."},
            {"step": "Embed", "detail": f"AzureOpenAIEmbeddingSkill writes a {dims}-dimension vector per chunk."},
            {"step": "Project", "detail": "Index projections write one row per chunk; parent documents are skipped."},
        ],
        "chunking": split,
        "retrieval": {
            "mode": "Hybrid (keyword + vector) with semantic ranking",
            "top": rag.get("top", 5),
            "k_nearest_neighbors": rag.get("k_nearest_neighbors", 5),
            "vector_weight": rag.get("weight", 0.5),
        },
        "deploy_job": "policyIndexer (src/pipeline/policyIndexer/indexerSetup.py), run as a Container Apps job after azd provision",
    }


def _runtime_paths() -> Dict[str, str]:
    paths = _yaml(PROCESSING_SETTINGS).get("remote_blob_paths") or {}
    return {
        "container": paths.get("container_name", "pre-auth-policies"),
        "base": paths.get("remote_dir_base", "pa_proccesing_runs"),
        "raw": paths.get("raw_uploaded_files", "raw_attachments"),
        "images": paths.get("processed_images", "processed_docs_images"),
    }


def _case_policy(record: Any) -> Optional[str]:
    key = None
    if record.template == "prototype" and record.prototype:
        key = record.prototype.get("case_key")
    elif record.template == "upload" and record.upload:
        key = record.upload.get("case_key")
    case = real_cases.scenarios().get(key) if key else None
    return case.policy.name if case is not None and case.policy is not None else None


def _flat_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flat_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flat_text(v) for v in value)
    return "" if value is None else str(value)


def suggested_query(record: Any) -> str:
    """The query the agent ran, or one built from the request and diagnosis."""
    if record.state.expanded_query:
        return record.state.expanded_query
    clinical = record.state.clinical_information or {}
    parts = [record.request, _flat_text(clinical.get("diagnosis")), _flat_text(clinical.get("treatment_request"))]
    text = " ".join(p for p in parts if p and p.strip())
    return " ".join(text.split())[:240]


def runtime_cases() -> List[Dict[str, Any]]:
    paths = _runtime_paths()
    out = []
    for record in store.all(utcnow()):
        pages = dict(record.state.documents.pages)
        for name, doc in record.documents.items():
            if not name.startswith("policy-"):
                pages.setdefault(name, len(doc))
        names = list(pages) or list(record.state.documents.files)
        base = f"{paths['container']}/{paths['base']}/{record.state.case_id}"
        out.append(
            {
                "case_id": record.state.case_id,
                "patient_name": record.patient_name,
                "source": record.template,
                "status": record.status,
                "received_at": record.received_at.isoformat(),
                "request": record.request,
                "policy": _case_policy(record),
                "cited_policy": record.state.policies[0].blob_url if record.state.policies else None,
                "query": suggested_query(record),
                "blob_prefix": base,
                "documents": [
                    {"name": n, "pages": pages.get(n), "raw_blob": f"{base}/{paths['raw']}/{n}"} for n in names
                ],
            }
        )
    return out


def runtime_steps() -> List[Dict[str, str]]:
    p = _runtime_paths()
    return [
        {"step": "Upload", "detail": f"Case PDFs are copied to {p['container']}/{p['base']}/<case>/{p['raw']}.", "writes": "Blob"},
        {"step": "Render + read", "detail": f"Each page becomes an image under .../{p['images']}; the extractor reads them in a temp folder.", "writes": "Blob, temp"},
        {"step": "Query", "detail": "Extracted clinical facts are expanded into a search query and run against the policy index (hybrid + semantic).", "writes": "Nothing (read only)"},
        {"step": "Read policy", "detail": "The top policy blob is read in full with Document Intelligence (prebuilt-layout) and summarized.", "writes": "Nothing (read only)"},
        {"step": "Decide + store", "detail": "The determination, extracted fields and citations are saved for the case.", "writes": "Cosmos DB"},
    ]


def persistence() -> List[Dict[str, str]]:
    p = _runtime_paths()
    return [
        {"artifact": "Policy PDFs", "tier": "prior", "where": f"Blob {_container()}/{_prefix()}", "lifetime": "Until replaced", "offline": "Repo files (utils/data/cases/policies)"},
        {"artifact": "Policy chunks + vectors", "tier": "prior", "where": "AI Search ai-policies-index", "lifetime": "Until the indexer re-runs", "offline": "Simulated from the PDF text layer on request"},
        {"artifact": "Case attachments", "tier": "runtime", "where": f"Blob {p['container']}/{p['base']}/<case>/{p['raw']}", "lifetime": "Kept (no cleanup policy)", "offline": "In memory; lost on restart or demo reset"},
        {"artifact": "Page images", "tier": "runtime", "where": f"Blob .../<case>/{p['images']}", "lifetime": "Kept (no cleanup policy)", "offline": "Not created"},
        {"artifact": "Temp working files", "tier": "runtime", "where": "Container local disk", "lifetime": "Deleted at the end of the run", "offline": "Not created"},
        {"artifact": "Search queries + scores", "tier": "runtime", "where": "Agent trace", "lifetime": "Kept with the case trace", "offline": "In memory"},
        {"artifact": "Determination + citations", "tier": "persists", "where": "Cosmos DB (Mongo vCore), keyed by case", "lifetime": "Kept", "offline": "In memory; lost on restart or demo reset"},
        {"artifact": "Reviewer actions", "tier": "persists", "where": "Case state (Cosmos DB)", "lifetime": "Kept; feeds eval traces", "offline": "In memory"},
        {"artifact": "Eval cases + ground truth", "tier": "persists", "where": "Repo (evals/cases, ground_truth.json)", "lifetime": "Versioned in git", "offline": "Same files"},
    ]


@router.get("")
def catalog() -> Dict[str, Any]:
    definition = index_definition()
    policies = [_policy_summary(n, p) for n, p in _policy_paths().items()]
    return {
        "index": definition,
        "prior": {
            "documents": policies,
            "expected_chunks": sum(p["chunks"] for p in policies),
        },
        "runtime": {"steps": runtime_steps(), "cases": runtime_cases()},
        "persistence": persistence(),
        "live": LIVE_SNAPSHOT,
    }


@router.get("/search")
def search(q: str = Query(..., min_length=1, max_length=500), top: int = Query(5, ge=1, le=20)) -> Dict[str, Any]:
    return {
        "query": q,
        "terms": list(dict.fromkeys(_terms(q))),
        "mode": "keyword (simulated)",
        "note": "Ranks the simulated chunks by keyword overlap. Azure adds vector similarity and the semantic ranker.",
        "results": search_chunks(q, top),
    }


def _policy(name: str) -> Path:
    path = _policy_paths().get(name)
    if path is None:
        raise HTTPException(status_code=404, detail=f"No indexed policy {name!r}.")
    return path


@router.get("/policies/{name}")
def policy_detail(name: str) -> Dict[str, Any]:
    path = _policy(name)
    out = _policy_summary(name, path)
    out["chunk_list"] = policy_chunks(path)
    out["preview_chars"] = PREVIEW_CHARS
    return out


@router.get("/policies/{name}/file")
def policy_file(name: str) -> FileResponse:
    return FileResponse(
        _policy(name), media_type="application/pdf", filename=name, content_disposition_type="inline"
    )
