import { useEffect, useRef, useState } from "react";
import {
  Button,
  Dropdown,
  Field,
  Input,
  MessageBar,
  MessageBarBody,
  Option,
  ProgressBar,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
} from "@fluentui/react-components";
import { api, followCase, type CaseSummary, type SubmitIn } from "../api";
import { BladeHeader, ErrorBar, StatusBadge } from "../components/common";
import { BuildingRegular } from "@fluentui/react-icons";
import { go } from "../App";

const ORG = "Lakeside GI Assoc.";
const FILES = ["request.pdf", "clinical_note.pdf", "labs.pdf"];

type Form = Omit<SubmitIn, "files">;
const EMPTY: Form = {
  patient_name: "",
  member_id: "",
  drug: "",
  urgency: "standard",
  prescriber: "",
  specialty: "",
  provider_org: ORG,
};

/** Advisory checks before submit; they never block. */
function precheck(f: Form, files: string[]): string[] {
  const out: string[] = [];
  if (!f.member_id) out.push("No member ID: eligibility cannot be checked and freshness will show unknown.");
  if (!files.some((x) => /note|clinical/i.test(x))) out.push("No clinical note attached: most criteria need one.");
  if (!files.some((x) => /lab/i.test(x))) out.push("No labs attached: lab-based criteria may pend.");
  if (f.drug && !f.specialty) out.push("Prescriber specialty is empty: specialist criteria cannot be verified.");
  return out;
}

export function ProviderPage() {
  const [form, setForm] = useState<Form>(EMPTY);
  const [files, setFiles] = useState<string[]>(FILES);
  const [mine, setMine] = useState<CaseSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const subs = useRef<Record<string, () => void>>({});

  const refresh = async () => {
    try {
      const res = await api.listCases();
      setMine(res.cases.filter((c) => c.provider_org === ORG));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const follow = (id: string) => {
    if (subs.current[id]) return;
    subs.current[id] = followCase(
      id,
      (s) => setMine((cur) => cur.map((c) => (c.case_id === s.case_id ? s : c))),
      () => {
        delete subs.current[id];
        refresh();
      },
    );
  };

  useEffect(() => {
    refresh();
    const all = subs.current;
    return () => Object.values(all).forEach((u) => u());
  }, []);

  useEffect(() => {
    mine.filter((c) => c.status === "running").forEach((c) => follow(c.case_id));
  }, [mine]);

  const set = (k: keyof Form) => (_: unknown, d: { value: string }) => setForm((f) => ({ ...f, [k]: d.value }));
  const checks = precheck(form, files);
  const valid = form.patient_name.trim() !== "" && form.drug.trim() !== "" && files.length > 0;

  const submit = async () => {
    setBusy(true);
    try {
      const created = await api.submit({ ...form, files });
      setMine((cur) => [created, ...cur.filter((c) => c.case_id !== created.case_id)]);
      follow(created.case_id);
      setForm(EMPTY);
      setFiles(FILES);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <BladeHeader icon={<BuildingRegular />} title="Provider portal" subtitle={`${ORG} · submit a prior authorization and watch it move`} />
      <div className="commandbar" />
      <ErrorBar error={error} />
      <div className="grid2">
        <section className="card stack" aria-label="New request">
          <p className="section-title">New request</p>
          <Field label="Patient name" required>
            <Input value={form.patient_name} onChange={set("patient_name")} name="patient_name" />
          </Field>
          <Field label="Member ID">
            <Input value={form.member_id} onChange={set("member_id")} name="member_id" />
          </Field>
          <Field label="Drug or service" required>
            <Input value={form.drug} onChange={set("drug")} name="drug" placeholder="e.g. Dupixent 300mg" />
          </Field>
          <div className="row">
            <Field label="Prescriber" style={{ flex: 1 }}>
              <Input value={form.prescriber} onChange={set("prescriber")} name="prescriber" />
            </Field>
            <Field label="Specialty" style={{ flex: 1 }}>
              <Input value={form.specialty} onChange={set("specialty")} name="specialty" />
            </Field>
          </div>
          <Field label="Urgency">
            <Dropdown
              value={form.urgency}
              selectedOptions={[form.urgency]}
              onOptionSelect={(_, d) => setForm((f) => ({ ...f, urgency: d.optionValue as Form["urgency"] }))}
            >
              <Option value="standard">standard</Option>
              <Option value="expedited">expedited</Option>
            </Dropdown>
          </Field>
          <Field label="Attachments" hint="Demo: file names only. Remove one to see the pre-check react.">
            <div className="row" style={{ gap: 4 }}>
              {files.map((f) => (
                <Button key={f} size="small" shape="circular" onClick={() => setFiles((x) => x.filter((y) => y !== f))}>
                  {f} ✕
                </Button>
              ))}
              {FILES.filter((f) => !files.includes(f)).map((f) => (
                <Button key={f} size="small" shape="circular" appearance="subtle" onClick={() => setFiles((x) => [...x, f])}>
                  + {f}
                </Button>
              ))}
            </div>
          </Field>
          {checks.length ? (
            <MessageBar intent="warning" data-testid="precheck">
              <MessageBarBody>
                <b>Pre-check:</b> {checks.join(" ")}
              </MessageBarBody>
            </MessageBar>
          ) : valid ? (
            <MessageBar intent="success" data-testid="precheck">
              <MessageBarBody>Pre-check passed. Nothing obvious is missing.</MessageBarBody>
            </MessageBar>
          ) : null}
          <div className="row">
            <Button appearance="primary" disabled={!valid || busy} onClick={submit} data-testid="submit">
              {busy ? <Spinner size="extra-tiny" /> : "Submit request"}
            </Button>
          </div>
        </section>

        <section className="card stack" aria-label="My requests">
          <p className="section-title">My requests</p>
          <Table size="small" aria-label="My requests">
            <TableHeader>
              <TableRow>
                <TableHeaderCell>Case</TableHeaderCell>
                <TableHeaderCell>Request</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Progress</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mine.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4}>
                    <span className="muted">No requests yet.</span>
                  </TableCell>
                </TableRow>
              ) : null}
              {mine.map((c) => (
                <TableRow key={c.case_id} data-case={c.case_id} onClick={() => go(`/case/${c.case_id}`)} style={{ cursor: "pointer" }}>
                  <TableCell>
                    <b>{c.case_id}</b>
                    <div className="muted">{c.patient_name}</div>
                  </TableCell>
                  <TableCell>{c.request}</TableCell>
                  <TableCell>
                    <StatusBadge status={c.status} />
                  </TableCell>
                  <TableCell>
                    <ProgressBar value={c.progress.done / Math.max(1, c.progress.total)} thickness="large" />
                    <span className="muted">
                      {c.status === "running" ? (c.progress.current ?? "starting") : `${c.progress.done}/${c.progress.total} steps`}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <span className="muted">Status streams live over server-sent events; no refresh needed.</span>
        </section>
      </div>
    </>
  );
}
