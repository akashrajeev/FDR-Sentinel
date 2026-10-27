import { useState } from "react";
import { api, download } from "../api";

export function DemoEvidence({
  id,
  release = false,
  run,
  busy,
}: {
  id: string;
  release?: boolean;
  run: (task: () => Promise<unknown>, message: string) => Promise<void>;
  busy: boolean;
}) {
  const [mode, setMode] = useState("DIGITAL");
  const [category, setCategory] = useState(
    release ? "SUPPORTING" : "DEPOSIT_PROOF",
  );
  return (
    <details className="policy-note">
      <summary>Explore upload, scanning, OCR and processing failures</summary>
      <p>
        All processing outcomes below are simulated. Download a synthetic PDF to
        try intake. Files are read locally; nothing is sent to a server.
        Unrecognized PDFs remain quarantined and receive no invented extraction.
      </p>
      <button
        disabled={busy}
        onClick={() =>
          run(() => download(id), "Synthetic upload template downloaded.")
        }
      >
        Download sample upload PDF
      </button>
      <form
        className="form-grid"
        onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget);
          run(
            () =>
              api(
                `/${release ? "release-cases" : "deposits"}/${id}/documents`,
                data,
              ),
            "Local sample intake recorded. Processing is simulated; no server upload occurred.",
          );
        }}
      >
        <label className="field">
          <span>Upload evidence category</span>
          <select
            name="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {[
              "DEPOSIT_PROOF",
              "REQUEST_LETTER",
              "AFFIDAVIT_6",
              "APPROVAL_LETTER",
              "SUPPORTING",
              "EXTERNAL_BODY_NOC",
              "CLOSURE_ORDER",
              "MERGER_ORDER",
              "CONVERSION_ORDER",
            ].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Synthetic PDF file (local only)</span>
          <input type="file" name="file" accept="application/pdf" required />
        </label>
        <button disabled={busy}>Try local PDF intake</button>
      </form>
      {!release && (
        <div className="form-grid">
          <label className="field">
            <span>Sample processing outcome</span>
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="DIGITAL">Digital PDF extraction</option>
              <option value="OCR_AI">
                Raster OCR and advisory AI proposal
              </option>
              <option value="PENDING">Quarantine then worker completion</option>
              <option value="WORKER_FAILURE">
                Worker failure and dead letter
              </option>
              <option value="MALWARE">Antivirus rejection (simulated)</option>
            </select>
          </label>
          <button
            disabled={busy}
            onClick={() =>
              run(
                () => api(`/deposits/${id}/demo-evidence`, { mode, category }),
                "Synthetic evidence scenario attached; original samples retained.",
              )
            }
          >
            Attach selected processing example
          </button>
        </div>
      )}
    </details>
  );
}
