import { useCallback, useEffect, useRef, useState } from "react";
import { api, exportCsv, type Schemas } from "./api";

type Task = {
  id: string;
  institution_id: string;
  deposit_id: string | null;
  case_id: string | null;
  category: string;
  state: string;
  episode: number;
  due_at: string;
  observed_at: string;
  policy_revision: number;
  detail: Record<string, unknown>;
  acknowledged_by: string | null;
  acknowledgement: string | null;
};
type Report = {
  items: Task[];
  total: number;
  counts: Record<string, number>;
  next_cursor: string | null;
  categories: string[];
};
type Config = {
  review_hours: number;
  verification_hours: number;
  discrepancy_hours: number;
  missing_document_hours: number;
  clearance_hours: number;
  escalation_hours: number;
  maturity_days: number[];
  supervisor_subject: string | null;
};
type Policy = {
  revision: number;
  configuration: Config;
  supervisor_candidates: string[];
};
type Notice = {
  id: string;
  kind: string;
  recipient: string;
  delivery: {
    state: string;
    attempts: number;
    last_error: string | null;
  } | null;
};
const label = (s: string) => s.replaceAll("_", " ").toLowerCase();
const hours = [
  "review_hours",
  "verification_hours",
  "discrepancy_hours",
  "missing_document_hours",
  "clearance_hours",
  "escalation_hours",
] as const;

