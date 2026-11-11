import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Spinner, Text } from "@fluentui/react-components";
import { ArrowLeftRegular, TimelineRegular } from "@fluentui/react-icons";
import { api, followCase, type Trace } from "../api";
import { BladeHeader, CommandBar, ErrorBar, EvalCaseDialog } from "../components/common";
import { go } from "../App";

export function TracePage({ id }: { id: string }) {
  const [t, setT] = useState<Trace | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setT(await api.trace(id));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const running = t !== null && t.total_seconds === null;
  useEffect(() => {
    if (!running) return;
    return followCase(id, () => load(), () => load());
  }, [id, running, load]);

  if (!t) return error ? <ErrorBar error={error} /> : <Spinner label="Loading trace…" />;

  const total = t.total_seconds ?? Math.max(1, ...t.spans.map((s) => s.seconds ?? 0));
  let offset = 0;
  const rows = t.spans.map((s) => {
    const start = s.depth === 1 ? offset : 0;
    if (s.depth === 1 && s.seconds) offset += s.seconds;
    return { ...s, start };
  });

  return (
    <>
      <BladeHeader
        icon={<TimelineRegular />}
        title={`Trace · ${id}`}
        subtitle={t.trace_id}
        badges={<Badge appearance="outline">runner: {t.runner}</Badge>}
        actions={
          <span className="row" style={{ gap: 16 }}>
            <span>
              Total <b data-testid="trace-total">{t.total_seconds === null ? "running…" : `${t.total_seconds.toFixed(1)}s`}</b>
            </span>
            {t.estimated_cost_usd !== null ? (
              <span>
                Est. cost <b>${t.estimated_cost_usd.toFixed(2)}</b>
              </span>
            ) : null}
          </span>
        }
      />
      <CommandBar>
        <Button appearance="subtle" icon={<ArrowLeftRegular />} onClick={() => go(`/case/${id}`)}>
          Back to case
        </Button>
        <EvalCaseDialog caseId={id} trigger={<Button appearance="subtle" disabled={running}>Save as eval case</Button>} />
      </CommandBar>
      <ErrorBar error={error} />
      <div className="card">
        <div className="waterfall" aria-label="Span waterfall">
          {rows.map((s, i) => {
            const width = s.seconds ? (s.seconds / total) * 100 : s.status === "run" || s.status === "wait" ? 4 : 0;
            const left = s.depth === 0 ? 0 : (s.start / total) * 100;
            const cls = s.status === "todo" ? "todo" : s.status === "run" || s.status === "wait" ? "run" : "";
            return (
              <div className="span-row" key={i} data-span={s.name} data-status={s.status}>
                <span style={{ paddingLeft: s.depth * 16 }}>
                  <code>{s.name}</code>
                </span>
                <div className="bar-track">
                  {width > 0 ? (
                    <div className={`bar ${cls}`} style={{ left: `${Math.min(left, 99)}%`, width: `${Math.min(width, 100 - left)}%` }} />
                  ) : null}
                </div>
                <span className="muted">
                  {s.seconds !== null ? `${s.seconds.toFixed(1)}s` : s.status === "wait" ? "waiting" : s.status === "run" ? "…" : ""}
                </span>
                <span className="muted">
                  {s.detail}
                  {s.signal ? (
                    <Badge size="small" appearance="tint" style={{ marginLeft: 4 }}>
                      {s.signal}
                    </Badge>
                  ) : null}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      <Text size={200} className="muted">
        Spans follow the OpenTelemetry GenAI conventions emitted by the agentic runner. Reviewer edits on this case become
        an eval case via "Save as eval case".
      </Text>
    </>
  );
}
