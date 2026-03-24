"""
Developer Tools page — Indexer operations and diagnostics.

Only accessible when Developer Mode is toggled on from the Home page sidebar.
"""

import os
import time

import dotenv
import httpx
import streamlit as st

from src.utils.function_keys import get_indexer_function_headers

dotenv.load_dotenv(".env", override=True)

st.set_page_config(
    page_title="Developer Tools",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Gate: redirect if developer mode is off ──────────────────────────────
if not st.session_state.get("developer_mode", False):
    st.warning("Developer Mode is disabled. Enable it from the **Home** page sidebar.")
    st.stop()

# ── Config ───────────────────────────────────────────────────────────────
INDEXER_HOSTNAME = os.getenv("INDEXER_FUNCTION_APP_HOSTNAME", "")
INDEXER_BASE_URL = os.getenv("INDEXER_FUNCTION_BASE_URL") or (
    f"https://{INDEXER_HOSTNAME}" if INDEXER_HOSTNAME else "http://localhost:7071"
)
REQUEST_TIMEOUT = 300.0  # seconds


def _headers() -> dict[str, str]:
    return get_indexer_function_headers()


def _call_indexer(method: str, path: str, **kwargs) -> dict:
    """Make a synchronous request to the indexer function app."""
    url = f"{INDEXER_BASE_URL}/api/{path}"
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        resp = client.request(method, url, headers=_headers(), **kwargs)
        resp.raise_for_status()
        return resp.json()


# ── Page header ──────────────────────────────────────────────────────────
st.markdown("# 🔧 Developer Tools")
st.caption(f"Indexer endpoint: `{INDEXER_BASE_URL}`")

# ── Tabs ─────────────────────────────────────────────────────────────────
tab_ops, tab_status, tab_health = st.tabs(
    ["⚙️ Indexer Operations", "📊 Processing Status", "❤️ Health Check"]
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 1 — Indexer Operations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_ops:
    col1, col2 = st.columns(2)

    # ── Reindex All ──────────────────────────────────────────────────────
    with col1:
        st.subheader("🔄 Reindex All Policies")
        st.markdown(
            "Reprocess **every PDF** in the blob container. "
            "This will OCR, chunk, embed, and push all documents to the AI Search index."
        )
        prefix = st.text_input(
            "Blob prefix",
            value="policies_ocr/",
            help="Only blobs under this prefix will be reindexed.",
        )
        if st.button("🚀 Start Reindex All", type="primary", use_container_width=True):
            with st.spinner("Reindexing all policies… this may take several minutes."):
                start = time.time()
                try:
                    result = _call_indexer("POST", "reindex_all", json={"prefix": prefix})
                    elapsed = round(time.time() - start, 1)
                    status = result.get("status", "unknown")
                    if status in ("ok", "partial"):
                        total = result.get("total", 0)
                        succeeded = result.get("succeeded", 0)
                        failed = result.get("failed", 0)
                        if failed == 0:
                            st.success(
                                f"Reindex complete — **{succeeded}/{total}** documents processed in {elapsed}s."
                            )
                        else:
                            st.warning(
                                f"Reindex finished with issues — {succeeded}/{total} succeeded, "
                                f"**{failed} failed** ({elapsed}s)."
                            )
                        with st.expander("View detailed results", expanded=False):
                            st.json(result)
                    else:
                        st.error(f"Reindex returned status: {status}")
                        st.json(result)
                except httpx.HTTPStatusError as exc:
                    st.error(f"HTTP {exc.response.status_code}: {exc.response.text}")
                except httpx.RequestError as exc:
                    st.error(f"Could not reach the indexer: {exc}")

    # ── Setup Index ──────────────────────────────────────────────────────
    with col2:
        st.subheader("🏗️ Setup / Update Index Schema")
        st.markdown(
            "Create or update the AI Search index schema. "
            "This is **idempotent** — safe to call repeatedly."
        )
        if st.button("🏗️ Setup Index", use_container_width=True):
            with st.spinner("Setting up index schema…"):
                try:
                    result = _call_indexer("POST", "setup_index")
                    if result.get("status") == "ok":
                        st.success("Index schema is up to date.")
                        with st.expander("Resources created/updated"):
                            st.json(result.get("resources", {}))
                    else:
                        st.error("Setup returned an unexpected status.")
                        st.json(result)
                except httpx.HTTPStatusError as exc:
                    st.error(f"HTTP {exc.response.status_code}: {exc.response.text}")
                except httpx.RequestError as exc:
                    st.error(f"Could not reach the indexer: {exc}")

    st.divider()

    # ── Process Single Blob ──────────────────────────────────────────────
    st.subheader("📄 Process a Single Blob")
    st.markdown("Manually trigger processing for one specific PDF in blob storage.")
    blob_name = st.text_input(
        "Blob name",
        placeholder="policies_ocr/my-policy.pdf",
        help="Full path of the blob within the container.",
    )
    if st.button("▶️ Process Blob", disabled=not blob_name):
        with st.spinner(f"Processing `{blob_name}`…"):
            try:
                result = _call_indexer(
                    "POST", "process_blob_manual", json={"blob_name": blob_name}
                )
                if result.get("status") == "ok":
                    st.success(
                        f"Processed **{blob_name}** — "
                        f"{result.get('chunk_count', '?')} chunks, "
                        f"{result.get('duration_seconds', '?')}s"
                    )
                else:
                    st.error(f"Processing failed: {result.get('error', 'unknown error')}")
                with st.expander("Full response"):
                    st.json(result)
            except httpx.HTTPStatusError as exc:
                st.error(f"HTTP {exc.response.status_code}: {exc.response.text}")
            except httpx.RequestError as exc:
                st.error(f"Could not reach the indexer: {exc}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 2 — Processing Status
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_status:
    st.subheader("📊 Processing Status & History")

    col_filter, col_limit = st.columns([2, 1])
    with col_filter:
        status_filter = st.selectbox(
            "Filter",
            options=["recent", "failed"],
            help="Show recent sessions or only failures.",
        )
    with col_limit:
        limit = st.number_input("Max results", min_value=1, max_value=500, value=50)

    if st.button("🔍 Fetch Status", use_container_width=True):
        with st.spinner("Fetching processing status…"):
            try:
                result = _call_indexer(
                    "GET",
                    "processing_status",
                    params={"filter": status_filter, "limit": str(limit)},
                )
                # Summary metrics
                summary = result.get("summary")
                if summary:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Sessions", summary.get("total_sessions", 0))
                    m2.metric("Succeeded", summary.get("succeeded", 0))
                    m3.metric("Failed", summary.get("failed", 0))
                    m4.metric("In Progress", summary.get("in_progress", 0))

                # Session list
                sessions = result.get("recent_sessions") or result.get("sessions", [])
                if sessions:
                    for s in sessions:
                        status_icon = "✅" if s.get("success") else "❌"
                        label = f"{status_icon} {s.get('blob_name', 'unknown')} — {s.get('session_id', '')[:8]}"
                        with st.expander(label):
                            st.json(s)
                else:
                    st.info("No sessions found for the selected filter.")
            except httpx.HTTPStatusError as exc:
                st.error(f"HTTP {exc.response.status_code}: {exc.response.text}")
            except httpx.RequestError as exc:
                st.error(f"Could not reach the indexer: {exc}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 3 — Health Check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_health:
    st.subheader("❤️ Indexer Health Check")
    st.markdown("Validate connectivity to AI Search, Blob Storage, OpenAI, and Document Intelligence.")

    if st.button("🩺 Run Health Check", use_container_width=True):
        with st.spinner("Running health checks…"):
            try:
                result = _call_indexer("GET", "health")
                overall = result.get("status", "unknown")
                if overall == "healthy":
                    st.success("All systems healthy ✅")
                else:
                    st.warning(f"System status: **{overall}**")

                checks = result.get("checks", {})
                for service, status in checks.items():
                    if isinstance(status, dict):
                        # session tracker summary
                        with st.expander(f"📋 {service}"):
                            st.json(status)
                    elif status in ("ok", "configured"):
                        st.markdown(f"- ✅ **{service}**: {status}")
                    else:
                        st.markdown(f"- ❌ **{service}**: {status}")
            except httpx.HTTPStatusError as exc:
                st.error(f"HTTP {exc.response.status_code}: {exc.response.text}")
            except httpx.RequestError as exc:
                st.error(f"Could not reach the indexer: {exc}")
