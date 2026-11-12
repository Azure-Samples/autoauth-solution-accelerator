# AutoAuth reviewer UI (React + Fluent UI v9)

This is the role-based UI from [the agentic 2026 design](../../../docs/architecture/agentic-2026.md#3-ui-wireframes). The clickable wireframe it was built from is [`docs/architecture/wireframes/agentic-2026.html`](../../../docs/architecture/wireframes/agentic-2026.html).

| Route | Page | What it does |
|---|---|---|
| `#/queue` | Review queue | Cases are sorted by SLA. You can filter by status, urgency, and data freshness, and each row has a freshness badge. |
| `#/case/:id` | Case workspace | Evidence and criteria are shown with citations. Each field can be accepted, edited, or rejected. You can re-verify stale inputs, ask grounded questions in chat, and approve, pend, or deny. **Save as eval case** turns reviewer corrections into YAML for `evals/cases/`. |
| `#/case/:id/trace` | Agent trace | Shows the span per agent step, with timing and status. |
| `#/provider` | Send a request | Pick a demo claim or upload a PDF. A pre-check runs before you submit. After submit, live agent progress streams over SSE. |
| `#/indexes/...` | Policy library | A guided walkthrough of what is indexed ahead of time, what is indexed at run time, and what persists. |
| `#/quality` | Quality | Shows override and freshness KPIs plus the existing eval families and suites. |
| `#/parity` | Prototype parity | Compares the 10 prototype cases (`utils/data/cases`) for each runner against the MD ground truth, and flags PDF label conflicts. Each row links to the case. |

The shell uses a friendly, modern look: a light top bar with pill tabs, soft rounded cards, tinted status chips, gradient primary buttons, and a step tracker on each case. Breadcrumbs appear only on case and trace pages. The theme is in `src/theme.ts` and `src/styles.css`. Alternative directions are compared in [`docs/architecture/wireframes/ui-themes.html`](../../../docs/architecture/wireframes/ui-themes.html).

## Run it locally (no Azure needed)

The UI talks to `/api/*`. The offline API (`app/backend/api`) serves fictional demo cases from memory.

```bash
# 1. API (from the repository root)
pip install fastapi uvicorn pyyaml pydantic
uvicorn app.backend.api.app:app --port 8000

# 2a. Dev server with hot reload (proxies /api to :8000)
cd app/frontend/web
npm install
npm run dev            # http://localhost:5173

# 2b. Or build once and let the API serve it
npm run build          # writes dist/; open http://localhost:8000
```

- `AUTOAUTH_API_URL` changes the dev proxy target. The default is `http://localhost:8000`.
- `AUTOAUTH_UI_ORIGINS` sets the CORS allow-list on the API. It's a comma-separated list.
- To mount the same endpoints on the main backend (`app/backend/main.py`), set `AUTOAUTH_REVIEWER_DEMO=1`.
- **Reset demo** in the header, or `POST /api/demo/reset`, restores the seed data.
- The queue also loads the 10 prototype cases from `utils/data/cases`, marked with a **Prototype** badge. Set `AUTOAUTH_PROTOTYPE_CASES=0` to hide them.
- The parity page reads recorded runs from `utils/data/cases/parity_runs/` (or `AUTOAUTH_PARITY_RUNS`). To record runs, deploy the infrastructure (`azd up`), then run `python -m src.evals.adapters.parity --run legacy agents`.

The demo store is in-memory. Its demo patients are fictional. The prototype cases are the sample files already in the repository. Wiring it to the agent runtime (`src/agents/`) and to persistent storage is the next step. See §6.1 of the design doc.
