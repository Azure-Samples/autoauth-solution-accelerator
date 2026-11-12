import { useEffect, useRef, useState, type DragEvent } from "react";
import { Badge, Button, Dropdown, Field, Option, Spinner, Text } from "@fluentui/react-components";
import { ArrowUploadRegular, DismissRegular, DocumentPdfRegular, SparkleRegular } from "@fluentui/react-icons";
import { api, type CaseSummary, type Sample } from "../api";

type Urgency = "standard" | "expedited";

/** One-line provenance for an uploaded case: which demo scenario it matched and how. */
export function matchText(c: CaseSummary): string {
  const u = c.upload;
  if (!u) return "";
  if (!u.case_key) return "No demo scenario matched these files; the case will route to a reviewer.";
  const hits = u.files.filter((f) => f.case_key === u.case_key);
  const how = Array.from(new Set(hits.map((f) => f.matched_by).filter(Boolean))).join(", ");
  return `Matched demo scenario ${u.case_key} (${hits.length}/${u.files.length} files${how ? ` by ${how}` : ""}).`;
}

const kb = (n: number) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

/** Drop a claim packet (PDFs) and the agents take it from there. In this demo the run is
 * simulated: the server matches the files to a scenario in utils/data/cases. */
export function UploadClaim(props: { providerOrg: string; onCreated: (c: CaseSummary) => void; onError: (m: string | null) => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [source, setSource] = useState<string | null>(null);
  const [urgency, setUrgency] = useState<Urgency>("standard");
  const [samples, setSamples] = useState<Sample[] | null>(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.samples().then((r) => setSamples(r.samples), () => setSamples([]));
  }, []);

  const add = (list: FileList | File[] | null) => {
    if (!list) return;
    const pdfs = Array.from(list).filter((f) => f.type === "application/pdf" || /\.pdf$/i.test(f.name));
    if (pdfs.length < Array.from(list).length) props.onError("Only PDF files are accepted.");
    setFiles((cur) => [...cur.filter((c) => !pdfs.some((p) => p.name === c.name)), ...pdfs]);
    setSource(null);
  };

  const drop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    add(e.dataTransfer.files);
  };

  const loadSample = async (s: Sample) => {
    setBusy(s.key);
    try {
      setFiles(await api.sampleFiles(s));
      setSource(s.label);
      props.onError(null);
    } catch (e) {
      props.onError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const upload = async () => {
    setBusy("upload");
    try {
      const created = await api.uploadClaim(files, { urgency, provider_org: props.providerOrg });
      props.onCreated(created);
      props.onError(null);
      setFiles([]);
      setSource(null);
    } catch (e) {
      props.onError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="card stack" aria-label="Upload claim document">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <p className="section-title" style={{ margin: 0 }}>
          Upload claim document
        </p>
        <Badge appearance="tint" color="informative" icon={<SparkleRegular />}>
          Agents extract the rest
        </Badge>
      </div>
      <div
        className={`dropzone${over ? " over" : ""}`}
        role="button"
        tabIndex={0}
        aria-label="Drop PDF files or browse"
        data-testid="dropzone"
        onClick={() => input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
      >
        <ArrowUploadRegular fontSize={28} />
        <div>
          <b>Drag and drop the claim packet here</b> or <span className="link">browse</span>
        </div>
        <span className="muted">PA form, clinical notes, labs, imaging. PDF, up to 25 MB each.</span>
        <input
          ref={input}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          data-testid="file-input"
          onChange={(e) => {
            add(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {files.length ? (
        <div className="staged" data-testid="staged">
          {source ? (
            <Text size={200} className="muted">
              Demo packet {source} loaded from utils/data/cases
            </Text>
          ) : null}
          {files.map((f) => (
            <div key={f.name} className="staged-file">
              <DocumentPdfRegular className="pdf-icon" />
              <span className="staged-name">{f.name}</span>
              <span className="muted">{kb(f.size)}</span>
              <Button
                size="small"
                appearance="subtle"
                icon={<DismissRegular />}
                aria-label={`Remove ${f.name}`}
                onClick={() => setFiles((cur) => cur.filter((c) => c.name !== f.name))}
              />
            </div>
          ))}
        </div>
      ) : null}

      <div className="row" style={{ alignItems: "flex-end" }}>
        <Field label="Urgency">
          <Dropdown value={urgency} selectedOptions={[urgency]} onOptionSelect={(_, d) => setUrgency(d.optionValue as Urgency)}>
            <Option value="standard">standard</Option>
            <Option value="expedited">expedited</Option>
          </Dropdown>
        </Field>
        <Button
          appearance="primary"
          icon={busy === "upload" ? <Spinner size="extra-tiny" /> : <ArrowUploadRegular />}
          disabled={!files.length || busy !== null}
          onClick={upload}
          data-testid="upload"
        >
          Upload and start review
        </Button>
      </div>

      <div className="stack" style={{ gap: 6 }}>
        <Text size={200} weight="semibold">
          Or use a demo claim from the original scenarios
        </Text>
        <div className="sample-tiles" data-testid="samples">
          {samples === null ? <Spinner size="tiny" label="Loading scenarios" /> : null}
          {samples?.map((s) => (
            <button
              key={s.key}
              type="button"
              className="sample-tile"
              data-sample={s.key}
              disabled={busy !== null}
              onClick={() => loadSample(s)}
              title={s.files.map((f) => f.name).join("\n")}
            >
              <span className="sample-label">{busy === s.key ? <Spinner size="extra-tiny" /> : s.label}</span>
              <span className="sample-req">{s.request ?? "Claim packet"}</span>
              <span className="muted">
                {s.files.length} PDF{s.files.length === 1 ? "" : "s"} · MD: {s.ground_truth}
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
