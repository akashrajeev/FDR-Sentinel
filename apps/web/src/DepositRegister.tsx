import { useEffect, useRef, useState } from "react";
import { api, type Schemas } from "./api";
import { Icon } from "./Icon";

type Deposit = Schemas["DepositOut"];
export function DepositRegister({
  records,
  institutions,
  overview,
  onOpen,
  onViewAll,
}: {
  records: Deposit[];
  institutions: Schemas["InstitutionOut"][];
  overview: boolean;
  onOpen: (record: Deposit) => void;
  onViewAll: () => void;
}) {
  const [query, setQuery] = useState("");
  const [workflow, setWorkflow] = useState("");
  const [filters, setFilters] = useState({ q: "", workflow: "" });
  const [results, setResults] = useState<Deposit[]>([]);
  const [cursor, setCursor] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestRevision = useRef(0);
  async function search(after = "") {
    const revision = ++requestRevision.current;
    setLoading(true);
    setError("");
    try {
      const found = await api<Deposit[]>(
        `/search/deposits?${new URLSearchParams({ ...filters, limit: "50", ...(after ? { after } : {}) })}`,
      );
      if (revision !== requestRevision.current) return;
      setResults(found);
      setCursor(found.length === 50 ? found[found.length - 1].id : "");
    } catch (e) {
      if (revision !== requestRevision.current) return;
      setError((e as Error).message);
      setResults([]);
      setCursor("");
    } finally {
      if (revision === requestRevision.current) setLoading(false);
    }
  }
  useEffect(() => {
    if (!overview) search();
    return () => {
      requestRevision.current++;
    };
  }, [overview, filters, records]);
  const shown = overview ? records.slice(0, 6) : results;
  return (
    <section className="panel register-panel" aria-label="Deposit register">
      <div className="section-head">
        <div>
          <h2>Deposit register</h2>
          <p>
            {overview
              ? "Latest records · amounts in INR"
              : "Search your complete assigned scope · 50 records per page"}
          </p>
        </div>
        {overview && (
          <button className="text-button" onClick={onViewAll}>
            View all records <Icon name="arrow" />
          </button>
        )}
      </div>
      {!overview && (
        <form
          className="register-filters"
          onSubmit={(e) => {
            e.preventDefault();
            setFilters({ q: query, workflow });
          }}
        >
          <label className="field register-search">
            <span>Search deposit records</span>
            <input
              value={query}
              maxLength={100}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Institution, bank, record ID or reference last four"
            />
          </label>
          <label className="field">
            <span>Register review status</span>
            <select
              aria-label="Register review status"
              value={workflow}
              onChange={(e) => setWorkflow(e.target.value)}
            >
              <option value="">All review states</option>
              <option value="DRAFT">Draft</option>
              <option value="PENDING_SCRUTINY">Awaiting scrutiny</option>
              <option value="ACCEPTED">Registration accepted</option>
            </select>
          </label>
          <button disabled={loading} type="submit">
            Search register
          </button>
        </form>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {loading && (
        <p className="loading-status" role="status">
          Loading scoped deposit records…
        </p>
      )}
      {shown.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Record / institution</th>
                <th>Instrument / reference</th>
                <th className="numeric">Declared amount</th>
                <th>Maturity</th>
                <th>Review status</th>
                <th>
                  <span className="sr-only">Open record</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {shown.map((d) => (
                <tr key={d.id}>
                  <td>
                    <button className="record-link" onClick={() => onOpen(d)}>
                      {d.id.slice(0, 8).toUpperCase()}
                    </button>
                    <small>
                      {institutions.find((i) => i.id === d.institution_id)
                        ?.legal_name ??
                        `Institution · ${d.institution_id.slice(0, 8).toUpperCase()}`}
                    </small>
                  </td>
                  <td>
                    {d.deposit_type}
                    <small>
                      {d.bank_code} · ••{d.reference_last4}
                    </small>
                  </td>
                  <td className="amount numeric">
                    {new Intl.NumberFormat("en-IN", {
                      style: "currency",
                      currency: "INR",
                      maximumFractionDigits: 0,
                    }).format(d.amount_paise / 100)}
                  </td>
                  <td>{d.maturity_date ?? "Not applicable"}</td>
                  <td>
                    <span
                      className={`badge ${d.workflow === "ACCEPTED" ? "blue" : ""}`}
                    >
                      {d.workflow.replaceAll("_", " ")}
                    </span>
                  </td>
                  <td>
                    <button
                      className="row-open"
                      aria-label={`Open deposit ${d.id.slice(0, 8).toUpperCase()}`}
                      onClick={() => onOpen(d)}
                    >
                      <Icon name="arrow" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !loading &&
        !error && (
          <div className="empty">
            <Icon name="deposits" />
            <h3>
              {query || workflow
                ? "No matching records"
                : "Your deposit register starts here"}
            </h3>
            <p>
              {query || workflow
                ? "Adjust the search or review status to find another record."
                : "Onboard an institution, register its obligation and upload a synthetic deposit proof."}
            </p>
          </div>
        )
      )}
      {!overview && (
        <div className="register-pagination">
          <span>{shown.length} records on this page</span>
          <div>
            <button disabled={loading} onClick={() => search()}>
              First page
            </button>
            <button
              disabled={loading || !cursor}
              onClick={() => search(cursor)}
            >
              Next records
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
