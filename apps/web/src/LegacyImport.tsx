import { useState } from "react";
import { api } from "./api";
import { isDemo } from "./demo/config";

type Preview = {
  sha256: string;
  rows: number;
  declared_total_paise: string;
  note: string;
};
export function LegacyImport({ onChange }: { onChange: () => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [bundledPreview, setBundledPreview] = useState(false);
  const run = async (commit = false, bundled = false) => {
    const sample = commit ? bundledPreview : bundled;
    if (!file && !sample) return;
    setBusy(true);
    setError("");
    setNotice("");
    const body = new FormData();
    if (file) body.append("file", file);
    if (commit && preview) body.append("expected_sha256", preview.sha256);
    try {
      if (commit) {
        const result = await api<{ rows: number }>(
          sample ? "/legacy-import/demo-commit" : "/legacy-import/commit",
          sample ? { expected_sha256: preview?.sha256 } : body,
        );
        setNotice(
          `${result.rows} DRAFT records imported atomically. Upload evidence and submit them for scrutiny.`,
        );
        setPreview(null);
        await onChange();
      } else {
        setPreview(
          await api<Preview>(
            sample ? "/legacy-import/demo-preview" : "/legacy-import/preview",
            sample ? {} : body,
          ),
        );
        setBundledPreview(sample);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const template = () => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(
      new Blob(
        [
          "obligation_id,deposit_type,bank_code,reference,amount_paise,issue_date,maturity_date,deposited_on\n",
        ],
        { type: "text/csv" },
      ),
    );
    link.download = "synthetic-legacy-template.csv";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  };
  return (
    <section className="panel">
      <h2>Validated legacy deposit import</h2>
      <p>
        UTF-8 CSV, at most 200 rows / 200 KiB. Use an obligation you own,
        fictional SYN- references and SYN- or SYNTHETIC- bank codes. Amounts are
        integer paise. FDR dates and RTGS/online deposit dates are validated
        separately.
      </p>
      <button onClick={template}>Download CSV header template</button>
      {isDemo && (
        <button
          onClick={async () => {
            try {
              const rows = await api<{ id: string }[]>("/obligations");
              const link = document.createElement("a");
              link.href = URL.createObjectURL(
                new Blob(
                  [
                    `obligation_id,deposit_type,bank_code,reference,amount_paise,issue_date,maturity_date,deposited_on\n${rows[0].id},FDR,SYN-BANK,SYN-CSV-0088,350000000,2016-10-01,2026-10-01,\n`,
                  ],
                  { type: "text/csv" },
                ),
              );
              link.download = "synthetic-example.csv";
              link.click();
              setTimeout(() => URL.revokeObjectURL(link.href), 1000);
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          Download synthetic CSV example
        </button>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      {isDemo && (
        <p>
          Preview the bundled example or select a synthetic CSV. Validation runs
          locally; no file is sent to a server.
        </p>
      )}
      <label className="field">
        <span>Legacy CSV file</span>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setPreview(null);
            setNotice("");
          }}
        />
      </label>
      <button disabled={busy || !file} onClick={() => run()}>
        Validate import preview
      </button>
      {isDemo && (
        <button disabled={busy} onClick={() => run(false, true)}>
          Preview bundled legacy sample
        </button>
      )}
      {preview && (
        <div className="policy-note">
          <h3>Import preview</h3>
          <p>
            {preview.rows} validated rows · declared total{" "}
            {preview.declared_total_paise} paise.
          </p>
          <p>{preview.note}</p>
          <small className="hash">
            {bundledPreview ? "Sample identifier" : "CSV SHA256"}{" "}
            {preview.sha256}
          </small>
          <button disabled={busy} onClick={() => run(true)}>
            Commit validated DRAFT records
          </button>
        </div>
      )}
    </section>
  );
}
