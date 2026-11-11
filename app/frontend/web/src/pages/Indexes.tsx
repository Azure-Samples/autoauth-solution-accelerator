import { useEffect, useMemo, useRef, useState, type ReactElement, type ReactNode } from "react";
import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Badge,
  Button,
  Dropdown,
  DrawerBody,
  DrawerHeader,
  DrawerHeaderTitle,
  Field,
  Input,
  Link,
  MessageBar,
  MessageBarActions,
  MessageBarBody,
  MessageBarTitle,
  Option,
  OverlayDrawer,
  Spinner,
  Text,
  Tooltip,
} from "@fluentui/react-components";
import {
  ArrowLeftRegular,
  ArrowRightRegular,
  ClockRegular,
  CloudArrowUpRegular,
  DatabaseRegular,
  DismissRegular,
  DocumentPdfRegular,
  DocumentSearchRegular,
  LibraryRegular,
  LightbulbRegular,
  OpenRegular,
  SearchRegular,
} from "@fluentui/react-icons";
import { api, type IndexCatalog, type IndexSearch, type IndexTier, type IndexedPolicy, type PolicyChunk, type RuntimeCase } from "../api";
import { go, type IndexStep } from "../App";
import { BladeHeader, ErrorBar, TableSkeleton } from "../components/common";

const GLOSSARY: Record<string, string> = {
  chunk: "A slice of a policy page (up to 3,000 characters). Search returns chunks, not whole PDFs, so the agent reads only the relevant part.",
  overlap: "The last 500 characters of one chunk are repeated at the start of the next, so a sentence cut at a boundary is still found whole.",
  embedding: "A list of 3,072 numbers that captures what a chunk means. Chunks with similar meaning have nearby embeddings, even with different wording.",
  hybrid: "Hybrid search combines keyword matching with embedding similarity, then a semantic ranker reorders the top results.",
  ocr: "Optical character recognition: reading text from the image of each page, so scanned PDFs are searchable too.",
};

/** Dotted-underline term with a plain-language definition on hover or focus. */
function Term({ k, children }: { k: keyof typeof GLOSSARY; children: ReactNode }) {
  return (
    <Tooltip content={GLOSSARY[k]} relationship="description" withArrow>
      <span className="term" tabIndex={0}>
        {children}
      </span>
    </Tooltip>
  );
}

const STEPS: { id: IndexStep; n: number; title: string; blurb: string; icon: ReactElement }[] = [
  { id: "prior", n: 1, title: "Before any claim", blurb: "Policies are read, split and indexed once.", icon: <LibraryRegular /> },
  { id: "runtime", n: 2, title: "When a claim arrives", blurb: "Claim files are read; the index is only queried.", icon: <CloudArrowUpRegular /> },
  { id: "kept", n: 3, title: "What's kept", blurb: "Where each artifact lives and for how long.", icon: <DatabaseRegular /> },
];

const TIER: Record<IndexTier, { label: string; cls: string }> = {
  prior: { label: "Indexed ahead", cls: "tier-prior" },
  runtime: { label: "Per claim", cls: "tier-runtime" },
  persists: { label: "Persists", cls: "tier-persists" },
};

function stepPath(step: IndexStep, caseId?: string) {
  return step === "runtime" && caseId ? `/indexes/runtime/${caseId}` : `/indexes/${step}`;
}

function Why({ children }: { children: ReactNode }) {
  return (
    <div className="why" role="note">
      <LightbulbRegular className="why-icon" aria-hidden />
      <div>
        <b>Why it matters</b>
        <div>{children}</div>
      </div>
    </div>
  );
}

function Flow({ items }: { items: { title: ReactNode; detail: string; tag?: ReactNode }[] }) {
  return (
    <ol className="flow">
      {items.map((it, i) => (
        <li key={i} className="flow-step">
          <span className="flow-num">{i + 1}</span>
          <div className="flow-title">{it.title}</div>
          <div className="flow-detail">{it.detail}</div>
          {it.tag ? <div className="flow-tag">{it.tag}</div> : null}
        </li>
      ))}
    </ol>
  );
}

