import { useEffect, useState } from "react";
import { api, previewUrl, type Schemas } from "./api";
import "./intelligence.css";

type Annotation = {
  id: string;
  document_id: string;
  field: string;
  value: string;
  quote: string;
  reason: string;
  status: string;
  maker: string;
  checker: string | null;
  page: number;
  bounds: number[];
};
type Finding = {
  id: string;
  status: string;
  finding: { code: string; field?: string; message: string };
  resolution: string | null;
};
type Attestation = {
  id: string;
  outcome: string;
  source: string;
  signature: string;
  payload: Record<string, unknown>;
};
type Intel = {
  corrections: Annotation[];
  discrepancies: Finding[];
  attestations: Attestation[];
};
type Run = (task: () => Promise<unknown>, message: string) => Promise<void>;
const val = (form: HTMLFormElement) =>
  Object.fromEntries(new FormData(form).entries()) as Record<string, string>;

function PdfAnnotator({
  documentId,
  page,
  width,
  height,
  bounds,
  onChange,
}: {
  documentId: string;
  page: number;
  width: number;
  height: number;
  bounds: number[];
  onChange: (bounds: number[]) => void;
}) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [start, setStart] = useState<number[] | null>(null);
  useEffect(() => {
    let cancelled = false,
      objectUrl = "";
    setUrl("");
    setError("");
    previewUrl(documentId, page)
      .then((u) => {
        objectUrl = u;
        if (!cancelled) setUrl(u);
        else URL.revokeObjectURL(u);
      })
      .catch((e) => setError(e.message));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, page]);
  if (error) return <p>{error}</p>;
  if (!url) return <p>Loading protected page preview…</p>;
  const point = (event: React.PointerEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return [
      Math.min(
        width,
        Math.max(0, ((event.clientX - rect.left) * width) / rect.width),
      ),
      Math.min(
        height,
        Math.max(0, ((event.clientY - rect.top) * height) / rect.height),
      ),
    ];
  };
  return (
    <div
      className="pdf-annotator"
      onPointerDown={(event) => {
        event.preventDefault();
        event.currentTarget.setPointerCapture(event.pointerId);
        setStart(point(event));
      }}
      onPointerMove={(event) => {
        if (start) {
          const end = point(event);
          onChange(
            [
              Math.min(start[0], end[0]),
              Math.min(start[1], end[1]),
              Math.max(start[0], end[0]),
              Math.max(start[1], end[1]),
            ].map((n) => Math.round(n * 100) / 100),
          );
        }
      }}
      onPointerUp={() => setStart(null)}
    >
      <img
        src={url}
        alt="Private PDF page preview; drag to select evidence"
        draggable={false}
      />
      <div
        className="pdf-selection"
        style={{
          left: `${(bounds[0] / width) * 100}%`,
          top: `${(bounds[1] / height) * 100}%`,
          width: `${((bounds[2] - bounds[0]) / width) * 100}%`,
          height: `${((bounds[3] - bounds[1]) / height) * 100}%`,
        }}
      />
    </div>
  );
}

