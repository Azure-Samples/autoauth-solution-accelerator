import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Badge,
  Button,
  Input,
  Link,
  MessageBar,
  MessageBarBody,
  MessageBarTitle,
  Spinner,
  Tab,
  TabList,
  Text,
  Textarea,
  Tooltip,
} from "@fluentui/react-components";
import {
  ArrowLeftRegular,
  ArrowUploadRegular,
  CheckmarkRegular,
  DocumentBulletListRegular,
  PersonAddRegular,
  TimelineRegular,
  DismissRegular,
  EditRegular,
  SendRegular,
} from "@fluentui/react-icons";
import {
  api,
  followCase,
  REVERIFY_ACTION,
  REVERIFY_LABEL,
  slaText,
  type CaseDetail,
  type Citation,
  type Decision,
  type FieldAction,
  type FreshnessEntry,
} from "../api";
import {
  BladeHeader,
  CommandBar,
  DecisionBadge,
  ErrorBar,
  Essentials,
  EvalCaseDialog,
  FreshBadge,
  freshnessShort,
  freshnessTitle,
  PrototypeBadge,
  StatusBadge,
} from "../components/common";
import { matchText } from "../components/UploadClaim";
import { go } from "../App";

export const REVIEWER = "J. Reviewer";
const SECTIONS = ["patient_information", "physician_information", "clinical_information"] as const;
const SUGGESTIONS = [
  "Why is C3 only partially met?",
  "Is the provider data stale?",
  "What is missing to approve?",
];

type Active = { source: string; quote: string } | null;

const pretty = (k: string) => k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
const show = (v: unknown): string =>
  v === null || v === undefined
    ? "—"
    : typeof v === "object"
      ? Object.values(v as Record<string, unknown>).map(show).join(", ")
      : String(v);
const matches = (line: string, quote: string) =>
  line.trim() !== "" && (line.includes(quote) || quote.includes(line.trim()));

function CiteLink({ c, onOpen }: { c: Citation; onOpen: (c: Citation) => void }) {
  return (
    <Tooltip content={`“${c.quote}”`} relationship="description">
      <button className="cite" onClick={() => onOpen(c)} data-cite={c.source}>
        [{c.source}
        {c.page ? ` p${c.page}` : ""}]
      </button>
    </Tooltip>
  );
}

function Cites({ list, onOpen }: { list: Citation[] | undefined; onOpen: (c: Citation) => void }) {
  if (!list?.length) return null;
  return (
    <span className="row" style={{ gap: 4, display: "inline-flex" }}>
      {list.map((c, i) => (
        <CiteLink key={i} c={c} onOpen={onOpen} />
      ))}
    </span>
  );
}

/* ------------------------------------------------------------------ header */

function Stepper({ steps }: { steps: CaseDetail["workflow"] }) {
  return (
    <div className="stepper" aria-label="Workflow">
      {steps.map((s, i) => (
        <div key={s.name} className={`step ${s.state}`} data-state={s.state}>
          <span className="step-dot" aria-hidden>
            {s.state === "done" ? "✓" : i + 1}
          </span>
          {s.name}
        </div>
      ))}
    </div>
  );
}

