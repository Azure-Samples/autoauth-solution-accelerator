// Typed client for the reviewer API in app/backend/api/cases.py.

export type Status = "ready" | "running" | "approved" | "pended" | "md_review";
export type FreshStatus = "fresh" | "aging" | "stale" | "unknown" | "pending";
export type Decision = "approve" | "pend" | "deny";
export type FieldAction = "accept" | "edit" | "reject";
export type ReverifyKind =
  | "provider_affiliation"
  | "member_eligibility"
  | "clinical_evidence"
  | "policy";

export interface Citation {
  source: string;
  chunk_id: string | null;
  page: number | null;
  quote: string;
  bbox: number[] | null;
}

export interface Recommendation {
  decision: string;
  label: string;
  /** null for prototype cases, whose label is MD ground truth rather than a model score. */
  confidence: number | null;
  criteria_met: number;
  criteria_total: number;
  model: string;
  warnings: string[];
}

export interface FreshnessSummary {
  overall: FreshStatus;
  counts: Partial<Record<FreshStatus, number>>;
  label: string;
}

export interface CaseSummary {
  case_id: string;
  trace_id: string;
  patient_name: string;
  member_id: string;
  request: string;
  urgency: "expedited" | "standard";
  line_of_business: string;
  provider_org: string;
  status: Status;
  owner: string | null;
  received_at: string;
  sla_hours: number;
  sla_left_hours: number;
  progress: { done: number; total: number; current: string | null };
  recommendation: Recommendation | null;
  freshness: FreshnessSummary;
  human_decision: { decision: Decision; reviewer: string; note?: string | null } | null;
  runner: string;
  prototype: Prototype | null;
}

/** Provenance for the real prototype cases in utils/data/cases (see app/backend/api/real_cases.py). */
export interface Prototype {
  case_key: string;
  folder: string;
  ground_truth: string;
  pdf_label: string | null;
  label_conflict: boolean;
  fact_sources: string[];
  policy: string | null;
  notes: string[];
}

export type ParityStatus = "not_run" | "ok" | "error";

export interface ParityResult {
  status: ParityStatus;
  decision: string | null;
  match: boolean | null;
  error?: string | null;
  seconds?: number | null;
  recorded_at?: string | null;
}

export interface ParityRow {
  case_id: string;
  number: string;
  variant: string;
  files: Record<string, string[]>;
  policy: string | null;
  ground_truth: string;
  ground_truth_note: string | null;
  pdf_label: string | null;
  label_conflict: boolean;
  notes: string[];
  results: Record<string, ParityResult>;
  ui_case_id: string;
}

export interface Parity {
  cases: ParityRow[];
  runners: string[];
  summary: Record<string, { run: number; scored: number; matched: number; rate: number | null }>;
  label_conflicts: string[];
  source: string;
  command: string;
}

export interface FreshnessEntry {
  kind: ReverifyKind;
  subject: string;
  as_of: string | null;
  age_days: number | null;
  max_age_days: number;
  status: FreshStatus;
  source: string;
  note: string | null;
  action: string | null;
}

export interface Assessment {
  criterion_id: string;
  status: string;
  evidence: string | null;
  policy_reference: string | null;
  notes: string | null;
  citations: Citation[];
  criterion_text: string | null;
  policy_citations: Citation[];
}

export interface PolicyHit {
  blob_url: string;
  chunk_id: string | null;
  reasoning: string;
  score: number | null;
  citations: Citation[];
  freshness: FreshnessEntry | null;
}

