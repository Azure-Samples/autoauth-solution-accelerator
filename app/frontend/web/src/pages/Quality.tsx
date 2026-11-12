import { useEffect, useState } from "react";
import {
  Badge,
  MessageBar,
  MessageBarBody,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
} from "@fluentui/react-components";
import { api, type Quality } from "../api";
import { BladeHeader, ErrorBar } from "../components/common";
import { DataBarVerticalRegular } from "@fluentui/react-icons";

const pct = (n: number) => `${Math.round(n * 100)}%`;
const label = (k: string) => k.replace(/_/g, " ");
/** Lets dotted module paths wrap at segment boundaries instead of mid-word. */
const dotted = (p: string) =>
  p.split(".").map((seg, i, all) => (
    <span key={i}>
      {seg}
      {i < all.length - 1 ? (
        <>
          .<wbr />
        </>
      ) : null}
    </span>
  ));

export function QualityPage() {
  const [q, setQ] = useState<Quality | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.quality().then(setQ, (e) => setError((e as Error).message));
  }, []);

  if (!q) return error ? <ErrorBar error={error} /> : <Spinner label="Loading quality…" />;

  return (
    <>
      <BladeHeader
        icon={<DataBarVerticalRegular />}
        title="Quality"
        subtitle="How well the agents are doing: offline evals from evals/cases plus live reviewer signals"
      />
      <MessageBar intent="info" style={{ marginBottom: 10 }}>
        <MessageBarBody>
          {q.illustrative_scores.note.split("`").map((part, i) => (i % 2 ? <code key={i}>{part}</code> : part))}
        </MessageBarBody>
      </MessageBar>

      <div className="grid2">
        <section className="card stack" aria-label="Regression">
          <p className="section-title">Regression: legacy vs agentic (illustrative)</p>
          <Table size="small" aria-label="Regression">
            <TableHeader>
              <TableRow>
                <TableHeaderCell>Family</TableHeaderCell>
                <TableHeaderCell>Legacy</TableHeaderCell>
                <TableHeaderCell>Agentic</TableHeaderCell>
                <TableHeaderCell>Δ</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {q.illustrative_scores.rows.map((r) => {
                const d = r.candidate - r.baseline;
                return (
                  <TableRow key={r.family} data-family={r.family}>
                    <TableCell>{r.family}</TableCell>
                    <TableCell>{pct(r.baseline)}</TableCell>
                    <TableCell>{pct(r.candidate)}</TableCell>
                    <TableCell className={d > 0 ? "delta-up" : d < 0 ? "delta-down" : "muted"}>
                      {d === 0 ? "±0" : `${d > 0 ? "+" : "−"}${Math.round(Math.abs(d) * 100)} pts`}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </section>

        <section className="card stack" aria-label="Live signals">
          <p className="section-title">Live signals</p>
          <div className="kpis kpis-compact">
            {Object.entries(q.illustrative_scores.online).map(([k, v]) => (
              <div className="kpi-tile illustrative" key={k}>
                <span className="kpi-label">{label(k)}</span>
                <span className="kpi-value">{pct(v)}</span>
                <span className="muted">illustrative</span>
              </div>
            ))}
            {Object.entries(q.live).map(([k, v]) => (
              <div className="kpi-tile" key={k} data-kpi={k}>
                <span className="kpi-label">{label(k)}</span>
                <span className="kpi-value">
                  {v === null ? "—" : typeof v === "number" && k.endsWith("rate") ? pct(v) : String(v)}
                </span>
                <span className="muted">live</span>
              </div>
            ))}
          </div>
          <span className="muted">Reviewer overrides count field edits and rejects across demo cases.</span>
        </section>
      </div>

      <section className="card stack" aria-label="Eval suites" style={{ marginTop: 12 }}>
        <p className="section-title">Eval suites (evals/cases, unchanged)</p>
        <Table size="small" aria-label="Eval suites" className="suites-table">
          <TableHeader>
            <TableRow>
              <TableHeaderCell style={{ width: "20%" }}>Suite</TableHeaderCell>
              <TableHeaderCell style={{ width: "17%" }}>Family</TableHeaderCell>
              <TableHeaderCell style={{ width: "23%" }}>Pipeline</TableHeaderCell>
              <TableHeaderCell style={{ width: "26%" }}>Evaluators</TableHeaderCell>
              <TableHeaderCell style={{ width: "6%" }}>Cases</TableHeaderCell>
              <TableHeaderCell style={{ width: "8%" }}>Evaluations</TableHeaderCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {q.suites.map((s) => (
              <TableRow key={s.suite} data-suite={s.suite}>
                <TableCell>
                  <code>{s.suite}</code>
                </TableCell>
                <TableCell>{s.family}</TableCell>
                <TableCell>
                  <code>{dotted(s.pipeline)}</code>
                </TableCell>
                <TableCell>
                  <div className="badge-wrap">
                    {s.evaluators.map((e) => (
                      <Badge key={e} size="small" appearance="tint">
                        {e}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>{s.cases}</TableCell>
                <TableCell>{s.evaluations}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>

      <div className="grid2" style={{ marginTop: 12 }}>
        <section className="card stack" aria-label="Families">
          <p className="section-title">By family</p>
          {q.families.map((f) => (
            <div key={f.family}>
              <b>{f.family}</b>{" "}
              <span className="muted">
                {f.suites} suite(s) · {f.evaluations} evaluation(s) · {f.evaluators.join(", ")}
              </span>
            </div>
          ))}
        </section>
        <section className="card stack" aria-label="Limits">
          <p className="section-title">Freshness limits and SLAs</p>
          {Object.entries(q.freshness_limits_days).map(([k, v]) => (
            <div key={k}>
              {label(k)}: <b>{v} days</b>
            </div>
          ))}
          {Object.entries(q.sla_hours).map(([k, v]) => (
            <div key={k}>
              SLA {k}: <b>{v} h</b>
            </div>
          ))}
        </section>
      </div>
    </>
  );
}
