import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { isDemo } from "./demo/config";

type Exchange = {
  id: string;
  operation: string;
  state: string;
  attempts: number;
  last_error: string | null;
  remote_id: string | null;
  ledger_id: string | null;
  result: {
    outcome: string;
    observed?: Record<string, unknown>;
    differences?: string[];
  } | null;
};
type Catalogue = {
  ledger: {
    id: string;
    institution_external_id: string;
    bank_code: string;
    reference_last4: string;
    amount_paise: number;
    status: string;
  }[];
};

export function IntegrationPanel({
  institutionId,
  depositId,
  version = 1,
  parentBusy = false,
  caseId,
  canRegistry = false,
  canBank = false,
  canRelease = false,
  onChange,
}: {
  institutionId: string;
  depositId?: string;
  version?: number;
  parentBusy?: boolean;
  caseId?: string;
  canRegistry?: boolean;
  canBank?: boolean;
  canRelease?: boolean;
  onChange?: () => Promise<void>;
}) {
  const [rows, setRows] = useState<Exchange[]>([]);
  const [ledger, setLedger] = useState("");
  const [behavior, setBehavior] = useState("NORMAL");
  const [catalogue, setCatalogue] = useState<Catalogue>({ ledger: [] });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const completed = useRef(new Set<string>());
  useEffect(() => {
    const fresh = rows.filter(
      (r) =>
        ["SUCCEEDED", "STALE", "DEAD_LETTER"].includes(r.state) &&
        !completed.current.has(r.id + r.state),
    );
    fresh.forEach((r) => completed.current.add(r.id + r.state));
    if (fresh.length) onChange?.().catch((e) => setError(e.message));
  }, [rows, onChange]);
  const refresh = useCallback(async () => {
    const filter: Record<string, string> = caseId
      ? { case_id: caseId }
      : depositId
        ? { deposit_id: depositId }
        : { institution_id: institutionId };
    setRows(
      await api<Exchange[]>(
        `/integration-requests?${new URLSearchParams(filter)}`,
      ),
    );
  }, [institutionId, depositId, caseId]);
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
    api<Catalogue>("/sandbox/catalogue")
      .then(setCatalogue)
      .catch((e) => setError(e.message));
    const timer = setInterval(
      () => refresh().catch((e) => setError(e.message)),
      2500,
    );
    return () => clearInterval(timer);
  }, [refresh]);
  const command = async (path: string, payload: unknown) => {
    if (parentBusy || busy) return;
    setBusy(true);
    setError("");
    try {
      await api(path, payload);
      await refresh();
      await onChange?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="panel" id={depositId ? "source-checks" : undefined}>
      <h3>
        {isDemo ? "Simulated source checks" : "Connected sandbox systems"}
      </h3>
      <p>
        {isDemo
          ? "Browser-only sample responses. No network exchange with a bank or AICTE occurs. Delay and retry choices illustrate outcomes; they do not test transport resilience."
          : "Real API exchanges with independently stored fictional bank and institution records. Sandbox evidence does not certify real bank authenticity or regulatory approval."}
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {(canBank || canRelease || canRegistry) && (
        <div className="form-grid">
          {(canBank || canRelease) && (
            <label className="field">
              <span>Independent bank ledger ID</span>
              <input
                aria-label="Independent bank ledger ID"
                list={`ledger-${depositId ?? caseId}`}
                value={ledger}
                onChange={(e) => setLedger(e.target.value)}
                placeholder="SB-FDR-001"
              />
              <datalist id={`ledger-${depositId ?? caseId}`}>
                {catalogue.ledger.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.institution_external_id} · {r.bank_code} · ending{" "}
                    {r.reference_last4} · {r.amount_paise} paise · {r.status}
                  </option>
                ))}
              </datalist>
            </label>
          )}
          <label className="field">
            <span>Sandbox transport behavior</span>
            <select
              aria-label="Sandbox transport behavior"
              value={behavior}
              onChange={(e) => setBehavior(e.target.value)}
            >
              <option value="NORMAL">Normal network exchange</option>
              <option value="DELAYED">Delayed response</option>
              <option value="TRANSIENT_FAILURE">
                One recoverable service failure
              </option>
            </select>
          </label>
          {canRegistry && (
            <button
              disabled={parentBusy || busy}
              onClick={() =>
                command(`/institutions/${institutionId}/registry-check`, {
                  behavior,
                })
              }
            >
              Check sandbox institution registry
            </button>
          )}
          {canBank && (
            <button
              disabled={parentBusy || busy || !ledger}
              onClick={() =>
                command(`/deposits/${depositId}/bank-check`, {
                  expected_version: version,
                  ledger_id: ledger,
                  behavior,
                })
              }
            >
              Request independent bank check
            </button>
          )}
          {canRelease && (
            <>
              <button
                disabled={parentBusy || busy}
                onClick={() =>
                  command(`/release-cases/${caseId}/sandbox-exchange`, {
                    expected_version: version,
                    behavior,
                  })
                }
              >
                Send case to AICTE sandbox
              </button>
              <button
                disabled={parentBusy || busy || !ledger}
                onClick={() =>
                  command(`/release-cases/${caseId}/sandbox-exchange`, {
                    expected_version: version,
                    ledger_id: ledger,
                    behavior,
                  })
                }
              >
                Reconcile with bank sandbox
              </button>
            </>
          )}
        </div>
      )}
      <div aria-live="polite">
        {rows.map((r) => (
          <article className="audit-row" key={r.id}>
            <div>
              <strong>
                {r.operation} · {r.state}
              </strong>
              <p>{r.result?.outcome ?? "Awaiting external sandbox result"}</p>
              <small>
                Request {r.id} · remote {r.remote_id ?? "pending"} ·{" "}
                {r.attempts} attempts · SANDBOX
              </small>
              {r.result?.differences?.length ? (
                <p className="error">
                  Conflicting fields: {r.result.differences.join(", ")}
                </p>
              ) : null}
              {r.result?.observed && (
                <details>
                  <summary>Independent source record</summary>
                  <pre style={{ whiteSpace: "pre-wrap" }}>
                    {JSON.stringify(r.result.observed, null, 2)}
                  </pre>
                </details>
              )}
              {r.last_error && (
                <p className="error">
                  {r.last_error} · processing remains incomplete
                </p>
              )}
              {r.state === "DEAD_LETTER" && (canBank || canRelease) && (
                <button
                  disabled={parentBusy || busy}
                  onClick={() =>
                    command(`/integration-requests/${r.id}/retry`, {
                      expected_version: r.attempts,
                    })
                  }
                >
                  Retry sandbox exchange
                </button>
              )}
            </div>
          </article>
        ))}
        {rows.length === 0 && <p>No sandbox exchange requested.</p>}
      </div>
    </section>
  );
}