export interface ReviewerAction {
  field: string;
  action: FieldAction;
  original: string | null;
  corrected: string | null;
  reviewer: string;
  note: string | null;
  at?: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

export interface CaseDetail extends CaseSummary {
  workflow: { name: string; state: "done" | "current" | "todo" }[];
  documents: Record<string, string[][]>;
  patient_information: Record<string, unknown>;
  physician_information: Record<string, unknown>;
  clinical_information: Record<string, unknown>;
  field_citations: Record<string, Citation[]>;
  policies: PolicyHit[];
  assessments: Assessment[];
  determination: {
    decision: string;
    rationale: string;
    missing_information: { information_needed: string; reason: string }[];
    citations?: Citation[];
    model?: string;
  } | null;
  freshness_report: FreshnessEntry[];
  reviewer_actions: ReviewerAction[];
  chat: ChatTurn[];
}

export interface Span {
  name: string;
  depth: number;
  detail: string;
  seconds: number | null;
  signal: string | null;
  status: "ok" | "run" | "todo" | "wait";
}

export interface Trace {
  case_id: string;
  trace_id: string;
  runner: string;
  total_seconds: number | null;
  estimated_cost_usd: number | null;
  spans: Span[];
}

export interface Quality {
  suites: {
    suite: string;
    family: string;
    pipeline: string;
    evaluators: string[];
    cases: number;
    evaluations: number;
  }[];
  families: { family: string; suites: number; evaluations: number; evaluators: string[] }[];
  illustrative_scores: {
    note: string;
    rows: { family: string; baseline: number; candidate: number }[];
    online: Record<string, number>;
  };
  live: Record<string, unknown>;
  freshness_limits_days: Record<string, number>;
  sla_hours: Record<string, number>;
}

export interface SubmitIn {
  patient_name: string;
  member_id?: string;
  drug: string;
  urgency: "expedited" | "standard";
  prescriber?: string;
  specialty?: string;
  provider_org?: string;
  files: string[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  call<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export interface CaseFilters {
  status?: string;
  urgency?: string;
  freshness?: string;
  q?: string;
}

export const api = {
  listCases(f: CaseFilters = {}) {
    const qs = new URLSearchParams(
      Object.entries(f).filter(([, v]) => v) as [string, string][],
    ).toString();
    return call<{ cases: CaseSummary[]; generated_at: string }>(`/cases${qs ? `?${qs}` : ""}`);
  },
  getCase: (id: string) => call<CaseDetail>(`/cases/${id}`),
  submit: (body: SubmitIn) => post<CaseSummary>("/cases", body),
  assign: (id: string, owner: string) => post<CaseSummary>(`/cases/${id}/assign`, { owner }),
  fieldAction: (id: string, body: ReviewerAction) =>
    post<{ action: ReviewerAction; reviewer_actions: number }>(`/cases/${id}/actions`, body),
  reverify: (id: string, kind: ReverifyKind) =>
    post<{ freshness_report: FreshnessEntry[]; warnings: string[]; freshness: FreshnessSummary }>(
      `/cases/${id}/reverify/${kind}`,
    ),
  decide: (id: string, decision: Decision, reviewer: string, note?: string) =>
    post<CaseSummary>(`/cases/${id}/decision`, { decision, reviewer, note }),
  trace: (id: string) => call<Trace>(`/cases/${id}/trace`),
  evalCase: (id: string) =>
    post<{ name: string; evaluations: number; case: unknown; yaml: string }>(`/cases/${id}/eval-case`),
  chat: (id: string, message: string) =>
    post<{ reply: { text: string; citations: Citation[] }; chat: ChatTurn[] }>(`/cases/${id}/chat`, {
      message,
    }),
  quality: () => call<Quality>("/quality"),
  parity: () => call<Parity>("/parity"),
  reset: () => post<unknown>("/demo/reset"),
};

/** Follows a running case over SSE; returns an unsubscribe function. */
export function followCase(
  id: string,
  onProgress: (s: CaseSummary) => void,
  onDone: (status: Status) => void,
): () => void {
  const es = new EventSource(`/api/cases/${id}/events`);
  es.addEventListener("progress", (e) => onProgress(JSON.parse((e as MessageEvent).data)));
  es.addEventListener("done", (e) => {
    onDone(JSON.parse((e as MessageEvent).data).status);
    es.close();
  });
  es.onerror = () => es.close();
  return () => es.close();
}

export const REVERIFY_LABEL: Record<ReverifyKind, string> = {
  provider_affiliation: "Provider affiliation",
  member_eligibility: "Member eligibility",
  clinical_evidence: "Clinical evidence",
  policy: "Policy",
};

export const REVERIFY_ACTION: Record<ReverifyKind, string> = {
  provider_affiliation: "Re-verify provider (NPPES)",
  member_eligibility: "Check eligibility (270/271)",
  clinical_evidence: "Request updated notes",
  policy: "Re-check policy version",
};

export const pct = (v: number | null | undefined) => (v === null || v === undefined ? null : Math.round(v * 100));

export function slaText(left: number, total: number): string {
  const fmt = (h: number) => (h >= 48 ? `${Math.round(h / 24)}d` : `${Math.max(0, Math.round(h))}h`);
  return `${fmt(left)} / ${fmt(total)}`;
}
