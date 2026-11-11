import { useState, type ReactElement, type ReactNode } from "react";
import {
  Badge,
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DialogTrigger,
  MessageBar,
  MessageBarBody,
  Skeleton,
  SkeletonItem,
  Spinner,
  Tooltip,
} from "@fluentui/react-components";
import { WarningFilled } from "@fluentui/react-icons";
import { api, type FreshStatus, type FreshnessEntry, type Status } from "../api";

const FRESH_COLOR: Record<FreshStatus, "success" | "warning" | "danger" | "subtle" | "informative"> = {
  fresh: "success",
  aging: "warning",
  stale: "danger",
  unknown: "subtle",
  pending: "informative",
};

export function FreshBadge(props: { status: FreshStatus; children?: ReactNode; title?: string }) {
  const badge = (
    <Badge appearance="tint" color={FRESH_COLOR[props.status]} data-fresh={props.status}>
      {props.children ?? props.status}
    </Badge>
  );
  return props.title ? (
    <Tooltip content={props.title} relationship="description">
      {badge}
    </Tooltip>
  ) : (
    badge
  );
}

export function freshnessTitle(f: FreshnessEntry): string {
  const age = f.age_days === null ? "no date on record" : `${f.age_days} days old`;
  return `${f.subject}: ${age} · limit ${f.max_age_days}d · source ${f.source}${f.note ? ` · ${f.note}` : ""}`;
}

export function freshnessShort(f: FreshnessEntry): string {
  return f.age_days === null ? "unknown" : `${f.age_days}d`;
}

const STATUS: Record<Status, { label: string; color: "brand" | "informative" | "success" | "warning" | "danger" }> = {
  ready: { label: "Ready for review", color: "brand" },
  running: { label: "Agents running", color: "informative" },
  approved: { label: "Approved", color: "success" },
  pended: { label: "Pended · info requested", color: "warning" },
  md_review: { label: "MD review", color: "danger" },
};

export function StatusBadge({ status }: { status: Status }) {
  const s = STATUS[status];
  return (
    <Badge appearance="filled" color={s.color}>
      {s.label}
    </Badge>
  );
}

export function ErrorBar({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <MessageBar intent="error">
      <MessageBarBody>{error}</MessageBarBody>
    </MessageBar>
  );
}

/** Azure-portal blade header: icon tile, title, resource-type subtitle and a right-hand slot. */
export function BladeHeader(props: {
  icon: ReactElement;
  title: ReactNode;
  subtitle?: ReactNode;
  badges?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="blade-head">
      <span className="blade-icon" aria-hidden>
        {props.icon}
      </span>
      <div className="blade-titles">
        <div className="row" style={{ gap: 10 }}>
          <h1>{props.title}</h1>
          {props.badges}
        </div>
        {props.subtitle ? <div className="blade-sub">{props.subtitle}</div> : null}
      </div>
      <span className="spacer" />
      {props.actions}
    </div>
  );
}

/** Command bar under a blade header. */
export function CommandBar({ children }: { children: ReactNode }) {
  return (
    <div className="commandbar" role="toolbar">
      {children}
    </div>
  );
}

