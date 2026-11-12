import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Link,
  MessageBar,
  MessageBarBody,
  MessageBarTitle,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  Tooltip,
} from "@fluentui/react-components";
import {
  ArrowClockwiseRegular,
  BranchCompareRegular,
  CheckmarkCircleFilled,
  CircleRegular,
  CopyRegular,
  DismissCircleFilled,
  WarningFilled,
} from "@fluentui/react-icons";
import { api, pct, type Parity, type ParityResult } from "../api";
import { BladeHeader, CommandBar, DecisionBadge, ErrorBar, TableSkeleton } from "../components/common";
import { go } from "../App";

const RUNNER_LABEL: Record<string, string> = {
  legacy: "Legacy pipeline",
  agents: "Agents (in-process)",
  "agents-af": "Agents (Agent Framework)",
};

function ResultPill({ r }: { r: ParityResult | undefined }) {
  if (!r || r.status === "not_run") {
    return (
      <span className="pill muted" data-parity="not_run">
        <CircleRegular /> Not run
      </span>
    );
  }
  if (r.status === "error") {
    return (
      <Tooltip content={r.error ?? "Runner failed"} relationship="description">
        <span className="pill pill-err" data-parity="error">
          <WarningFilled /> Error
        </span>
      </Tooltip>
    );
  }
  const tip = [r.decision, r.seconds != null ? `${r.seconds.toFixed(1)}s` : null, r.recorded_at]
    .filter(Boolean)
    .join(" · ");
  return (
    <Tooltip content={tip} relationship="description">
      <span className={`pill ${r.match ? "pill-ok" : "pill-bad"}`} data-parity={r.match ? "match" : "mismatch"}>
        {r.match ? <CheckmarkCircleFilled /> : <DismissCircleFilled />} {r.decision ?? "—"}
      </span>
    </Tooltip>
  );
}

export function ParityPage() {
  const [p, setP] = useState<Parity | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setP(await api.parity());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    load();
  }, []);

  const anyRun = p ? Object.values(p.summary).some((s) => s.run > 0) : false;

  return (
    <>
      <BladeHeader
        icon={<BranchCompareRegular />}
        title="Prototype parity"
        subtitle="Real cases from utils/data/cases, scored against the MD ground truth"
      />
      <CommandBar>
        <Button appearance="subtle" icon={<ArrowClockwiseRegular />} onClick={load}>
          Refresh
        </Button>
        {p ? (
          <Button
            appearance="subtle"
            icon={<CopyRegular />}
            onClick={() => navigator.clipboard?.writeText(p.command)}
          >
            Copy run command
          </Button>
        ) : null}
        <span className="spacer" />
        {p ? (
          <Text size={200} className="muted">
            Source <code>{p.source}</code>
          </Text>
        ) : null}
      </CommandBar>
      <ErrorBar error={error} />
      {!p ? (
        <TableSkeleton rows={10} />
      ) : (
        <>
          <div className="kpis">
            <div className="kpi-tile">
              <span className="kpi-label">Prototype cases</span>
              <span className="kpi-value">{p.cases.length}</span>
              <span className="muted">{p.label_conflicts.length} with a label conflict</span>
            </div>
            {p.runners.map((r) => {
              const s = p.summary[r];
              const rate = pct(s?.rate ?? null);
              return (
                <div className="kpi-tile" key={r} data-runner={r}>
                  <span className="kpi-label">{RUNNER_LABEL[r] ?? r}</span>
                  <span className="kpi-value">{rate === null ? "—" : `${rate}%`}</span>
                  <span className="muted">
                    {s && s.run ? `${s.matched}/${s.scored} match ground truth` : "Not run yet"}
                  </span>
                </div>
              );
            })}
          </div>

          {!anyRun ? (
            <MessageBar intent="info" style={{ marginBottom: 12 }}>
              <MessageBarBody>
                <MessageBarTitle>No runner results recorded yet</MessageBarTitle>
                Runs need the deployed Azure resources and a <code>.env</code>. Then run <code>{p.command}</code>. Results
                are written to the parity runs file and show up here.
              </MessageBarBody>
            </MessageBar>
          ) : null}

          {p.label_conflicts.length ? (
            <MessageBar intent="warning" style={{ marginBottom: 12 }} data-testid="label-conflicts">
              <MessageBarBody>
                <MessageBarTitle>Ground-truth label conflict</MessageBarTitle>
                The PDF headers for {p.label_conflicts.join(", ")} disagree with <code>ground_truth.json</code>. Parity is
                scored against the ground truth. Confirm the correct labels with the MD before you trust these rows.
              </MessageBarBody>
            </MessageBar>
          ) : null}

          <div className="card flush">
            <Table size="small" aria-label="Prototype parity">
              <TableHeader>
                <TableRow>
                  <TableHeaderCell>Case</TableHeaderCell>
                  <TableHeaderCell>Policy</TableHeaderCell>
                  <TableHeaderCell>Ground truth</TableHeaderCell>
                  <TableHeaderCell>PDF label</TableHeaderCell>
                  {p.runners.map((r) => (
                    <TableHeaderCell key={r}>{RUNNER_LABEL[r] ?? r}</TableHeaderCell>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {p.cases.map((c) => (
                  <TableRow key={c.case_id} data-parity-case={c.case_id}>
                    <TableCell>
                      <div className="stack" style={{ gap: 0 }}>
                        <Link onClick={() => go(`/case/${c.ui_case_id}`)}>{c.ui_case_id}</Link>
                        <span className="muted">
                          {c.case_id} · {Object.values(c.files).flat().length} file(s)
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>{c.policy ?? <span className="muted">—</span>}</TableCell>
                    <TableCell>
                      <Tooltip content={c.ground_truth_note ?? "ground_truth.json"} relationship="description">
                        <span>
                          <DecisionBadge decision={c.ground_truth} />
                        </span>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      {c.pdf_label ? (
                        <span className="row" style={{ gap: 4, flexWrap: "nowrap" }}>
                          {c.label_conflict ? (
                            <WarningFilled color="#d83b01" aria-label="Disagrees with ground truth" />
                          ) : null}
                          <Badge appearance="outline" color={c.label_conflict ? "warning" : "informative"}>
                            {c.pdf_label}
                          </Badge>
                        </span>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </TableCell>
                    {p.runners.map((r) => (
                      <TableCell key={r}>
                        <ResultPill r={c.results[r]} />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </>
  );
}