export function IntelligencePanel({
  record,
  reviewer,
  maker,
  subject,
  run,
  busy,
}: {
  record: Schemas["DepositDetail"];
  reviewer: boolean;
  maker: boolean;
  subject: string;
  run: Run;
  busy: boolean;
}) {
  const [intel, setIntel] = useState<Intel>({
    corrections: [],
    discrepancies: [],
    attestations: [],
  });
  const [documentId, setDocumentId] = useState("");
  const [field, setField] = useState("amount_paise");
  const [value, setValue] = useState("");
  const [quote, setQuote] = useState("");
  const [page, setPage] = useState(1);
  const [bounds, setBounds] = useState([0, 0, 0, 0]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Intel>(`/deposits/${record.id}/intelligence`)
      .then(setIntel)
      .catch((e) => setError(e.message));
  }, [record.id, record.version]);
  const documents = record.documents.filter(
    (d) => d.active && d.status === "READY",
  );
  const doc = documents.find((d) => d.id === documentId) ?? documents[0];
  const pageSizes = (doc?.processing_metadata?.page_sizes ?? []) as number[][];
  const canPropose =
    (maker || reviewer) &&
    record.workflow !== "ACCEPTED" &&
    doc &&
    pageSizes.length > 0;
  return (
    <section className="panel">
      <div className="section-head">
        <div>
          <h2>Document intelligence & source review</h2>
          <p>
            Original extraction is retained. Proposed changes need an
            independent officer; AI cannot authorize anything.
          </p>
        </div>
        <span className="badge">EVIDENCE LINKED</span>
      </div>
      {error && <p className="error">{error}</p>}
      {record.documents
        .filter((d) => d.active)
        .map((d) => (
          <div className="document" key={d.id}>
            <div className="section-head">
              <strong>{d.category.replaceAll("_", " ")}</strong>
              <span className="badge">
                AI {String(d.processing_metadata.ai_status ?? "NOT_RUN")}
              </span>
            </div>
            <p>
              {Number(d.processing_metadata.ocr_pages ?? 0)} OCR pages ·{" "}
              {d.status} ·{" "}
              {String(
                d.processing_metadata.algorithm ??
                  "Processing metadata unavailable",
              )}
            </p>
            {reviewer && d.status === "FAILED" && (
              <button
                disabled={busy}
                onClick={() =>
                  run(
                    () =>
                      api(`/documents/${d.id}/retry`, {
                        expected_version: record.version,
                      }),
                    "Failed document returned to quarantine for a bounded retry.",
                  )
                }
              >
                Retry failed document processing
              </button>
            )}
            {(
              (d.processing_metadata.ai_proposals ?? []) as Record<
                string,
                unknown
              >[]
            ).map((proposal, i) => (
              <div className="evidence" key={i}>
                <strong>
                  ADVISORY: {String(proposal.field)} = {String(proposal.value)}
                </strong>
                <small>
                  Page {String(proposal.page)} · {String(proposal.model)} ·{" "}
                  {String(proposal.quote_linking_method)}
                </small>
                <p>{String(proposal.quote)}</p>
                {canPropose && (
                  <button
                    disabled={busy}
                    onClick={() => {
                      setDocumentId(d.id);
                      setField(String(proposal.field));
                      setValue(String(proposal.value));
                      setQuote(String(proposal.quote));
                      setPage(Number(proposal.page));
                      const original = d.evidence.find(
                        (e) => e.field === proposal.field,
                      );
                      setBounds((original?.bounds as number[]) ?? [0, 0, 0, 0]);
                    }}
                  >
                    Prepare a human correction proposal
                  </button>
                )}
              </div>
            ))}
          </div>
        ))}
      {canPropose && (
        <div className="annotation-grid">
          <div>
            <h3>1. Select the evidence region</h3>
            <label className="field">
              <span>Annotation document</span>
              <select
                value={doc.id}
                onChange={(e) => {
                  setDocumentId(e.target.value);
                  setPage(1);
                  setBounds([0, 0, 0, 0]);
                }}
              >
                {documents.map((d) => (
                  <option value={d.id} key={d.id}>
                    {d.category} · {d.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Evidence page</span>
              <input
                type="number"
                value={page}
                min={1}
                max={Math.min(3, pageSizes.length)}
                onChange={(e) => {
                  setPage(Number(e.target.value));
                  setBounds([0, 0, 0, 0]);
                }}
              />
            </label>
            {pageSizes[page - 1] && (
              <PdfAnnotator
                documentId={doc.id}
                page={page}
                width={pageSizes[page - 1][0]}
                height={pageSizes[page - 1][1]}
                bounds={bounds}
                onChange={setBounds}
              />
            )}
            <small>
              Drag over the field. Selected page coordinates:{" "}
              {bounds.join(", ")}
            </small>
          </div>
          <form
            className="review-form"
            onSubmit={(e) => {
              e.preventDefault();
              const v = val(e.currentTarget);
              run(
                () =>
                  api(`/documents/${doc.id}/corrections`, {
                    field,
                    value,
                    quote,
                    page,
                    bounds,
                    reason: v.reason,
                  }),
                "Evidence correction proposed; independent officer confirmation required.",
              );
            }}
          >
            <h3>2. Propose the transcription</h3>
            <label className="field">
              <span>Extracted field</span>
              <select value={field} onChange={(e) => setField(e.target.value)}>
                <option value="amount_paise">Amount (integer INR paise)</option>
                <option value="issue_date">Issue date (YYYY-MM-DD)</option>
                <option value="maturity_date">
                  Maturity date (YYYY-MM-DD)
                </option>
                <option value="institution_external_id">
                  Institution identifier
                </option>
              </select>
            </label>
            <label className="field">
              <span>Proposed typed value</span>
              <input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Source transcription</span>
              <textarea
                value={quote}
                onChange={(e) => setQuote(e.target.value)}
                required
                maxLength={240}
              />
            </label>
            <label className="field">
              <span>Correction rationale</span>
              <textarea name="reason" required minLength={10} />
            </label>
            <button
              className="primary"
              disabled={
                busy || bounds[2] <= bounds[0] || bounds[3] <= bounds[1]
              }
            >
              Propose evidence correction
            </button>
            <p>
              Confirmation changes the input revision and invalidates the
              previous evaluation. Source originals stay intact.
            </p>
          </form>
        </div>
      )}
      {intel.corrections.map((c) => (
        <div className="document" key={c.id}>
          <div className="section-head">
            <strong>
              {c.field} → {c.value}
            </strong>
            <span className="badge">{c.status}</span>
          </div>
          <p>
            Page {c.page} · {c.quote} · {c.reason}
          </p>
          <small>
            Maker {c.maker} · Checker {c.checker ?? "not yet confirmed"}
          </small>
          {reviewer && c.status === "PROPOSED" && c.maker !== subject && (
            <form
              className="form-grid"
              onSubmit={(e) => {
                e.preventDefault();
                const v = val(e.currentTarget);
                run(
                  () =>
                    api(`/corrections/${c.id}/decision`, {
                      decision: v.decision,
                      reason: v.reason,
                    }),
                  "Independent correction decision recorded. Reevaluate the deposit.",
                );
              }}
            >
              <label className="field">
                <span>Correction decision</span>
                <select name="decision">
                  <option>CONFIRMED</option>
                  <option>REJECTED</option>
                </select>
              </label>
              <label className="field">
                <span>Independent correction reason</span>
                <textarea name="reason" required minLength={10} />
              </label>
              <button disabled={busy}>Record correction decision</button>
            </form>
          )}
        </div>
      ))}
      <h3>Discrepancy registry</h3>
      {intel.discrepancies.length === 0 && (
        <p>No substantive discrepancies recorded for this deposit.</p>
      )}
      {intel.discrepancies.map((d) => (
        <div className="document" key={d.id}>
          <div className="section-head">
            <strong>
              {d.finding.code} {d.finding.field ?? ""}
            </strong>
            <span className="badge">{d.status}</span>
          </div>
          <p>
            {d.finding.message} {d.resolution ?? ""}
          </p>
          {reviewer && d.status === "OPEN" && (
            <form
              className="form-grid"
              onSubmit={(e) => {
                e.preventDefault();
                const v = val(e.currentTarget);
                run(
                  () =>
                    api(`/discrepancies/${d.id}/resolve`, {
                      reason: v.reason,
                      evidence_document_id: v.evidence,
                    }),
                  "Discrepancy disposition recorded against current evaluation.",
                );
              }}
            >
              <label className="field">
                <span>Resolution evidence</span>
                <select name="evidence" required>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.category} · {doc.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Discrepancy resolution reason</span>
                <textarea name="reason" minLength={10} required />
              </label>
              <button disabled={busy}>Resolve corrected discrepancy</button>
            </form>
          )}
        </div>
      ))}
      <details className="policy-note">
        <summary>Historical local fixture attestations</summary>
        <p>
          These older fixture records are retained for audit. New verification
          uses the independently persisted connected sandbox above.
        </p>
        {intel.attestations.map((a) => (
          <div className="document" key={a.id}>
            <strong>{a.outcome}</strong>
            <p>Source: {a.source} · LOCAL DEMO HMAC, not bank PKI</p>
            <small className="hash">Signature {a.signature}</small>
            <pre className="source-payload">
              {JSON.stringify(a.payload.observed, null, 2)}
            </pre>
          </div>
        ))}
      </details>
    </section>
  );
}