/** Wraps each matched search term in a mark. */
function Highlight({ text, terms }: { text: string; terms: string[] }) {
  if (!terms.length) return <>{text}</>;
  const esc = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`\\b(${esc.join("|")})\\w*`, "gi");
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(re)) {
    out.push(text.slice(last, m.index));
    out.push(<mark key={m.index}>{m[0]}</mark>);
    last = m.index! + m[0].length;
  }
  out.push(text.slice(last));
  return <>{out}</>;
}

export function IndexesPage({ step, caseId }: { step: IndexStep; caseId?: string }) {
  const [cat, setCat] = useState<IndexCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [peek, setPeek] = useState<{ name: string; chunk?: string } | null>(null);

  useEffect(() => {
    api.indexes().then(setCat, (e) => setError(String(e)));
  }, []);

  const idx = STEPS.findIndex((s) => s.id === step);
  const prev = STEPS[idx - 1];
  const next = STEPS[idx + 1];

  return (
    <div className="stack" style={{ gap: 16 }}>
      <BladeHeader
        icon={<LibraryRegular />}
        title="Indexed documents"
        subtitle="How AutoAuth finds the right policy for a claim, and what it keeps afterwards"
        badges={
          cat ? (
            <Badge appearance="tint" color={cat.live.status === "healthy" ? "success" : "warning"}>
              Azure index: {cat.live.status}
            </Badge>
          ) : null
        }
      />
      <ErrorBar error={error} />
      {cat ? <LiveHealth live={cat.live} /> : null}

      <nav className="guide" aria-label="Steps">
        {STEPS.map((s, i) => (
          <button
            key={s.id}
            className={`guide-step${s.id === step ? " current" : ""}${i < idx ? " done" : ""}`}
            aria-current={s.id === step ? "step" : undefined}
            onClick={() => go(stepPath(s.id, s.id === "runtime" ? caseId : undefined))}
          >
            <span className="guide-num">{s.n}</span>
            <span className="guide-icon" aria-hidden>
              {s.icon}
            </span>
            <span className="guide-text">
              <b>{s.title}</b>
              <span>{s.blurb}</span>
            </span>
          </button>
        ))}
      </nav>

      {!cat ? (
        <div className="card">
          <TableSkeleton rows={5} />
        </div>
      ) : step === "prior" ? (
        <PriorStep cat={cat} onPeek={(name) => setPeek({ name })} />
      ) : step === "runtime" ? (
        <RuntimeStep cat={cat} caseId={caseId} onPeek={(name, chunk) => setPeek({ name, chunk })} />
      ) : (
        <KeptStep cat={cat} />
      )}

      <div className="row guide-foot">
        {prev ? (
          <Button icon={<ArrowLeftRegular />} onClick={() => go(stepPath(prev.id))}>
            {prev.n}. {prev.title}
          </Button>
        ) : null}
        <span className="spacer" />
        {next ? (
          <Button appearance="primary" icon={<ArrowRightRegular />} iconPosition="after" onClick={() => go(stepPath(next.id, caseId))}>
            Next: {next.title}
          </Button>
        ) : (
          <Button appearance="primary" icon={<ArrowRightRegular />} iconPosition="after" onClick={() => go("/queue")}>
            Back to the reviewer queue
          </Button>
        )}
      </div>

      <ChunkDrawer target={peek} onClose={() => setPeek(null)} />
    </div>
  );
}