/** Two-column key/value "Essentials" panel. */
export function Essentials({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="essentials" aria-label="Essentials">
      {items.map(([k, v]) => (
        <div key={k} className="ess-item">
          <dt>{k}</dt>
          <dd>{v ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Marks a real case from utils/data/cases whose label is an MD ground truth, not a model output. */
export function PrototypeBadge({ conflict }: { conflict?: boolean }) {
  return (
    <Tooltip
      content={
        conflict
          ? "Real prototype case. The PDF header disagrees with ground_truth.json; the ground truth is shown."
          : "Real prototype case from utils/data/cases. The label is the MD ground truth from ground_truth.json."
      }
      relationship="description"
    >
      <Badge
        appearance="tint"
        color={conflict ? "warning" : "brand"}
        shape="rounded"
        icon={conflict ? <WarningFilled /> : undefined}
        aria-label={conflict ? "Prototype, label conflict" : "Prototype"}
        data-prototype
        className="nowrap"
      >
        Prototype
      </Badge>
    </Tooltip>
  );
}

const DECISION_COLOR: Record<string, "success" | "danger" | "warning" | "informative"> = {
  approved: "success",
  approve: "success",
  rejected: "danger",
  denied: "danger",
  deny: "danger",
  "needs more information": "warning",
  pend: "warning",
};

export function DecisionBadge({ decision, label }: { decision: string; label?: string }) {
  const color = DECISION_COLOR[decision.toLowerCase()] ?? "informative";
  return (
    <Badge appearance="filled" color={color} data-decision={decision}>
      {label ?? decision}
    </Badge>
  );
}

/** Confidence meter. Ground-truth (prototype) cases have no model score, so they show the source instead. */
export function Confidence({ value, runner }: { value: number | null; runner?: string }) {
  if (value === null) {
    return <span className="muted" title="Label comes from MD review, not a model">{runner === "ground_truth" ? "MD ground truth" : "—"}</span>;
  }
  const p = Math.round(value * 100);
  return (
    <div className="row" title={`${p}%`} style={{ flexWrap: "nowrap" }}>
      <div className={`meter${p < 60 ? " low" : p < 80 ? " mid" : ""}`}>
        <span style={{ width: `${p}%` }} />
      </div>
      <span className="muted">{p}%</span>
    </div>
  );
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <Skeleton aria-label="Loading" className="card">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="row" style={{ padding: "8px 0", flexWrap: "nowrap" }}>
          <SkeletonItem size={16} style={{ width: "18%" }} />
          <SkeletonItem size={16} style={{ width: "30%" }} />
          <SkeletonItem size={16} style={{ width: "22%" }} />
          <SkeletonItem size={16} style={{ width: "15%" }} />
        </div>
      ))}
    </Skeleton>
  );
}

/** "Save as eval case" turns reviewer edits into YAML for evals/cases via TraceToEvaluation. */
export function EvalCaseDialog({ caseId, trigger }: { caseId: string; trigger: ReactElement }) {
  const [yaml, setYaml] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setYaml(null);
    setError(null);
    try {
      const res = await api.evalCase(caseId);
      setName(`${res.name} · ${res.evaluations} evaluation(s)`);
      setCount(res.evaluations);
      setYaml(res.yaml);
    } catch (e) {
      setError(String((e as Error).message));
    }
  };

  return (
    <Dialog onOpenChange={(_, d) => d.open && load()}>
      <DialogTrigger disableButtonEnhancement>{trigger}</DialogTrigger>
      <DialogSurface style={{ maxWidth: 760 }}>
        <DialogBody>
          <DialogTitle>Save as eval case</DialogTitle>
          <DialogContent>
            <p className="muted">
              Generated by <code>TraceToEvaluation.from_reviewer_actions</code>. Drop it into{" "}
              <code>evals/cases/</code>; the existing evaluators score it unchanged.
            </p>
            <ErrorBar error={error} />
            {yaml === null && !error ? <Spinner size="tiny" label="Building case…" /> : null}
            {yaml !== null ? (
              <>
                <b data-testid="eval-name">{name}</b>
                {count === 0 ? (
                  <MessageBar intent="info" data-testid="eval-empty">
                    <MessageBarBody>
                      No corrections yet. Edit or reject an extracted field, or override the AI decision, to
                      create a ground-truth row.
                    </MessageBarBody>
                  </MessageBar>
                ) : null}
                <pre className="yaml" data-testid="eval-yaml">
                  {yaml}
                </pre>
              </>
            ) : null}
          </DialogContent>
          <DialogActions>
            {yaml ? (
              <Button appearance="primary" onClick={() => navigator.clipboard?.writeText(yaml)}>
                Copy YAML
              </Button>
            ) : null}
            <DialogTrigger disableButtonEnhancement>
              <Button>Close</Button>
            </DialogTrigger>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}
