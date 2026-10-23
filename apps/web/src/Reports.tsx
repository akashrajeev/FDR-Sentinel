import { useEffect, useState } from "react";
import { api, exportCsv, type Schemas } from "./api";

export function Reports() {
  const [summary, setSummary] = useState<Schemas["SummaryOut"] | null>(null);
  const [records, setRecords] = useState<Schemas["DepositOut"][]>([]);
  const [query, setQuery] = useState("");
  const [workflow, setWorkflow] = useState("");
  const [error, setError] = useState("");
  const [cursor, setCursor] = useState("");
  const search = async (after = "") => {
    setError("");
    try {
      const result = await api<Schemas["DepositOut"][]>(
        `/search/deposits?${new URLSearchParams({ q: query, workflow, limit: "50", ...(after ? { after } : {}) })}`,
      );
      setRecords(result);
      setCursor(result.length === 50 ? result[result.length - 1].id : "");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    api<Schemas["SummaryOut"]>("/dashboard/summary")
      .then(setSummary)
      .catch((e) => setError(e.message));
    api<Schemas["DepositOut"][]>("/search/deposits")
      .then((result) => {
        setRecords(result);
        setCursor(result.length === 50 ? result[result.length - 1].id : "");
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <section className="panel">
        <div className="section-head">
          <div>
            <h2>Scoped operations report</h2>
            <p>
              Server-calculated totals across your complete scope; search
              results are paginated.
            </p>
          </div>
          <button onClick={() => exportCsv().catch((e) => setError(e.message))}>
            Export scoped CSV
          </button>
        </div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {summary && (
          <>
            <div className="stats">
              <div>
                <span>FDRs matured from dates</span>
                <strong>{summary.fdr_matured_from_dates}</strong>
                <small>As of {summary.as_of} · no automatic release</small>
              </div>
              <div>
                <span>Due within 90 days</span>
                <strong>{summary.fdr_upcoming_90_days}</strong>
                <small>Product reminder policy</small>
              </div>
              <div>
                <span>Replaced records retained</span>
                <strong>{summary.stored_lifecycle_counts.REPLACED ?? 0}</strong>
                <small>Source and lineage preserved</small>
              </div>
              <div>
                <span>Actual financial releases</span>
                <strong>0</strong>
                <small>External banks / AICTE not connected</small>
              </div>
            </div>
            <div className="report-bars">
              {Object.entries(summary.workflow_counts).map(([name, count]) => (
                <div key={name}>
                  <span>{name.replaceAll("_", " ")}</span>
                  <div
                    style={{
                      width: `${Math.max(2, (count / Math.max(1, ...Object.values(summary.workflow_counts))) * 100)}%`,
                    }}
                  />
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
            <p>
              Completed synthetic case timing:{" "}
              {String(summary.completed_synthetic_case_time.samples)} samples ·
              median{" "}
              {String(
                summary.completed_synthetic_case_time.median_seconds ??
                  "not measured",
              )}{" "}
              seconds. Audit timestamps include automated demo actor switching,
              not human review turnaround. No manual baseline or savings claim.
            </p>
            <small>
              Current policy checksum {summary.policy_revision} ·{" "}
              {summary.policy_status}
            </small>
          </>
        )}
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            search();
          }}
        >
          <label className="field">
            <span>
              Search institution, bank, record ID or reference last four
            </span>
            <input value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <label className="field">
            <span>Workflow filter</span>
            <select
              aria-label="Workflow filter"
              value={workflow}
              onChange={(e) => setWorkflow(e.target.value)}
            >
              <option value="">All workflows</option>
              <option>DRAFT</option>
              <option>PENDING_SCRUTINY</option>
              <option>ACCEPTED</option>
            </select>
          </label>
          <button className="primary">Search scoped records</button>
        </form>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Record</th>
                <th>Type / bank</th>
                <th>Declared amount INR</th>
                <th>Review</th>
                <th>Verification</th>
                <th>Maturity</th>
              </tr>
            </thead>
            <tbody>
              {records.map((d) => (
                <tr key={d.id}>
                  <td>
                    {d.id.slice(0, 8).toUpperCase()}
                    <small>··{d.reference_last4}</small>
                  </td>
                  <td>
                    {d.deposit_type}
                    <small>{d.bank_code}</small>
                  </td>
                  <td>
                    {new Intl.NumberFormat("en-IN", {
                      style: "currency",
                      currency: "INR",
                    }).format(d.amount_paise / 100)}
                  </td>
                  <td>{d.workflow.replaceAll("_", " ")}</td>
                  <td>{d.verification_status.replaceAll("_", " ")}</td>
                  <td>{d.maturity_date ?? "Not applicable"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {cursor && (
          <button onClick={() => search(cursor)}>Next 50 records →</button>
        )}
      </section>
    </>
  );
}
