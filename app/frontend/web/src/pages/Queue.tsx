import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Dropdown,
  Input,
  Option,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
} from "@fluentui/react-components";
import { FlagFilled, SearchRegular } from "@fluentui/react-icons";
import { api, slaText, type CaseFilters, type CaseSummary } from "../api";
import { ErrorBar, FreshBadge, StatusBadge } from "../components/common";
import { go } from "../App";

const STATUS_OPTS = [
  ["", "All statuses"],
  ["ready", "Ready for review"],
  ["running", "Agents running"],
  ["pended", "Pended"],
  ["md_review", "MD review"],
  ["approved", "Approved"],
] as const;
const URGENCY_OPTS = [
  ["", "Any urgency"],
  ["expedited", "Expedited"],
  ["standard", "Standard"],
] as const;
const FRESH_OPTS = [
  ["", "Any freshness"],
  ["flagged", "Needs re-verification"],
] as const;

function Filter(props: {
  label: string;
  opts: readonly (readonly [string, string])[];
  value: string | undefined;
  onChange: (v: string) => void;
}) {
  const current = props.opts.find(([v]) => v === (props.value ?? "")) ?? props.opts[0];
  return (
    <Dropdown
      aria-label={props.label}
      value={current[1]}
      selectedOptions={[current[0]]}
      onOptionSelect={(_, d) => props.onChange(d.optionValue ?? "")}
      style={{ minWidth: 170 }}
    >
      {props.opts.map(([v, l]) => (
        <Option key={v || "all"} value={v}>
          {l}
        </Option>
      ))}
    </Dropdown>
  );
}

export function QueuePage() {
  const [filters, setFilters] = useState<CaseFilters>({});
  const [rows, setRows] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.listCases(filters);
      setRows(res.cases);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [filters]);

  useEffect(() => {
    load();
    const t = window.setInterval(load, 3000);
    return () => window.clearInterval(t);
  }, [load]);

  const set = (k: keyof CaseFilters) => (v: string) => setFilters((f) => ({ ...f, [k]: v || undefined }));
  const flagged = rows?.filter((r) => ["stale", "unknown"].includes(r.freshness.overall)).length ?? 0;

  return (
    <>
      <div className="page-head">
        <h1>Reviewer queue</h1>
        {rows ? (
          <Text className="muted">
            {rows.length} case(s) · sorted by SLA · {flagged} need re-verification
          </Text>
        ) : null}
        <span className="spacer" />
        <Input
          contentBefore={<SearchRegular />}
          placeholder="Case, patient or drug"
          aria-label="Search cases"
          onChange={(_, d) => set("q")(d.value)}
        />
        <Filter label="Status" opts={STATUS_OPTS} value={filters.status} onChange={set("status")} />
        <Filter label="Urgency" opts={URGENCY_OPTS} value={filters.urgency} onChange={set("urgency")} />
        <Filter label="Freshness" opts={FRESH_OPTS} value={filters.freshness} onChange={set("freshness")} />
      </div>
      <ErrorBar error={error} />
      {rows === null ? (
        <Spinner label="Loading queue…" />
      ) : (
        <div className="card">
          <Table className="queue-table" aria-label="Prior authorization queue" size="small">
            <TableHeader>
              <TableRow>
                <TableHeaderCell style={{ width: 28 }} />
                <TableHeaderCell>Case · patient</TableHeaderCell>
                <TableHeaderCell>Requested</TableHeaderCell>
                <TableHeaderCell>Urgency</TableHeaderCell>
                <TableHeaderCell>AI recommendation</TableHeaderCell>
                <TableHeaderCell>Confidence</TableHeaderCell>
                <TableHeaderCell>Data freshness</TableHeaderCell>
                <TableHeaderCell>SLA left</TableHeaderCell>
                <TableHeaderCell>Owner</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => {
                const rec = r.recommendation;
                const late = r.sla_left_hours < r.sla_hours * 0.25;
                const flag = r.freshness.overall === "stale" || (rec?.warnings.length ?? 0) > 0;
                return (
                  <TableRow
                    key={r.case_id}
                    className={r.status === "running" ? "running" : undefined}
                    onClick={() => go(`/case/${r.case_id}`)}
                    data-case={r.case_id}
                  >
                    <TableCell>{flag ? <FlagFilled color="#c50f1f" aria-label="Flagged" /> : null}</TableCell>
                    <TableCell>
                      <div className="stack" style={{ gap: 0 }}>
                        <b>{r.case_id}</b>
                        <span className="muted">
                          {r.patient_name} · {r.line_of_business}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>{r.request}</TableCell>
                    <TableCell>
                      <Badge appearance="outline" color={r.urgency === "expedited" ? "danger" : "informative"}>
                        {r.urgency}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {r.status === "running" ? (
                        <Spinner
                          size="extra-tiny"
                          label={`${r.progress.current ?? "agents"} · ${r.progress.done}/${r.progress.total}`}
                        />
                      ) : r.human_decision ? (
                        <StatusBadge status={r.status} />
                      ) : rec ? (
                        <span>
                          {rec.label}{" "}
                          <span className="muted">
                            ({rec.criteria_met}/{rec.criteria_total} criteria)
                          </span>
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      {rec ? (
                        <div className="row" title={`${Math.round(rec.confidence * 100)}%`}>
                          <div className="meter">
                            <span style={{ width: `${rec.confidence * 100}%` }} />
                          </div>
                          <span className="muted">{Math.round(rec.confidence * 100)}%</span>
                        </div>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <FreshBadge status={r.freshness.overall}>{r.freshness.label}</FreshBadge>
                    </TableCell>
                    <TableCell className={late ? "sla-late" : undefined}>
                      {slaText(r.sla_left_hours, r.sla_hours)}
                    </TableCell>
                    <TableCell>{r.owner ?? <span className="muted">Unassigned</span>}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