export function OperationsReport({ onOpen }: { onOpen: (id: string) => void }) {
  const [institutions, setInstitutions] = useState<Schemas["InstitutionOut"][]>(
    [],
  );
  const [bindings, setBindings] = useState<
    { role: string; scope_id: string; scope_type: string }[]
  >([]);
  const [institution, setInstitution] = useState("");
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [category, setCategory] = useState("");
  const [state, setState] = useState("OPEN");
  const [deposit, setDeposit] = useState("");
  const [overdue, setOverdue] = useState(false);
  const [selected, setSelected] = useState<Task | null>(null);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const reportRevision = useRef(0);
  const policyInstitution = useRef(institution);
  policyInstitution.current = institution;
  const canManage = bindings.some(
    (b) =>
      b.role === "REVIEWER" &&
      b.scope_type === "INSTITUTION" &&
      b.scope_id === institution,
  );
  const params = new URLSearchParams({
    state,
    ...(institution ? { institution_id: institution } : {}),
    ...(category ? { category } : {}),
    ...(deposit ? { deposit_id: deposit } : {}),
    ...(overdue ? { overdue: "true" } : {}),
  }).toString();
  const refresh = useCallback(
    async (after = "") => {
      const revision = ++reportRevision.current;
      const result = await api<Report>(
        `/reports/interventions?${params}${after ? `&after=${after}` : ""}`,
      );
      if (revision !== reportRevision.current) return;
      setReport(result);
      setSelected((previous) =>
        previous
          ? (result.items.find((t) => t.id === previous.id) ?? null)
          : null,
      );
    },
    [params],
  );
  const loadPolicy = useCallback(async () => {
    if (!institution) return;
    try {
      const value = await api<Policy>(
        `/institutions/${institution}/operations-policy`,
      );
      if (policyInstitution.current === institution) setPolicy(value);
    } catch (error) {
      if (policyInstitution.current === institution) throw error;
    }
  }, [institution]);
  useEffect(() => {
    Promise.all([
      api<Schemas["InstitutionOut"][]>("/institutions"),
      api<{ bindings: typeof bindings }>("/me"),
    ])
      .then(([i, me]) => {
        setInstitutions(i);
        setBindings(me.bindings);
        setInstitution(i[0]?.id ?? "");
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    setSelected(null);
    refresh().catch((e) => setError(e.message));
    return () => {
      reportRevision.current++;
    };
  }, [refresh]);
  useEffect(() => {
    loadPolicy().catch((e) => setError(e.message));
  }, [loadPolicy]);
  useEffect(() => {
    if (!selected) return;
    let active = true;
    const poll = () =>
      api<Notice[]>(`/interventions/${selected.id}/notifications`)
        .then((value) => {
          if (active) setNotices(value);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    setNotices([]);
    poll();
    const timer = setInterval(poll, 3000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [selected?.id]);
  async function act(task: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await task();
      await refresh();
      await loadPolicy();
      setNotice(message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" aria-label="Intervention reports">
      <div className="section-head">
        <div>
          <h2>Interventions and escalation</h2>
          <p>
            Missing evidence, verification, reviews and unresolved cases.
            Deadlines are product policy. Only source-workflow completion
            resolves a task.
          </p>
        </div>
        <button
          onClick={() =>
            exportCsv(
              `/reports/interventions.csv?${params}`,
              "synthetic-interventions.csv",
            ).catch((e) => setError(e.message))
          }
        >
          Export intervention CSV
        </button>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      <div className="form-grid">
        <label className="field">
          <span>Intervention institution</span>
          <select
            aria-label="Intervention institution"
            value={institution}
            onChange={(e) => {
              if (e.target.value !== institution) {
                setInstitution(e.target.value);
                setPolicy(null);
                setSelected(null);
              }
            }}
          >
            <option value="">All assigned institutions</option>
            {institutions.map((i) => (
              <option key={i.id} value={i.id}>
                {i.legal_name} · {i.external_id}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Intervention category</span>
          <select
            aria-label="Intervention category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {report?.categories.map((c) => (
              <option key={c} value={c}>
                {label(c)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Intervention state</span>
          <select
            aria-label="Intervention state"
            value={state}
            onChange={(e) => setState(e.target.value)}
          >
            {["OPEN", "RESOLVED", "ALL"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Intervention deposit ID</span>
          <input
            value={deposit}
            onChange={(e) => setDeposit(e.target.value.trim())}
          />
        </label>
      </div>
      <label>
        <input
          type="checkbox"
          checked={overdue}
          onChange={(e) => setOverdue(e.target.checked)}
        />{" "}
        Overdue only (current real time)
      </label>
      <button
        disabled={busy}
        onClick={() => refresh().catch((e) => setError(e.message))}
      >
        Refresh interventions
      </button>
      {report && (
        <>
          <p>
            <strong>{report.total} matching interventions</strong> · totals
            cover the complete filtered scope; each page contains at most 50.
          </p>
          <div className="stats">
            {Object.entries(report.counts).map(([c, n]) => (
              <div key={c}>
                <span>{label(c)}</span>
                <strong>{n}</strong>
              </div>
            ))}
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Category / record</th>
                  <th>Deadline</th>
                  <th>State</th>
                  <th>Follow-up</th>
                </tr>
              </thead>
              <tbody>
                {report.items.map((t) => (
                  <tr key={t.id}>
                    <td>
                      {label(t.category)}
                      <small>{t.deposit_id ?? t.institution_id}</small>
                      {t.case_id && <small>Case {t.case_id}</small>}
                    </td>
                    <td>
                      {new Date(t.due_at).toLocaleString()}
                      <small>
                        Observed {new Date(t.observed_at).toLocaleString()} ·
                        policy {t.policy_revision}
                      </small>
                    </td>
                    <td>
                      {t.state}
                      <small>
                        {t.acknowledged_by
                          ? "Acknowledged; source still governs resolution"
                          : "Not acknowledged"}
                      </small>
                    </td>
                    <td>
                      <button
                        onClick={() => {
                          setSelected(t);
                          setNotices([]);
                        }}
                      >
                        Inspect follow-up {t.id.slice(0, 8)}
                      </button>
                      {t.deposit_id && (
                        <button onClick={() => onOpen(t.deposit_id!)}>
                          Open deposit evidence
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {report.next_cursor && (
            <button
              onClick={() =>
                refresh(report.next_cursor!).catch((e) => setError(e.message))
              }
            >
              Next intervention page
            </button>
          )}
        </>
      )}
      {selected && (
        <div className="policy-note">
          <h3>Follow-up details · {label(selected.category)}</h3>
          <pre>{JSON.stringify(selected.detail, null, 2)}</pre>
          {notices.map((n) => (
            <div key={n.id}>
              <p>
                {label(n.kind)} · recipient {n.recipient} · Email:{" "}
                {n.delivery?.state ?? "PENDING"} · {n.delivery?.attempts ?? 0}{" "}
                attempts
              </p>
              {n.delivery?.last_error && <small>{n.delivery.last_error}</small>}
              {canManage && n.delivery?.state === "DEAD_LETTER" && (
                <button
                  disabled={busy}
                  onClick={() =>
                    act(
                      () =>
                        api(`/notifications/${n.id}/retry`, {
                          expected_version: n.delivery!.attempts,
                        }),
                      "Operational email requeued; source and recipient access will be checked again.",
                    )
                  }
                >
                  Retry operational email
                </button>
              )}
            </div>
          ))}
          {canManage &&
            selected.state === "OPEN" &&
            !selected.acknowledged_by && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const reason = String(
                    new FormData(e.currentTarget).get("reason"),
                  );
                  act(async () => {
                    const t = await api<Task>(
                      `/interventions/${selected.id}/acknowledge`,
                      { reason },
                    );
                    setSelected(t);
                  }, "Follow-up acknowledged. Source conditions still require resolution.");
                }}
              >
                <label className="field">
                  <span>Follow-up acknowledgement</span>
                  <input
                    name="reason"
                    minLength={10}
                    maxLength={2000}
                    required
                  />
                </label>
                <button disabled={busy}>Acknowledge follow-up</button>
              </form>
            )}
        </div>
      )}
      {canManage && (
        <>
          <form
            className="form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              const value = String(new FormData(e.currentTarget).get("as_of"));
              act(
                () =>
                  api("/operations/scan", {
                    institution_id: institution,
                    as_of: value ? new Date(value).toISOString() : null,
                  }),
                "Intervention scan completed; reminders and escalation queued when due.",
              );
            }}
          >
            <label className="field">
              <span>Synthetic operations clock (optional)</span>
              <input name="as_of" type="datetime-local" />
            </label>
            <button disabled={busy}>Run intervention scan</button>
          </form>
          <p>
            Clock override is for fictional demonstrations only. It never
            advances financial approval or statutory eligibility.
          </p>
        </>
      )}
      {policy && canManage && (
        <details>
          <summary>Configure follow-up deadlines and supervisor</summary>
          <p>
            Versioned product service levels, not statutory deadlines. A
            supervisor must already hold an independent institution scope.
          </p>
          <form
            key={`${institution}:${policy.revision}`}
            className="form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              const v = Object.fromEntries(new FormData(e.currentTarget));
              const values = Object.fromEntries(
                hours.map((h) => [h, Number(v[h])]),
              );
              act(
                () =>
                  api(`/institutions/${institution}/operations-policy`, {
                    ...values,
                    maturity_days: String(v.days).split(",").map(Number),
                    supervisor_subject: v.supervisor || null,
                    reason: v.reason,
                    expected_revision: policy.revision,
                  }),
                "Operations policy saved with audit history.",
              );
            }}
          >
            {hours.map((h) => (
              <label className="field" key={h}>
                <span>{label(h)}</span>
                <input
                  name={h}
                  aria-label={label(h)}
                  type="number"
                  min={1}
                  max={8760}
                  required
                  defaultValue={policy.configuration[h]}
                />
              </label>
            ))}
            <label className="field">
              <span>Maturity reminder days</span>
              <input
                name="days"
                required
                defaultValue={policy.configuration.maturity_days.join(",")}
              />
            </label>
            <label className="field">
              <span>Escalation supervisor</span>
              <select
                name="supervisor"
                aria-label="Escalation supervisor"
                defaultValue={policy.configuration.supervisor_subject ?? ""}
              >
                <option value="">
                  Unassigned — escalations cannot be delivered
                </option>
                {Array.from(
                  new Set([
                    ...policy.supervisor_candidates,
                    ...(policy.configuration.supervisor_subject
                      ? [policy.configuration.supervisor_subject]
                      : []),
                  ]),
                ).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Operations policy reason</span>
              <input name="reason" required minLength={10} maxLength={2000} />
            </label>
            <button disabled={busy}>Save operations policy</button>
          </form>
        </details>
      )}
      {policy && !policy.configuration.supervisor_subject && (
        <p className="policy-note">
          Supervisor unassigned. Assign an independent scoped officer to receive
          overdue escalation; ordinary reminders still run.
        </p>
      )}
    </section>
  );
}
