import { useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
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
import { ArrowClockwiseRegular, FlagFilled, SearchRegular, TaskListSquareLtrRegular } from "@fluentui/react-icons";
import { api, slaText, type CaseFilters, type CaseSummary } from "../api";
import {
  BladeHeader,
  CommandBar,
  Confidence,
  ErrorBar,
  FreshBadge,
  PrototypeBadge,
  StatusBadge,
  TableSkeleton,
} from "../components/common";
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
  const prototypes = rows?.filter((r) => r.prototype).length ?? 0;

  return (
    <>
      <BladeHeader
        icon={<TaskListSquareLtrRegular />}
        title="Reviewer queue"
        subtitle="Prior authorization · Contoso Health Plan"
      />
      <CommandBar>
        <Button appearance="subtle" icon={<ArrowClockwiseRegular />} onClick={load}>
          Refresh
        </Button>
        <span className="cmd-sep" />
        <Input
          contentBefore={<SearchRegular />}
          placeholder="Filter by case, patient or drug"
          aria-label="Search cases"
          onChange={(_, d) => set("q")(d.value)}
          style={{ minWidth: 260 }}
        />
        <Filter label="Status" opts={STATUS_OPTS} value={filters.status} onChange={set("status")} />
        <Filter label="Urgency" opts={URGENCY_OPTS} value={filters.urgency} onChange={set("urgency")} />
        <Filter label="Freshness" opts={FRESH_OPTS} value={filters.freshness} onChange={set("freshness")} />
        <span className="spacer" />
        {rows ? (
          <Text className="muted" size={200}>
            Showing {rows.length} case(s) · {prototypes} prototype · sorted by SLA · {flagged} need re-verification
          </Text>
        ) : null}
      </CommandBar>
      <ErrorBar error={error} />
      {rows === null ? (
        <TableSkeleton />
      ) : (
        <div className="card">
          <Table className="queue-table" aria-label="Prior authorization queue" size="small">
            <TableHeader>
              <TableRow>
                <TableHeaderCell style={{ width: 28 }} />
                <TableHeaderCell style={{ width: "21%" }}>Case · patient</TableHeaderCell>
                <TableHeaderCell style={{ width: "14%" }}>Requested</TableHeaderCell>
                <TableHeaderCell style={{ width: "9%" }}>Urgency</TableHeaderCell>
                <TableHeaderCell style={{ width: "15%" }}>AI recommendation</TableHeaderCell>
                <TableHeaderCell style={{ width: "12%" }}>Confidence</TableHeaderCell>
                <TableHeaderCell style={{ width: "13%" }}>Data freshness</TableHeaderCell>
                <TableHeaderCell style={{ width: "8%" }}>SLA left</TableHeaderCell>
                <TableHeaderCell style={{ width: "8%" }}>Owner</TableHeaderCell>
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
                        <span className="row" style={{ gap: 6 }}>
                          <a className="cell-link" href={`#/case/${r.case_id}`} onClick={(e) => e.stopPropagation()}>
                            {r.case_id}
                          </a>
                          {r.prototype ? <PrototypeBadge conflict={r.prototype.label_conflict} /> : null}
                        </span>
                        <span className="muted cell-sub">
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
                          {rec.label}
                          {rec.criteria_total ? (
                            <span className="muted">
                              {" "}
                              ({rec.criteria_met}/{rec.criteria_total} criteria)
                            </span>
                          ) : null}
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      {rec ? <Confidence value={rec.confidence} runner={r.runner} /> : null}
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