function FreshnessStrip(props: {
  entries: FreshnessEntry[];
  busy: string | null;
  onReverify: (e: FreshnessEntry) => void;
}) {
  if (!props.entries.length) return null;
  return (
    <div className="fresh-strip" aria-label="Data freshness">
      {props.entries.map((f) => (
        <div className="fresh-item" key={`${f.kind}:${f.subject}`} data-kind={f.kind}>
          <b>{REVERIFY_LABEL[f.kind]}</b>
          <FreshBadge status={f.status} title={freshnessTitle(f)}>
            {f.status} · {freshnessShort(f)}
          </FreshBadge>
          <span className="muted">{f.subject}</span>
          {f.status !== "fresh" && f.status !== "pending" ? (
            <Button
              size="small"
              appearance="subtle"
              disabled={props.busy !== null}
              onClick={() => props.onReverify(f)}
              data-reverify={f.kind}
            >
              {props.busy === f.kind ? <Spinner size="extra-tiny" /> : (f.action ?? REVERIFY_ACTION[f.kind])}
            </Button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------- evidence */

function EvidencePane(props: {
  c: CaseDetail;
  active: Active;
  doc: string;
  setDoc: (d: string) => void;
  onOpen: (c: Citation) => void;
  onField: (field: string, action: FieldAction, original: string, corrected?: string) => Promise<void>;
}) {
  const { c, active } = props;
  const docs = Object.keys(c.documents);
  const markRef = useRef<HTMLElement | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const cited = useMemo(() => {
    const all = [
      ...Object.values(c.field_citations).flat(),
      ...c.assessments.flatMap((a) => [...a.citations, ...a.policy_citations]),
    ];
    return all.filter((x) => x.source === props.doc).map((x) => x.quote);
  }, [c, props.doc]);

  useEffect(() => {
    markRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [active, props.doc]);

  const lastAction = (field: string) => [...c.reviewer_actions].reverse().find((a) => a.field === field);
  const pages = c.documents[props.doc] ?? [];

  return (
    <section className="card stack" aria-label="Evidence">
      <p className="section-title">Evidence</p>
      {docs.length ? (
        <>
          <div className="tab-scroll">
          <TabList size="small" selectedValue={props.doc} onTabSelect={(_, d) => props.setDoc(String(d.value))}>
            {docs.map((d) => (
              <Tab key={d} value={d}>
                {d}
              </Tab>
            ))}
          </TabList>
          </div>
          <div className="doc" data-doc={props.doc}>
            {pages.map((lines, p) => (
              <div key={p}>
                {p > 0 ? <div className="page-break">page {p + 1}</div> : null}
                {lines.map((line, i) => {
                  const isActive = active?.source === props.doc && matches(line, active.quote);
                  const isCited = cited.some((q) => matches(line, q));
                  if (!isActive && !isCited) return <div key={i}>{line || "\u00a0"}</div>;
                  return (
                    <div key={i}>
                      <mark className={isActive ? "active" : undefined} ref={isActive ? markRef : undefined}>
                        {line}
                      </mark>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </>
      ) : (
        <Text className="muted">Documents appear once intake finishes.</Text>
      )}

      <p className="section-title" style={{ marginTop: 8 }}>
        Extracted facts
      </p>
      {SECTIONS.map((section) =>
        Object.entries(c[section] ?? {}).map(([key, value]) => {
          const field = `${section}.${key}`;
          const original = show(value);
          const last = lastAction(field);
          const state = last?.action === "edit" ? "edited" : last?.action === "reject" ? "rejected" : "";
          return (
            <div className={`fact ${state}`} key={field} data-field={field}>
              <span className="key">{pretty(key)}</span>
              {editing === field ? (
                <Input
                  size="small"
                  value={draft}
                  aria-label={`Correct ${pretty(key)}`}
                  onChange={(_, d) => setDraft(d.value)}
                  onKeyDown={async (e) => {
                    if (e.key === "Enter") {
                      await props.onField(field, "edit", original, draft);
                      setEditing(null);
                    }
                    if (e.key === "Escape") setEditing(null);
                  }}
                />
              ) : (
                <span className="val">
                  {original} <Cites list={c.field_citations[field]} onOpen={props.onOpen} />
                  {last?.action === "accept" ? (
                    <Badge size="small" appearance="tint" color="success" style={{ marginLeft: 4 }}>
                      accepted
                    </Badge>
                  ) : null}
                </span>
              )}
              <span className="row" style={{ gap: 0 }}>
                {editing === field ? (
                  <Button
                    size="small"
                    appearance="primary"
                    onClick={async () => {
                      await props.onField(field, "edit", original, draft);
                      setEditing(null);
                    }}
                  >
                    Save
                  </Button>
                ) : (
                  <>
                    <Tooltip content="Accept" relationship="label">
                      <Button
                        size="small"
                        appearance="subtle"
                        icon={<CheckmarkRegular />}
                        onClick={() => props.onField(field, "accept", original)}
                        data-act="accept"
                      />
                    </Tooltip>
                    <Tooltip content="Edit" relationship="label">
                      <Button
                        size="small"
                        appearance="subtle"
                        icon={<EditRegular />}
                        onClick={() => {
                          setDraft(original);
                          setEditing(field);
                        }}
                        data-act="edit"
                      />
                    </Tooltip>
                    <Tooltip content="Reject" relationship="label">
                      <Button
                        size="small"
                        appearance="subtle"
                        icon={<DismissRegular />}
                        onClick={() => props.onField(field, "reject", original)}
                        data-act="reject"
                      />
                    </Tooltip>
                  </>
                )}
              </span>
            </div>
          );
        }),
      )}
    </section>
  );
}

/* ---------------------------------------------------------------- criteria */

const CRIT_CLASS: Record<string, string> = { "Fully Met": "met", "Partially Met": "partial", "Not Met": "notmet" };
const CRIT_COLOR: Record<string, "success" | "warning" | "danger" | "informative"> = {
  "Fully Met": "success",
  "Partially Met": "warning",
  "Not Met": "danger",
};

function CriteriaPane({ c, onOpen }: { c: CaseDetail; onOpen: (c: Citation) => void }) {
  const policy = c.policies[0];
  return (
    <section className="card stack" aria-label="Criteria">
      <p className="section-title">Policy criteria</p>
      {policy ? (
        <div className="row">
          <b>{policy.blob_url}</b>
          {policy.score !== null ? <span className="muted">match {Math.round(policy.score * 100)}%</span> : null}
          {policy.freshness ? (
            <FreshBadge status={policy.freshness.status} title={freshnessTitle(policy.freshness)}>
              policy {freshnessShort(policy.freshness)}
            </FreshBadge>
          ) : null}
          <a
            href={`#/indexes/runtime/${encodeURIComponent(c.case_id)}`}
            onClick={(e) => {
              e.preventDefault();
              go(`/indexes/runtime/${encodeURIComponent(c.case_id)}`);
            }}
          >
            How was this policy found?
          </a>
        </div>
      ) : null}
      {c.assessments.length === 0 ? <Text className="muted">Criteria appear once the criteria agent finishes.</Text> : null}
      {c.assessments.map((a, i) => (
        <div className={`criterion ${CRIT_CLASS[a.status] ?? ""}`} key={a.criterion_id} data-criterion={a.criterion_id}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <b>
              C{i + 1}. {a.criterion_text ?? a.criterion_id}
            </b>
            <Badge appearance="tint" color={CRIT_COLOR[a.status] ?? "informative"}>
              {a.status}
            </Badge>
          </div>
          {a.evidence ? <div style={{ marginTop: 4 }}>{a.evidence}</div> : null}
          {a.notes ? <div className="muted" style={{ marginTop: 2 }}>{a.notes}</div> : null}
          <div className="row" style={{ marginTop: 4, gap: 4 }}>
            {a.policy_reference ? <span className="muted">{a.policy_reference}</span> : null}
            <Cites list={[...a.citations, ...a.policy_citations]} onOpen={onOpen} />
          </div>
        </div>
      ))}
    </section>
  );
}

/* -------------------------------------------------------------------- chat */

function ChatPane(props: { c: CaseDetail; onOpen: (c: Citation) => void; onChat: (msg: string) => Promise<void> }) {
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);
  const running = props.c.status === "running";

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [props.c.chat.length]);

  const send = async (text: string) => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      await props.onChat(text);
      setMsg("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card stack" aria-label="Ask about this case">
      <p className="section-title">Ask about this case</p>
      <div className="chat-log" ref={logRef}>
        {props.c.chat.length === 0 ? (
          <Text className="muted" size={200}>
            Answers come only from this case's documents and policy, with citations.
          </Text>
        ) : null}
        {props.c.chat.map((t, i) => (
          <div className={`bubble ${t.role}`} key={i} data-role={t.role}>
            <div style={{ whiteSpace: "pre-wrap" }}>{t.text}</div>
            {t.citations?.length ? (
              <div style={{ marginTop: 4 }}>
                <Cites list={t.citations} onOpen={props.onOpen} />
              </div>
            ) : null}
          </div>
        ))}
        {busy ? <Spinner size="extra-tiny" label="Thinking…" /> : null}
      </div>
      <div className="row" style={{ gap: 4 }}>
        {SUGGESTIONS.map((s) => (
          <Button key={s} size="small" shape="circular" disabled={busy || running} onClick={() => send(s)}>
            {s}
          </Button>
        ))}
      </div>
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <Input
          style={{ flex: 1 }}
          value={msg}
          disabled={busy || running}
          placeholder={running ? "Available when agents finish" : "Ask about criteria, evidence, freshness…"}
          aria-label="Chat message"
          onChange={(_, d) => setMsg(d.value)}
          onKeyDown={(e) => e.key === "Enter" && send(msg)}
        />
        <Button icon={<SendRegular />} appearance="primary" disabled={busy || running} onClick={() => send(msg)} aria-label="Send" />
      </div>
    </section>
  );
}

/* --------------------------------------------------------- recommendation */

function RecommendationBar(props: { c: CaseDetail; onDecide: (d: Decision, note?: string) => Promise<void>; onOpen: (c: Citation) => void }) {
  const { c } = props;
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<Decision | null>(null);
  const det = c.determination;
  const rec = c.recommendation;
  const decided = c.human_decision;

  const decide = async (d: Decision) => {
    setBusy(d);
    try {
      await props.onDecide(d, note || undefined);
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="recbar stack" aria-label="Recommendation">
      <div className="row">
        <Text weight="semibold">AI recommendation:</Text>
        {rec ? (
          <>
            <DecisionBadge decision={rec.decision} label={rec.label} />
            <span className="muted">
              {[
                rec.confidence === null ? null : `${Math.round(rec.confidence * 100)}% confidence`,
                rec.criteria_total ? `${rec.criteria_met}/${rec.criteria_total} criteria` : null,
                rec.model,
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
          </>
        ) : (
          <Spinner size="extra-tiny" label="Agents running…" />
        )}
        <span className="spacer" />
        <Button onClick={() => go(`/case/${c.case_id}/trace`)}>View trace</Button>
        <EvalCaseDialog caseId={c.case_id} trigger={<Button disabled={c.status === "running"}>Save as eval case</Button>} />
      </div>
      {det ? (
        <div>
          {det.rationale} <Cites list={det.citations} onOpen={props.onOpen} />
          {det.missing_information.length ? (
            <div className="muted" style={{ marginTop: 4 }}>
              Missing: {det.missing_information.map((m) => `${m.information_needed} (${m.reason})`).join("; ")}
            </div>
          ) : null}
        </div>
      ) : null}
      {decided ? (
        <MessageBar intent={c.status === "approved" ? "success" : "warning"} data-testid="decided">
          <MessageBarBody>
            <MessageBarTitle>
              <StatusBadge status={c.status} />
            </MessageBarTitle>{" "}
            by {decided.reviewer}
            {decided.note ? ` · “${decided.note}”` : ""}
          </MessageBarBody>
        </MessageBar>
      ) : (
        <div className="row" style={{ alignItems: "flex-end" }}>
          <Textarea
            style={{ flex: 1, minWidth: 260 }}
            resize="vertical"
            placeholder="Reviewer note (sent with pend/deny and stored with the decision)"
            aria-label="Reviewer note"
            value={note}
            onChange={(_, d) => setNote(d.value)}
          />
          <Button appearance="primary" disabled={!rec || busy !== null} onClick={() => decide("approve")} data-decide="approve">
            {busy === "approve" ? <Spinner size="extra-tiny" /> : "Approve"}
          </Button>
          <Button disabled={!rec || busy !== null} onClick={() => decide("pend")} data-decide="pend">
            {busy === "pend" ? <Spinner size="extra-tiny" /> : "Pend: request info"}
          </Button>
          <Tooltip content="Denials are never automatic; this routes to a medical director." relationship="description">
            <Button disabled={!rec || busy !== null} onClick={() => decide("deny")} data-decide="deny">
              {busy === "deny" ? <Spinner size="extra-tiny" /> : "Deny → MD review"}
            </Button>
          </Tooltip>
        </div>
      )}
    </section>
  );
}

/* -------------------------------------------------------------------- page */

export function CasePage({ id }: { id: string }) {
  const [c, setC] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<Active>(null);
  const [doc, setDoc] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const d = await api.getCase(id);
      setC(d);
      setDoc((cur) => (cur && d.documents[cur] ? cur : (Object.keys(d.documents)[0] ?? "")));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const running = c?.status === "running";
  useEffect(() => {
    if (!running) return;
    return followCase(id, () => load(), () => load());
  }, [id, running, load]);

  const guard = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      setError(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const openCite = (cite: Citation) => {
    setActive({ source: cite.source, quote: cite.quote });
    if (c?.documents[cite.source]) setDoc(cite.source);
  };

  if (!c) return error ? <ErrorBar error={error} /> : <Spinner label="Loading case…" />;

  const allWarnings = c.recommendation?.warnings ?? [];
  const conflicts = allWarnings.filter((w) => w.toLowerCase().startsWith("label conflict"));
  const partial = allWarnings.filter((w) => w.toLowerCase().startsWith("partial upload"));
  const warnings = allWarnings.filter((w) => !conflicts.includes(w) && !partial.includes(w));
  return (
    <>
      <BladeHeader
        icon={<DocumentBulletListRegular />}
        title={`${c.case_id} · ${c.patient_name}`}
        subtitle={`Prior authorization request · ${c.request}`}
        badges={
          <>
            <StatusBadge status={c.status} />
            {c.prototype ? <PrototypeBadge conflict={c.prototype.label_conflict} /> : null}
            {c.upload ? (
              <Badge appearance="tint" color="brand" icon={<ArrowUploadRegular />} data-testid="uploaded-badge">
                Uploaded
              </Badge>
            ) : null}
          </>
        }
      />
      <CommandBar>
        <Button appearance="subtle" icon={<ArrowLeftRegular />} onClick={() => go("/queue")}>
          Back to queue
        </Button>
        <span className="cmd-sep" />
        {c.owner !== REVIEWER ? (
          <Button appearance="subtle" icon={<PersonAddRegular />} onClick={() => guard(() => api.assign(id, REVIEWER))}>
            Assign to me
          </Button>
        ) : null}
        <Button appearance="subtle" icon={<TimelineRegular />} onClick={() => go(`/case/${c.case_id}/trace`)}>
          View trace
        </Button>
      </CommandBar>
      <Essentials
        items={[
          ["Member", `${c.patient_name} · ${c.member_id}`],
          ["Line of business", c.line_of_business],
          ["Provider", c.provider_org],
          [
            "Urgency",
            <Badge key="u" appearance="outline" color={c.urgency === "expedited" ? "danger" : "informative"}>
              {c.urgency}
            </Badge>,
          ],
          ["SLA remaining", <b key="s">{slaText(c.sla_left_hours, c.sla_hours)}</b>],
          ["Owner", <span key="o" data-testid="owner">{c.owner ?? "Unassigned"}</span>],
          ["Runner", c.runner === "ground_truth" ? "MD ground truth (prototype)" : c.runner],
          [
            "Source",
            c.upload
              ? `Uploaded packet · ${matchText(c)}`
              : c.prototype
              ? `${c.prototype.folder}${c.prototype.pdf_label ? ` · PDF says ${c.prototype.pdf_label}` : ""}`
              : "Demo data",
          ],
        ]}
      />
      <ErrorBar error={error} />
      <Stepper steps={c.workflow} />
      <FreshnessStrip
        entries={c.freshness_report}
        busy={busy}
        onReverify={(f) => {
          setBusy(f.kind);
          guard(() => api.reverify(id, f.kind)).finally(() => setBusy(null));
        }}
      />
      {conflicts.length ? (
        <MessageBar intent="error" style={{ marginBottom: 10 }} data-testid="label-conflict">
          <MessageBarBody>
            <MessageBarTitle>Ground-truth label conflict</MessageBarTitle>
            {conflicts.map((w) => w.replace(/^label conflict:\s*/i, "").replace(/\.?$/, ".")).join(" ")} Confirm the label with the medical director before you use this case for parity.
          </MessageBarBody>
        </MessageBar>
      ) : null}
      {partial.length ? (
        <MessageBar intent="info" style={{ marginBottom: 10 }} data-testid="partial-upload">
          <MessageBarBody>
            <MessageBarTitle>Partial packet</MessageBarTitle>
            {partial.map((w) => w.replace(/^partial upload:\s*/i, "").replace(/\.?$/, ".")).join(" ")}
          </MessageBarBody>
        </MessageBar>
      ) : null}
      {warnings.length ? (
        <MessageBar intent="warning" style={{ marginBottom: 10 }} data-testid="advisory">
          <MessageBarBody>
            <MessageBarTitle>Freshness advisory</MessageBarTitle>
            {warnings.join(" ")} Freshness never changes the AI recommendation; re-verify before you decide.
          </MessageBarBody>
        </MessageBar>
      ) : null}
      {running ? (
        <MessageBar intent="info" style={{ marginBottom: 10 }}>
          <MessageBarBody>
            Agents are working: {c.progress.current ?? "starting"} ({c.progress.done}/{c.progress.total}). This page
            updates live.
          </MessageBarBody>
        </MessageBar>
      ) : null}
      <div className="panes">
        <EvidencePane
          c={c}
          active={active}
          doc={doc}
          setDoc={setDoc}
          onOpen={openCite}
          onField={(field, action, original, corrected) =>
            guard(() =>
              api.fieldAction(id, {
                field,
                action,
                original,
                corrected: corrected ?? null,
                reviewer: REVIEWER,
                note: null,
              }),
            )
          }
        />
        <CriteriaPane c={c} onOpen={openCite} />
        <ChatPane c={c} onOpen={openCite} onChat={(m) => guard(() => api.chat(id, m))} />
      </div>
      <RecommendationBar c={c} onOpen={openCite} onDecide={(d, note) => guard(() => api.decide(id, d, REVIEWER, note))} />
      <Text size={200} className="muted">
        Trace {c.trace_id} · <Link onClick={() => go(`/case/${c.case_id}/trace`)}>open waterfall</Link>
      </Text>
    </>
  );
}