function LiveHealth({ live }: { live: IndexCatalog["live"] }) {
  const [open, setOpen] = useState(false);
  if (live.status === "healthy") return null;
  return (
    <MessageBar intent="warning" layout="multiline">
      <MessageBarBody>
        <MessageBarTitle>The deployed Azure index needs a re-run</MessageBarTitle>
        {live.summary} This page explains the design using the policy PDFs in the repo, so it works either way.
        {open ? (
          <div className="live-detail">
            <div className="muted">
              Checked {live.as_of} on {live.service} ({live.environment})
            </div>
            <ul>
              {live.findings.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <div>
              <b>Fix:</b> {live.fix}
            </div>
          </div>
        ) : null}
      </MessageBarBody>
      <MessageBarActions>
        <Button size="small" onClick={() => setOpen((o) => !o)}>
          {open ? "Hide details" : "Show details"}
        </Button>
      </MessageBarActions>
    </MessageBar>
  );
}

function PriorStep({ cat, onPeek }: { cat: IndexCatalog; onPeek: (name: string) => void }) {
  const docs = cat.prior.documents;
  const pages = docs.reduce((n, d) => n + d.pages, 0);
  const ix = cat.index;
  const glossFor: Record<string, ReactNode> = {
    OCR: <Term k="ocr">OCR</Term>,
    Split: <Term k="chunk">Split into chunks</Term>,
    Embed: <Term k="embedding">Embed</Term>,
  };
  return (
    <div className="stack" style={{ gap: 16 }}>
      <Why>
        Payer policies are long. Indexing them once, ahead of time, lets each claim find the few paragraphs that matter in
        about a second instead of reading every PDF.
      </Why>

      <div className="kpis">
        <div className="kpi-tile">
          <div className="kpi-label">Policies</div>
          <div className="kpi-value">{docs.length}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Pages read</div>
          <div className="kpi-value">{pages}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">
            <Term k="chunk">Chunks</Term>
          </div>
          <div className="kpi-value">{cat.prior.expected_chunks}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">
            <Term k="overlap">Chunk size / overlap</Term>
          </div>
          <div className="kpi-value kpi-small">
            {ix.chunking.size.toLocaleString()} / {ix.chunking.overlap} chars
          </div>
        </div>
      </div>

      <section className="card stack">
        <p className="section-title">How a policy PDF becomes searchable</p>
        <Flow items={ix.pipeline.map((p) => ({ title: glossFor[p.step] ?? p.step, detail: p.detail }))} />
        <Text size={200} className="muted">
          Runs once per policy as the <code>policyIndexer</code> job after <code>azd provision</code>, and again whenever a
          policy is added or replaced in <code>{ix.container}/{ix.prefix}</code>.
        </Text>
      </section>

      <section className="stack">
        <p className="section-title">Policies in the index</p>
        <div className="policy-grid">
          {docs.map((d) => (
            <PolicyCard key={d.name} d={d} onPeek={() => onPeek(d.name)} />
          ))}
        </div>
      </section>

      <Accordion collapsible>
        <AccordionItem value="schema">
          <AccordionHeader>Technical details: index schema and retrieval settings</AccordionHeader>
          <AccordionPanel>
            <div className="grid2" style={{ alignItems: "start" }}>
              <div className="card flush">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Type</th>
                      <th>Purpose</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ix.fields.map((f) => (
                      <tr key={f.name}>
                        <td>
                          <code>{f.name}</code> <span className="pill muted">{f.role}</span>
                        </td>
                        <td className="muted">{f.type}</td>
                        <td>{f.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <dl className="essentials">
                {(
                  [
                    ["Index", ix.name],
                    ["Indexer / skillset", `${ix.indexer} / ${ix.skillset}`],
                    ["Data source", `${ix.data_source} (${ix.container}/${ix.prefix})`],
                    ["Retrieval", ix.retrieval.mode],
                    ["Top results", `${ix.retrieval.top} chunks, k=${ix.retrieval.k_nearest_neighbors}, vector weight ${ix.retrieval.vector_weight}`],
                    ["Vector", `${ix.vector.dimensions} dims, HNSW m=${ix.vector.m}, efSearch=${ix.vector.ef_search}`],
                    ["Semantic config", ix.semantic_config],
                  ] as [string, string][]
                ).map(([k, v]) => (
                  <div key={k} className="ess-item">
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </AccordionPanel>
        </AccordionItem>
      </Accordion>
    </div>
  );
}

function PolicyCard({ d, onPeek }: { d: IndexedPolicy; onPeek: () => void }) {
  return (
    <article className="card policy-card">
      <div className="row" style={{ gap: 8 }}>
        <DocumentPdfRegular className="policy-icon" aria-hidden />
        <span className="muted">{d.name}</span>
        <span className="spacer" />
        {d.payer ? <span className="pill">{d.payer}</span> : null}
      </div>
      <b className="policy-title">{d.title}</b>
      <div className="policy-meta">
        <span>
          <ClockRegular aria-hidden /> Effective {d.effective ?? "unknown"}
        </span>
        <span>{d.pages} pages</span>
        <span>{d.chunks} chunks</span>
      </div>
      {d.scenarios.length ? (
        <div className="muted" style={{ fontSize: 12 }}>
          Used by demo cases {d.scenarios.join(", ")}
        </div>
      ) : null}
      <div className="row" style={{ marginTop: "auto" }}>
        <Button size="small" appearance="primary" icon={<DocumentSearchRegular />} onClick={onPeek}>
          See its chunks
        </Button>
        <Button size="small" as="a" href={api.policyUrl(d.name)} target="_blank" icon={<OpenRegular />}>
          Open PDF
        </Button>
      </div>
    </article>
  );
}

function RuntimeStep({
  cat,
  caseId,
  onPeek,
}: {
  cat: IndexCatalog;
  caseId?: string;
  onPeek: (name: string, chunk?: string) => void;
}) {
  const cases = cat.runtime.cases;
  const ordered = useMemo(
    () => [...cases.filter((c) => c.policy), ...cases.filter((c) => !c.policy)],
    [cases],
  );
  const current: RuntimeCase | undefined = cases.find((c) => c.case_id === caseId) ?? ordered[0];
  const policy = cat.prior.documents.find((d) => d.name === current?.policy);

  return (
    <div className="stack" style={{ gap: 16 }}>
      <Why>
        Claim documents are read for this case only. They are <b>never added to the policy index</b>, so one patient's
        records can't show up in another patient's search.
      </Why>

      <section className="card stack">
        <p className="section-title">What happens when a claim is uploaded</p>
        <Flow
          items={cat.runtime.steps.map((s) => ({
            title: s.step === "Query" ? <Term k="hybrid">Query the index</Term> : s.step,
            detail: s.detail,
            tag: (
              <span className={`pill ${s.writes.startsWith("Nothing") ? "pill-ok" : "muted"}`}>
                {s.writes.startsWith("Nothing") ? "Read only" : `Writes: ${s.writes}`}
              </span>
            ),
          }))}
        />
      </section>

      {current ? (
        <section className="card stack">
          <div className="row" style={{ alignItems: "end" }}>
            <Field label="Follow a claim through these steps" style={{ minWidth: 340 }}>
              <Dropdown
                value={`${current.case_id} · ${current.patient_name} · ${current.request}`}
                selectedOptions={[current.case_id]}
                onOptionSelect={(_, d) => d.optionValue && go(`/indexes/runtime/${d.optionValue}`)}
              >
                {ordered.map((c) => (
                  <Option key={c.case_id} value={c.case_id} text={`${c.case_id} · ${c.patient_name} · ${c.request}`}>
                    {c.case_id} · {c.patient_name} · {c.request}
                    {c.policy ? "" : " (seeded)"}
                  </Option>
                ))}
              </Dropdown>
            </Field>
            <span className="spacer" />
            <Button icon={<OpenRegular />} onClick={() => go(`/case/${current.case_id}`)}>
              Open this case
            </Button>
          </div>

          <div className="grid2" style={{ alignItems: "start" }}>
            <div className="stack">
              <div className="mini-head">
                <span className="flow-num">1</span> Uploaded and read (not indexed)
              </div>
              <ul className="filelist">
                {current.documents.map((d) => (
                  <li key={d.name}>
                    <DocumentPdfRegular aria-hidden />
                    <div>
                      <b>{d.name}</b> <span className="muted">· {d.pages} pages</span>
                      <div className="path">{d.raw_blob}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="stack">
              <div className="mini-head">
                <span className="flow-num">3</span> Matched policy
              </div>
              {policy ? (
                <div className="matched">
                  <b>{policy.title}</b>
                  <div className="muted">
                    {policy.payer} · {policy.name} · effective {policy.effective ?? "unknown"}
                  </div>
                  <div className="row" style={{ marginTop: 6 }}>
                    <Button size="small" icon={<DocumentSearchRegular />} onClick={() => onPeek(policy.name)}>
                      See its chunks
                    </Button>
                    <Button size="small" as="a" href={api.policyUrl(policy.name)} target="_blank" icon={<OpenRegular />}>
                      Open PDF
                    </Button>
                  </div>
                </div>
              ) : current.cited_policy ? (
                <Text className="muted">
                  This seeded demo case cites <b>{current.cited_policy}</b>, an illustrative policy that is not in the
                  indexed corpus. Try the search below to see what the real index would return.
                </Text>
              ) : (
                <Text className="muted">
                  No policy has been matched for this case yet. Try the search below to see what the index would
                  return.
                </Text>
              )}
            </div>
          </div>

          <TrySearch key={current.case_id} initial={current.query} expected={current.policy} onPeek={onPeek} />
        </section>
      ) : null}
    </div>
  );
}

function TrySearch({
  initial,
  expected,
  onPeek,
}: {
  initial: string;
  expected: string | null;
  onPeek: (name: string, chunk?: string) => void;
}) {
  const [q, setQ] = useState(initial);
  const [res, setRes] = useState<IndexSearch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (text: string) => {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setRes(await api.searchIndex(text.trim()));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void run(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial]);

  return (
    <div className="stack">
      <div className="mini-head">
        <span className="flow-num">2</span> The search the agent runs
      </div>
      <Text size={200} className="muted">
        Built from the clinical facts extracted from the claim. Edit it to see how the ranking changes.
      </Text>
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          void run(q);
        }}
      >
        <Input
          value={q}
          onChange={(_, d) => setQ(d.value)}
          contentBefore={<SearchRegular />}
          style={{ flex: 1 }}
          aria-label="Search query"
        />
        <Button type="submit" appearance="primary" disabled={busy || !q.trim()}>
          Search
        </Button>
        {q !== initial ? (
          <Button
            appearance="subtle"
            onClick={() => {
              setQ(initial);
              void run(initial);
            }}
          >
            Reset
          </Button>
        ) : null}
      </form>
      <ErrorBar error={error} />
      {busy && !res ? <Spinner size="tiny" label="Searching" /> : null}
      {res ? (
        <>
          <Text size={200} className="muted">
            {res.note}
          </Text>
          <ol className="results">
            {res.results.map((r, i) => (
              <li key={r.chunk_id} className={`result${expected && r.policy === expected ? " expected" : ""}`}>
                <div className="row" style={{ gap: 8 }}>
                  <span className="rank">#{i + 1}</span>
                  <b>{r.policy}</b>
                  <span className="muted">
                    page {r.page_number} · {r.chunk_id}
                  </span>
                  {expected && r.policy === expected ? <span className="pill pill-ok">matched policy</span> : null}
                  <span className="spacer" />
                  <span className="score" title={`Relative score ${r.score}`}>
                    <span style={{ width: `${Math.round(r.score * 100)}%` }} />
                  </span>
                </div>
                <div className="snippet">
                  <Highlight text={r.snippet} terms={res.terms} />
                </div>
                <div className="row">
                  <Link onClick={() => onPeek(r.policy, r.chunk_id)}>View chunk</Link>
                  <Link href={api.policyUrl(r.policy, r.page_number)} target="_blank">
                    Open PDF at page {r.page_number}
                  </Link>
                </div>
              </li>
            ))}
          </ol>
          {res.results.length === 0 ? <Text className="muted">No chunk contains these words.</Text> : null}
        </>
      ) : null}
    </div>
  );
}

function KeptStep({ cat }: { cat: IndexCatalog }) {
  const tiers: IndexTier[] = ["prior", "runtime", "persists"];
  return (
    <div className="stack" style={{ gap: 16 }}>
      <Why>
        Knowing where each artifact lives tells you what survives a restart, what to clean up, and what to re-run when a
        policy changes.
      </Why>
      <div className="tier-legend">
        {tiers.map((t) => (
          <span key={t} className={`tier ${TIER[t].cls}`}>
            {TIER[t].label}
          </span>
        ))}
      </div>
      <div className="card flush">
        <table className="table">
          <thead>
            <tr>
              <th>Artifact</th>
              <th>When</th>
              <th>Where (Azure)</th>
              <th>How long</th>
              <th>In this demo</th>
            </tr>
          </thead>
          <tbody>
            {cat.persistence.map((p) => (
              <tr key={p.artifact}>
                <td>
                  <b>{p.artifact}</b>
                </td>
                <td>
                  <span className={`tier ${TIER[p.tier].cls}`}>{TIER[p.tier].label}</span>
                </td>
                <td className="path">{p.where}</td>
                <td>{p.lifetime}</td>
                <td className="muted">{p.offline}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Text size={200} className="muted">
        Case attachments and page images have no cleanup policy today. Add a blob lifecycle rule on{" "}
        <code>pa_proccesing_runs/</code> if claims must expire.
      </Text>
    </div>
  );
}

function ChunkDrawer({ target, onClose }: { target: { name: string; chunk?: string } | null; onClose: () => void }) {
  const [data, setData] = useState<(IndexedPolicy & { chunk_list: PolicyChunk[]; preview_chars: number }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number | "all">("all");
  const focusRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!target) return;
    setData(null);
    setError(null);
    api.policy(target.name).then(
      (d) => {
        setData(d);
        const hit = d.chunk_list.find((c) => c.chunk_id === target.chunk);
        setPage(hit ? hit.page_number : "all");
      },
      (e) => setError(String(e)),
    );
  }, [target]);

  useEffect(() => {
    focusRef.current?.scrollIntoView({ block: "center" });
  }, [data, page]);

  const pages = data ? [...new Set(data.chunk_list.map((c) => c.page_number))] : [];
  const shown = data ? data.chunk_list.filter((c) => page === "all" || c.page_number === page) : [];

  return (
    <OverlayDrawer open={!!target} position="end" size="large" onOpenChange={(_, d) => !d.open && onClose()}>
      <DrawerHeader>
        <DrawerHeaderTitle
          action={<Button appearance="subtle" aria-label="Close" icon={<DismissRegular />} onClick={onClose} />}
        >
          {data?.title ?? target?.name}
        </DrawerHeaderTitle>
        {data ? (
          <div className="muted">
            {data.payer} · {data.name} · {data.pages} pages · {data.chunks} chunks
          </div>
        ) : null}
      </DrawerHeader>
      <DrawerBody>
        <ErrorBar error={error} />
        {!data && !error ? <Spinner label="Reading chunks" /> : null}
        {data ? (
          <div className="stack">
            <Text size={200}>
              Each card is one row in the index. <mark className="overlap">Highlighted text</mark> is the{" "}
              <Term k="overlap">overlap</Term> repeated from the previous chunk.
            </Text>
            <div className="row">
              <Field label="Page">
                <Dropdown
                  value={page === "all" ? "All pages" : `Page ${page}`}
                  selectedOptions={[String(page)]}
                  onOptionSelect={(_, d) => setPage(d.optionValue === "all" ? "all" : Number(d.optionValue))}
                  style={{ minWidth: 140 }}
                >
                  <Option value="all">All pages</Option>
                  {pages.map((p) => (
                    <Option key={p} value={String(p)}>{`Page ${p}`}</Option>
                  ))}
                </Dropdown>
              </Field>
              <span className="spacer" />
              <Button as="a" href={api.policyUrl(data.name, page === "all" ? undefined : page)} target="_blank" icon={<OpenRegular />}>
                Open PDF
              </Button>
            </div>
            {shown.map((c) => (
              <ChunkCard
                key={c.chunk_id}
                c={c}
                preview={data.preview_chars}
                focused={c.chunk_id === target?.chunk}
                refFn={c.chunk_id === target?.chunk ? focusRef : undefined}
              />
            ))}
          </div>
        ) : null}
      </DrawerBody>
    </OverlayDrawer>
  );
}

function ChunkCard({
  c,
  preview,
  focused,
  refFn,
}: {
  c: PolicyChunk;
  preview: number;
  focused: boolean;
  refFn?: React.Ref<HTMLDivElement>;
}) {
  const [full, setFull] = useState(focused);
  const head = c.text.slice(0, c.overlap_chars);
  const rest = c.text.slice(c.overlap_chars);
  const limit = Math.max(preview - head.length, 0);
  return (
    <div className={`chunk${focused ? " focused" : ""}`} ref={refFn}>
      <div className="row" style={{ gap: 8 }}>
        <code>{c.chunk_id}</code>
        <span className="muted">
          page {c.page_number} · {c.chars.toLocaleString()} chars
          {c.overlap_chars ? ` · ${c.overlap_chars} overlap` : ""}
        </span>
        {focused ? <span className="pill pill-ok">search hit</span> : null}
      </div>
      <div className="doc chunk-text">
        {head ? <mark className="overlap">{full ? head : head.slice(0, preview)}</mark> : null}
        {full ? rest : rest.slice(0, limit)}
        {!full && c.text.length > preview ? "…" : ""}
      </div>
      {c.text.length > preview ? (
        <Link onClick={() => setFull((f) => !f)}>{full ? "Show less" : "Show full chunk"}</Link>
      ) : null}
    </div>
  );
}
