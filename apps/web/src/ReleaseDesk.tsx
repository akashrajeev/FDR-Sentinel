import { useCallback, useEffect, useState } from "react";
import { api, download, type Schemas } from "./api";

type Case = Schemas["ReleaseOut"];
type Deposit = Schemas["DepositOut"];
type Binding = { role: string; scope_type: string; scope_id: string };
type Relation = {
  id: string;
  institution_id: string;
  old_deposit_id: string;
  new_deposit_id: string;
  kind: string;
  state: string;
  version: number;
};
type Notification = {
  id: string;
  deposit_id: string;
  detail: { days_remaining: number; threshold: number; as_of: string };
};
const label = (value: string) => value.replaceAll("_", " ");
const short = (value: string) => value.slice(0, 8).toUpperCase();
const val = (form: HTMLFormElement) =>
  Object.fromEntries(new FormData(form).entries()) as Record<string, string>;

export function ReleaseDesk({
  records,
  bindings,
}: {
  records: Deposit[];
  bindings: Binding[];
}) {
  const [cases, setCases] = useState<Case[]>([]);
  const [selected, setSelected] = useState<Case | null>(null);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const has = (role: string, id: string, scope = "INSTITUTION") =>
    bindings.some(
      (b) => b.role === role && b.scope_type === scope && b.scope_id === id,
    );
  const refresh = useCallback(async () => {
    const [a, b, c] = await Promise.all([
      api<Case[]>("/release-cases"),
      api<Relation[]>("/replacements"),
      api<Notification[]>("/notifications"),
    ]);
    setCases(a);
    setRelations(b);
    setNotifications(c);
    if (selected) setSelected(a.find((c) => c.id === selected.id) ?? selected);
  }, [selected?.id]);
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
    const timer = setInterval(
      () => refresh().catch((e) => setError(e.message)),
      4000,
    );
    return () => clearInterval(timer);
  }, [refresh]);
  const act = async (task: () => Promise<unknown>, message: string) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await task();
      await refresh();
      setNotice(message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const command = (path: string, body: Record<string, unknown> = {}) =>
    act(async () => {
      const next = await api<Case>(`/release-cases/${selected!.id}/${path}`, {
        expected_version: selected!.version,
        ...body,
      });
      setSelected(next);
    }, "Human action committed with audit evidence.");
  const deposit = records.find((d) => d.id === selected?.deposit_id);
  const maker = selected && has("MAKER", selected.institution_id);
  const reviewer = selected && has("REVIEWER", selected.institution_id);
  const approver = selected && has("APPROVER", selected.institution_id);
  const issuer = selected && has("ISSUER", selected.institution_id);
  const evidenceOptions = selected?.documents
    .filter((d) => d.status === "READY")
    .map((d) => (
      <option value={String(d.id)} key={String(d.id)}>
        {label(String(d.category))} · {short(String(d.id))}
      </option>
    ));
  return (
    <>
      <div className="policy-note">
        SYNTHETIC WORKFLOW ONLY · APH 6.46 provisional · No bank settlement,
        official NOC or payment authority. Maturity never authorizes release.
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      {!selected ? (
        <>
          <section className="panel">
            <div className="section-head">
              <div>
                <h2>Cross-bureau release desk</h2>
                <p>
                  Scanned evidence → independent clearances → human approval →
                  synthetic output
                </p>
              </div>
              <span className="badge">{cases.length} CASES</span>
            </div>
            {cases.length > 0 ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Case / deposit</th>
                      <th>Reason</th>
                      <th>Workflow</th>
                      <th>Open blockers</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {cases.map((c) => (
                      <tr key={c.id} onClick={() => setSelected(c)}>
                        <td>
                          <strong>{short(c.id)}</strong>
                          <small>{short(c.deposit_id)}</small>
                        </td>
                        <td>{label(c.reason)}</td>
                        <td>
                          <span className="badge">{label(c.state)}</span>
                        </td>
                        <td>{c.blockers.length}</td>
                        <td>↗</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty">
                <h3>No release cases in your scope</h3>
                <p>
                  Start from an accepted deposit. The API enforces evidence,
                  bureau and signatory gates.
                </p>
              </div>
            )}
            {records.some(
              (d) =>
                d.workflow === "ACCEPTED" && has("MAKER", d.institution_id),
            ) && (
              <form
                className="form-grid"
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = val(e.currentTarget);
                  act(async () => {
                    setSelected(
                      await api<Case>("/release-cases", {
                        deposit_id: v.deposit_id,
                        reason: v.reason,
                      }),
                    );
                  }, "Synthetic release case created. Upload its supporting evidence.");
                }}
              >
                <label className="field">
                  <span>Accepted deposit</span>
                  <select name="deposit_id" required>
                    {records
                      .filter(
                        (d) =>
                          d.workflow === "ACCEPTED" &&
                          has("MAKER", d.institution_id) &&
                          d.lifecycle_status !== "REPLACED" &&
                          !cases.some((c) => c.deposit_id === d.id),
                      )
                      .map((d) => (
                        <option value={d.id} key={d.id}>
                          {short(d.id)} · {d.deposit_type} ·{" "}
                          {d.maturity_date ?? "No FDR maturity"}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="field">
                  <span>Release reason</span>
                  <select name="reason">
                    {[
                      "TERM_COMPLETED",
                      "CLOSURE",
                      "MERGER",
                      "CONVERSION",
                      "OTHER",
                    ].map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                </label>
                <button className="primary" disabled={busy}>
                  Create release case
                </button>
              </form>
            )}
          </section>
          <section className="panel">
            <h2>Maturity monitor</h2>
            <p>
              90 / 30 / 7 day reminders are product policy. Alerts persist
              in-app; no external email/SMS is sent.
            </p>
            {bindings.some((b) => b.role === "REVIEWER") && (
              <form
                className="form-grid"
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = val(e.currentTarget);
                  act(
                    () => api("/monitoring/run", { as_of: v.as_of || null }),
                    "Maturity states and deduplicated in-app alerts updated.",
                  );
                }}
              >
                <label className="field">
                  <span>Synthetic demo clock override (optional)</span>
                  <input name="as_of" type="date" />
                </label>
                <button disabled={busy}>Run maturity monitor</button>
              </form>
            )}
            {notifications.slice(0, 12).map((n) => (
              <div className="audit-row" key={n.id}>
                <span className="status-dot" />
                <div>
                  <strong>
                    {short(n.deposit_id)} ·{" "}
                    {n.detail.days_remaining <= 0
                      ? "Matured"
                      : `${n.detail.days_remaining} days remaining`}
                  </strong>
                  <small>
                    As of {n.detail.as_of} · {n.detail.threshold}-day band ·
                    persisted in-app
                  </small>
                </div>
              </div>
            ))}
          </section>
          <section className="panel">
            <h2>Renewal & replacement lineage</h2>
            <p>
              Originals are preserved. Later accepted replacement evidence and
              an independent officer’s policy basis are required.
            </p>
            {records.filter(
              (d) =>
                has("MAKER", d.institution_id) && d.workflow === "ACCEPTED",
            ).length >= 2 && (
              <form
                className="form-grid"
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = val(e.currentTarget);
                  const old = records.find((d) => d.id === v.old)!;
                  const next = records.find((d) => d.id === v.next)!;
                  act(async () => {
                    const detail = await api<Schemas["DepositDetail"]>(
                      `/deposits/${next.id}`,
                    );
                    const proof = detail.documents.find(
                      (d) => d.status === "READY" && d.active,
                    );
                    if (!proof)
                      throw new Error("Replacement READY evidence required");
                    await api("/replacements", {
                      old_deposit_id: old.id,
                      new_deposit_id: next.id,
                      expected_old_version: old.version,
                      kind: v.kind,
                      rationale: v.rationale,
                      evidence_document_id: proof.id,
                    });
                  }, "Replacement request recorded; officer authorization required.");
                }}
              >
                <label className="field">
                  <span>Original deposit</span>
                  <select name="old">
                    {records
                      .filter(
                        (d) =>
                          d.workflow === "ACCEPTED" &&
                          has("MAKER", d.institution_id),
                      )
                      .map((d) => (
                        <option value={d.id} key={d.id}>
                          {short(d.id)} · {d.maturity_date}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="field">
                  <span>New accepted deposit</span>
                  <select name="next">
                    {records
                      .filter(
                        (d) =>
                          d.workflow === "ACCEPTED" &&
                          has("MAKER", d.institution_id),
                      )
                      .map((d) => (
                        <option value={d.id} key={d.id}>
                          {short(d.id)} · {d.maturity_date}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="field">
                  <span>Relationship</span>
                  <select name="kind">
                    <option>REPLACEMENT</option>
                    <option>RENEWAL</option>
                    <option>AUTO_RENEWAL_RECORDED</option>
                  </select>
                </label>
                <label className="field">
                  <span>Evidence rationale</span>
                  <textarea name="rationale" minLength={20} required />
                </label>
                <button disabled={busy}>Request lineage authorization</button>
              </form>
            )}
            {relations.map((r) => (
              <div className="document" key={r.id}>
                <div className="section-head">
                  <strong>
                    {short(r.old_deposit_id)} → {short(r.new_deposit_id)} ·{" "}
                    {label(r.kind)}
                  </strong>
                  <span className="badge">{r.state}</span>
                </div>
                {r.state === "REQUESTED" &&
                  has("REVIEWER", r.institution_id) && (
                    <form
                      className="form-grid"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const v = val(e.currentTarget);
                        act(
                          () =>
                            api(`/replacements/${r.id}/approve`, {
                              expected_version: r.version,
                              policy_basis: v.policy_basis,
                            }),
                          "Replacement authorized; original retained.",
                        );
                      }}
                    >
                      <label className="field">
                        <span>Officer policy basis</span>
                        <textarea name="policy_basis" minLength={30} required />
                      </label>
                      <button disabled={busy}>Authorize replacement</button>
                    </form>
                  )}
              </div>
            ))}
          </section>
        </>
      ) : (
        <>
          <div className="section-head">
            <div>
              <h2>
                Case {short(selected.id)} · {deposit?.deposit_type}
              </h2>
              <p>
                {label(selected.reason)} · input {selected.input_revision} ·
                version {selected.version}
              </p>
            </div>
            <button onClick={() => setSelected(null)}>← Release cases</button>
          </div>
          <div className="case-steps">
            {[
              "DRAFT",
              "CLEARANCES_PENDING",
              "APPROVAL_REVIEW",
              "APPROVED_SYNTHETIC",
              "ISSUED_SYNTHETIC",
            ].map((s, i) => (
              <div key={s} className={selected.state === s ? "current" : ""}>
                <span>{i + 1}</span>
                {label(s)}
              </div>
            ))}
          </div>
          {selected.blockers.length > 0 && (
            <div className="blocker-panel">
              <h2>Release is blocked</h2>
              {selected.blockers.map((b, i) => (
                <p key={i}>● {b}</p>
              ))}
            </div>
          )}
          <div className="detail-grid">
            <section className="panel">
              <h2>Required evidence</h2>
              <p>
                Deposit proof, request letter, Affidavit 6 and latest LoA/EoA.
                Exception branches require an additional order/evidence.
              </p>
              {selected.documents.map((d) => (
                <div className="document" key={String(d.id)}>
                  <div className="section-head">
                    <strong>{label(String(d.category))}</strong>
                    <span className="badge">{String(d.status)}</span>
                  </div>
                  <small className="hash">SHA256 {String(d.sha256)}</small>
                  {d.status === "READY" && (
                    <button
                      onClick={() =>
                        act(() => download(String(d.id)), "Download audited.")
                      }
                    >
                      Download evidence
                    </button>
                  )}
                </div>
              ))}
              {maker && selected.state === "DRAFT" && (
                <form
                  className="upload-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const data = new FormData(e.currentTarget);
                    act(
                      () =>
                        api(`/release-cases/${selected.id}/documents`, data),
                      "Evidence quarantined for actual scanning.",
                    );
                  }}
                >
                  <label className="field">
                    <span>Release evidence category</span>
                    <select name="category">
                      {[
                        "REQUEST_LETTER",
                        "AFFIDAVIT_6",
                        "APPROVAL_LETTER",
                        "CLOSURE_ORDER",
                        "MERGER_ORDER",
                        "CONVERSION_ORDER",
                        "SUPPORTING",
                        "EXTERNAL_BODY_NOC",
                      ].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Release PDF</span>
                    <input
                      name="file"
                      type="file"
                      accept="application/pdf"
                      required
                    />
                  </label>
                  <button disabled={busy}>Upload release evidence</button>
                  <button
                    type="button"
                    className="primary"
                    disabled={busy}
                    onClick={() => command("submit")}
                  >
                    Submit to bureaus
                  </button>
                </form>
              )}
            </section>
            <section className="panel">
              <h2>Independent bureau clearances</h2>
              {selected.required_bureaus.map((bureau) => {
                const decision = selected.clearances.find(
                  (c) => c.bureau === bureau,
                );
                return (
                  <div className="document" key={bureau}>
                    <div className="section-head">
                      <strong>{bureau}</strong>
                      <span className="badge">
                        {String(decision?.decision ?? "PENDING")}
                      </span>
                    </div>
                    {decision && (
                      <small>
                        Actor {String(decision.actor)} ·{" "}
                        {String(decision.reason)}
                      </small>
                    )}
                    {!decision &&
                      selected.state === "CLEARANCES_PENDING" &&
                      has("CLEARANCE", bureau, "BUREAU") && (
                        <form
                          className="review-form"
                          onSubmit={(e) => {
                            e.preventDefault();
                            const v = val(e.currentTarget);
                            command(`clearances/${bureau}/decision`, {
                              decision: v.decision,
                              reason: v.reason,
                              evidence_document_id: v.evidence,
                            });
                          }}
                        >
                          <label className="field">
                            <span>{bureau} disposition</span>
                            <select name="decision">
                              <option>CLEARED</option>
                              <option>REJECTED</option>
                            </select>
                          </label>
                          <label className="field">
                            <span>{bureau} evidence</span>
                            <select name="evidence" required>
                              {evidenceOptions}
                            </select>
                          </label>
                          <label className="field">
                            <span>{bureau} reason</span>
                            <textarea name="reason" minLength={10} required />
                          </label>
                          <button disabled={busy}>
                            Record {bureau} decision
                          </button>
                        </form>
                      )}
                  </div>
                );
              })}
              {reviewer &&
                ["CLEARANCES_PENDING", "APPROVAL_REVIEW"].includes(
                  selected.state,
                ) && (
                  <form
                    className="review-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      command("return", {
                        reason: val(e.currentTarget).reason,
                      });
                    }}
                  >
                    <label className="field">
                      <span>Return for correction reason</span>
                      <textarea name="reason" minLength={10} required />
                    </label>
                    <button disabled={busy}>Return release case</button>
                  </form>
                )}
            </section>
          </div>
          <section className="panel">
            <h2>Holds & final authorization</h2>
            {selected.holds.map((h) => (
              <div className="document" key={String(h.id)}>
                <strong>{String(h.reason)}</strong>
                <p>
                  {h.active
                    ? "ACTIVE HOLD"
                    : `Resolved: ${String(h.resolution)}`}
                </p>
                {!!h.active && approver && (
                  <form
                    className="form-grid"
                    onSubmit={(e) => {
                      e.preventDefault();
                      const v = val(e.currentTarget);
                      command(`holds/${h.id}/resolve`, {
                        resolution: v.resolution,
                        evidence_document_id: v.evidence,
                      });
                    }}
                  >
                    <label className="field">
                      <span>Hold resolution evidence</span>
                      <select name="evidence" required>
                        {evidenceOptions}
                      </select>
                    </label>
                    <label className="field">
                      <span>Resolution and authority</span>
                      <textarea name="resolution" minLength={20} required />
                    </label>
                    <button disabled={busy}>Resolve with evidence</button>
                  </form>
                )}
              </div>
            ))}
            {(reviewer || approver) &&
              selected.state !== "ISSUED_SYNTHETIC" && (
                <form
                  className="form-grid"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const v = val(e.currentTarget);
                    command("holds", { reason: v.reason, kind: v.kind });
                  }}
                >
                  <label className="field">
                    <span>Add blocking hold</span>
                    <textarea name="reason" minLength={10} required />
                  </label>
                  <label className="field">
                    <span>Hold category</span>
                    <select name="kind" aria-label="Hold category">
                      <option>MANUAL</option>
                      <option>FINANCIAL_EMBEZZLEMENT</option>
                      <option>LEGAL</option>
                      <option>REGULATORY_EXCEPTION</option>
                    </select>
                  </label>
                  <button disabled={busy}>Record hold</button>
                </form>
              )}
            {approver &&
              ["CLEARANCES_PENDING", "APPROVAL_REVIEW"].includes(
                selected.state,
              ) && (
                <form
                  className="review-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    command("approve", {
                      regulatory_basis: val(e.currentTarget).basis,
                      synthetic_acknowledgement: true,
                    });
                  }}
                >
                  <label className="field">
                    <span>Independent approver regulatory basis</span>
                    <textarea name="basis" minLength={30} required />
                  </label>
                  <label className="check">
                    <input type="checkbox" required />I reviewed applicability,
                    term, evidence and all required clearances. This result is
                    synthetic only.
                  </label>
                  <button disabled={busy} className="primary">
                    Attempt synthetic approval
                  </button>
                </form>
              )}
            {issuer && selected.state === "APPROVED_SYNTHETIC" && (
              <button
                disabled={busy}
                className="primary"
                onClick={() => command("issue-document")}
              >
                Issue synthetic{" "}
                {["FDR", "RPGF"].includes(deposit?.deposit_type ?? "")
                  ? "NOC"
                  : "sanction order"}
              </button>
            )}
            {selected.output_document_id && (
              <div className="notice">
                <h2>Synthetic result issued</h2>
                <p>No financial release or bank settlement occurred.</p>
                <button
                  onClick={() =>
                    act(
                      () => download(selected.output_document_id!),
                      "Synthetic output downloaded and audited.",
                    )
                  }
                >
                  Download synthetic result
                </button>
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}
