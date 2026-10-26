import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type { User } from "oidc-client-ts";
import { api, download, identity, setToken, type Schemas } from "./api";
import "./style.css";
import { ReleaseDesk } from "./ReleaseDesk";
import { IntelligencePanel } from "./IntelligencePanel";
import { Reports } from "./Reports";
import { IntegrationPanel } from "./IntegrationPanel";

type Deposit = Schemas["DepositOut"];
type Detail = Schemas["DepositDetail"];
type Institution = Schemas["InstitutionOut"];
type Obligation = Schemas["ObligationOut"];
type Me = {
  subject: string;
  bindings: { role: string; scope_type: string; scope_id: string }[];
};
const money = (paise: number | string) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(
    typeof paise === "string" ? (BigInt(paise) + 50n) / 100n : paise / 100,
  );
const short = (value: string) => value.slice(0, 8).toUpperCase();
const display = (value: string) => value.replaceAll("_", " ");
function Badge({ value }: { value: string }) {
  return (
    <span
      className={`badge ${["FAIL", "REJECTED", "FAILED"].includes(value) ? "red" : ["READY", "ACCEPTED", "MANUALLY_REVIEWED"].includes(value) ? "green" : ""}`}
    >
      {display(value)}
    </span>
  );
}
function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
function values(form: HTMLFormElement) {
  return Object.fromEntries(new FormData(form).entries()) as Record<
    string,
    string
  >;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [tab, setTab] = useState("Overview");
  const [records, setRecords] = useState<Deposit[]>([]);
  const [summary, setSummary] = useState<Schemas["SummaryOut"] | null>(null);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [selected, setSelected] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState("Checking services");
  const [audit, setAudit] = useState<Schemas["AuditOut"][]>([]);
  const [form, setForm] = useState("");
  const [kind, setKind] = useState("FDR");

  useEffect(() => {
    (async () => {
      try {
        const authenticated =
          window.location.pathname === "/callback"
            ? await identity.signinRedirectCallback()
            : await identity.getUser();
        if (window.location.pathname === "/callback")
          history.replaceState({}, "", "/");
        if (authenticated && !authenticated.expired) {
          setToken(authenticated.access_token);
          setUser(authenticated);
        }
      } catch (e) {
        setError(String(e));
      }
      setAuthReady(true);
    })();
    const expired = () => {
      setUser(null);
      setToken("");
      setNotice("Session expired. Sign in again.");
    };
    identity.events.addAccessTokenExpired(expired);
    return () => identity.events.removeAccessTokenExpired(expired);
  }, []);

  const refresh = useCallback(async () => {
    if (!user) return;
    const [a, b, c, d, e, s] = await Promise.all([
      api<Me>("/me"),
      api<Deposit[]>("/deposits"),
      api<Institution[]>("/institutions"),
      api<Obligation[]>("/obligations"),
      api<Schemas["AuditOut"][]>("/audit-events"),
      api<Schemas["SummaryOut"]>("/dashboard/summary"),
    ]);
    setMe(a);
    setRecords(b);
    setInstitutions(c);
    setObligations(d);
    setAudit(e);
    setSummary(s);
    const h = await fetch("/api/v1/health/ready").then((r) => r.json());
    setHealth(display(h.status));
  }, [user]);
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, [refresh]);
  useEffect(() => {
    if (!selected) return;
    const id = selected.id;
    const timer = setInterval(
      () =>
        api<Detail>(`/deposits/${id}`)
          .then(setSelected)
          .catch((e) => setError(e.message)),
      4000,
    );
    return () => clearInterval(timer);
  }, [selected?.id]);

  const perform = async (task: () => Promise<unknown>, message: string) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await task();
      await refresh();
      if (selected) setSelected(await api<Detail>(`/deposits/${selected.id}`));
      setNotice(message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const open = (record: Deposit) =>
    perform(async () => {
      setSelected(await api<Detail>(`/deposits/${record.id}`));
      setForm("");
    }, "");
  const maker = (id: string) =>
    !!me?.bindings.some((b) => b.role === "MAKER" && b.scope_id === id);
  const reviewer = (id: string) =>
    !!me?.bindings.some((b) => b.role === "REVIEWER" && b.scope_id === id);
  const command = (action: string, extra: Record<string, unknown> = {}) =>
    perform(
      () =>
        api(`/deposits/${selected!.id}/${action}`, {
          expected_version: selected!.version,
          ...extra,
        }),
      action === "submit"
        ? "Submitted for officer scrutiny, including any unresolved findings."
        : "Action recorded with audit evidence.",
    );

  if (!authReady)
    return <div className="splash">Preparing secure workspace…</div>;
  if (!user)
    return (
      <div className="login">
        <div className="login-main">
          <div className="wordmark">
            <span className="logo">S</span> FDR Sentinel
          </div>
          <p className="eyebrow">SIH 2026 · SIH26265</p>
          <h1>
            Every deposit.
            <br />
            Every decision.
            <br />
            <em>Accounted for.</em>
          </h1>
          <p>
            One workspace for institutional security deposits, evidence and
            accountable officer review.
          </p>
          <button onClick={() => identity.signinRedirect()} className="primary">
            Sign in securely <span>↗</span>
          </button>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <small>Keycloak OIDC · Authorization code + PKCE</small>
        </div>
        <div className="login-side">
          <div className="orbit">
            S
            <span className="orbit-label">EVIDENCE → SCRUTINY → CLEARANCE</span>
          </div>
          <div>
            <Badge value="SYNTHETIC_LOCAL" />
            <h2>
              Built around evidence.
              <br />
              Governed by people.
            </h2>
            <p>
              Bank and AICTE sandbox APIs use fictional records. Official
              systems are not connected. Policy fixtures are provisional. No
              actual financial release.
            </p>
          </div>
        </div>
      </div>
    );

  return (
    <div className="shell">
      <aside>
        <div className="wordmark">
          <span className="logo">S</span>
          <div>
            FDR Sentinel<small>DEPOSIT OPERATIONS</small>
          </div>
        </div>
        <div className="nav-label">WORKSPACE</div>
        {[
          "Overview",
          "Deposits",
          "Institutions",
          "Release cases",
          "Reports",
          "Audit trail",
        ].map((name, i) => (
          <button
            key={name}
            className={`nav ${tab === name ? "active" : ""}`}
            onClick={() => {
              setTab(name);
              setSelected(null);
              setForm("");
            }}
          >
            <span>{["◫", "▤", "⌂", "⇄", "▥", "◷"][i]}</span>
            {name}
          </button>
        ))}
        <div className="sidebar-bottom">
          <span className="status-dot" />
          {health}
          <p>SIH26265 · Development</p>
          <button
            className="logout"
            onClick={() =>
              identity.signoutRedirect({ id_token_hint: user.id_token })
            }
          >
            Sign out ↗
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <span>/</span> {tab}
          </div>
          <div className="user">
            <span className="avatar">
              {String(user.profile.preferred_username ?? "U")
                .slice(0, 1)
                .toUpperCase()}
            </span>
            <div>
              {String(user.profile.preferred_username ?? "User")}
              <small>
                {me?.bindings
                  .map((b) => b.role)
                  .filter((x, i, a) => a.indexOf(x) === i)
                  .join(" · ") || "Institution onboarding"}
              </small>
            </div>
          </div>
        </header>
        <div className="mode">
          <span>◈ SYNTHETIC ENVIRONMENT</span> Bank / AICTE: sandbox APIs ·
          Provisional policy · Human decisions required
        </div>
        <div className="content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">INSTITUTIONAL SECURITY DEPOSITS</p>
              <h1>
                {selected
                  ? `Deposit ${short(selected.id)}`
                  : tab === "Overview"
                    ? "Your operations, at a glance."
                    : tab}
              </h1>
              <p>
                {selected
                  ? `${selected.deposit_type} · ${selected.bank_code} · Reference ending ${selected.reference_last4}`
                  : "A clear view of records, evidence and the decisions that move them forward."}
              </p>
            </div>
            {!selected && (
              <div className="heading-actions">
                <button
                  onClick={() => {
                    setForm("institution");
                    setTab("Institutions");
                  }}
                >
                  + Onboard institution
                </button>
                {me?.bindings.some((b) => b.role === "MAKER") && (
                  <button
                    className="primary"
                    onClick={() => {
                      setForm("deposit");
                      setTab("Deposits");
                    }}
                  >
                    + Register deposit
                  </button>
                )}
              </div>
            )}
            {selected && (
              <button onClick={() => setSelected(null)}>← All deposits</button>
            )}
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
              <button onClick={() => setError("")}>×</button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
            </div>
          )}
          {form === "institution" && (
            <section className="panel">
              <h2>Declare an institution</h2>
              <p>
                Creates your maker scope. This does not verify AICTE
                registration.
              </p>
              <form
                className="form-grid"
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = values(e.currentTarget);
                  perform(async () => {
                    const institution = await api<Institution>(
                      "/institutions",
                      {
                        external_id: v.external_id,
                        legal_name: v.legal_name,
                        context: {
                          academic_year: v.academic_year,
                          governance:
                            v.governance as Schemas["PolicyContext"]["governance"],
                          programme:
                            v.programme as Schemas["PolicyContext"]["programme"],
                          level: v.level as Schemas["PolicyContext"]["level"],
                          land: v.land as Schemas["PolicyContext"]["land"],
                          exceptional_context: v.exceptional === "yes",
                        },
                      } satisfies Schemas["InstitutionIn"],
                    );
                    await api("/obligations", {
                      institution_id: institution.id,
                      regulatory_event: v.event,
                      coverage_mode: v.coverage_mode,
                    });
                    setForm("");
                  }, "Institution and separate deposit obligation recorded.");
                }}
              >
                <Field label="Legal name">
                  <input name="legal_name" required minLength={3} />
                </Field>
                <Field label="Institution identifier (synthetic)">
                  <input
                    name="external_id"
                    required
                    pattern="[A-Za-z0-9-]{5,64}"
                  />
                </Field>
                <Field label="Academic year">
                  <input
                    name="academic_year"
                    defaultValue="2026-27"
                    required
                    pattern="20[0-9]{2}-[0-9]{2}"
                  />
                </Field>
                <Field label="Governance">
                  <select name="governance">
                    <option>PRIVATE</option>
                    <option>GOVERNMENT</option>
                    <option>GOVERNMENT_AIDED</option>
                    <option>UNKNOWN</option>
                  </select>
                </Field>
                <Field label="Programme">
                  <select name="programme">
                    <option value="ENGINEERING">
                      Engineering & Technology
                    </option>
                    <option>PLANNING</option>
                    <option>APPLIED_ARTS</option>
                    <option>DESIGN</option>
                    <option>HMCT</option>
                    <option>COMPUTER_APPLICATIONS</option>
                    <option>MANAGEMENT</option>
                    <option>OTHER</option>
                    <option>UNKNOWN</option>
                  </select>
                </Field>
                <Field label="Programme level">
                  <select name="level" defaultValue="UG">
                    <option>DIPLOMA</option>
                    <option>UG</option>
                    <option>PG</option>
                    <option>UNKNOWN</option>
                  </select>
                </Field>
                <Field label="Obligation coverage">
                  <select name="coverage_mode">
                    <option value="SINGLE_RECORD">
                      Single covering record
                    </option>
                    <option value="AGGREGATE_REVIEW">
                      Split / aggregate deposits — human review
                    </option>
                  </select>
                </Field>
                <Field label="Land / building">
                  <select name="land">
                    <option>OWNED</option>
                    <option>PRIVATE_LEASE</option>
                    <option>OTHER</option>
                    <option>UNKNOWN</option>
                  </select>
                </Field>
                <Field label="Regulatory event">
                  <select name="event">
                    <option>NEW_INSTITUTION</option>
                    <option>HISTORICAL_RECORD</option>
                    <option>OTHER</option>
                  </select>
                </Field>
                <Field label="Exceptional history / uncertainty">
                  <select name="exceptional">
                    <option value="yes">Yes / unknown — needs review</option>
                    <option value="no">No — supported simple context</option>
                  </select>
                </Field>
                <button disabled={busy} className="primary">
                  Create institution & obligation
                </button>
                <button type="button" onClick={() => setForm("")}>
                  Cancel
                </button>
              </form>
            </section>
          )}
          {form === "deposit" && (
            <section className="panel">
              <h2>Register a deposit record</h2>
              <p>
                Historical FDR registration does not authorize creating a new
                FDR for a current online obligation.
              </p>
              <form
                className="form-grid"
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = values(e.currentTarget);
                  perform(async () => {
                    await api("/deposits", {
                      obligation_id: v.obligation_id,
                      deposit_type: v.type,
                      bank_code: v.bank_code,
                      reference: v.reference,
                      amount_paise: Math.round(Number(v.amount) * 100),
                      issue_date: v.issue_date || null,
                      maturity_date: v.maturity_date || null,
                      deposited_on: v.deposited_on || null,
                    });
                    setForm("");
                  }, "Deposit persisted. Upload its proof to begin scrutiny.");
                }}
              >
                <Field label="Obligation / institution">
                  <select name="obligation_id" required>
                    {obligations
                      .filter((o) => maker(o.institution_id))
                      .map((o) => (
                        <option key={o.id} value={o.id}>
                          {
                            institutions.find((i) => i.id === o.institution_id)
                              ?.legal_name
                          }{" "}
                          · {display(o.regulatory_event)}
                        </option>
                      ))}
                  </select>
                </Field>
                <Field label="Deposit type">
                  <select
                    name="type"
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    {["FDR", "RPGF", "RTGS", "ONLINE", "OTHER_LEGACY"].map(
                      (t) => (
                        <option key={t}>{t}</option>
                      ),
                    )}
                  </select>
                </Field>
                <Field label="Bank code">
                  <input
                    name="bank_code"
                    defaultValue="DEMO-BANK"
                    required
                    pattern="[A-Z0-9-]{3,32}"
                  />
                </Field>
                <Field label="Full reference (stored as digest + last four)">
                  <input
                    name="reference"
                    required
                    minLength={6}
                    maxLength={80}
                  />
                </Field>
                <Field label="Declared amount (INR)">
                  <input
                    name="amount"
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                  />
                </Field>
                {kind === "FDR" ? (
                  <>
                    <Field label="Issue date">
                      <input name="issue_date" type="date" required />
                    </Field>
                    <Field label="Maturity date">
                      <input name="maturity_date" type="date" required />
                    </Field>
                  </>
                ) : (
                  <Field label="Deposited on">
                    <input name="deposited_on" type="date" required />
                  </Field>
                )}
                <button disabled={busy} className="primary">
                  Save deposit
                </button>
                <button type="button" onClick={() => setForm("")}>
                  Cancel
                </button>
              </form>
            </section>
          )}
          {!selected && !form && (
            <>
              {tab === "Overview" && (
                <>
                  <div className="stats">
                    <div>
                      <span>Total recorded</span>
                      <strong>
                        {Object.values(summary?.workflow_counts ?? {})
                          .reduce((a, b) => a + b, 0)
                          .toString()
                          .padStart(2, "0")}
                      </strong>
                      <small>Across your assigned scope</small>
                    </div>
                    <div>
                      <span>Declared deposit value</span>
                      <strong>
                        {money(summary?.declared_total_paise ?? 0)}
                      </strong>
                      <small>Institution assertions · not bank verified</small>
                    </div>
                    <div>
                      <span>Awaiting scrutiny</span>
                      <strong>
                        {(summary?.workflow_counts.PENDING_SCRUTINY ?? 0)
                          .toString()
                          .padStart(2, "0")}
                      </strong>
                      <small>Human review required</small>
                    </div>
                    <div>
                      <span>Registration accepted</span>
                      <strong>
                        {(summary?.workflow_counts.ACCEPTED ?? 0)
                          .toString()
                          .padStart(2, "0")}
                      </strong>
                      <small>Separate from release eligibility</small>
                    </div>
                  </div>
                  <div className="insight">
                    <div className="insight-icon">↗</div>
                    <div>
                      <h2>Evidence first. Decisions with a record.</h2>
                      <p>
                        Upload proof, inspect deterministic findings and send
                        deposits to an assigned officer. Every transition
                        retains its actor, reason and policy revision.
                      </p>
                    </div>
                    <span className="muted">APH 2024–27 / provisional</span>
                  </div>
                </>
              )}
              {(tab === "Overview" || tab === "Deposits") && (
                <section className="panel">
                  <div className="section-head">
                    <div>
                      <h2>Deposit register</h2>
                      <p>Latest 100 scoped records · amounts in INR</p>
                    </div>
                    <Badge value="PERSISTENT_DATA" />
                  </div>
                  {records.length ? (
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Record / institution</th>
                            <th>Type</th>
                            <th>Declared amount</th>
                            <th>Maturity</th>
                            <th>Review status</th>
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {records.map((d) => (
                            <tr
                              key={d.id}
                              onClick={() => open(d)}
                              tabIndex={0}
                              onKeyDown={(e) => e.key === "Enter" && open(d)}
                            >
                              <td>
                                <strong>
                                  {short(d.id)}{" "}
                                  <span className="muted">
                                    ··{d.reference_last4}
                                  </span>
                                </strong>
                                <small>
                                  {
                                    institutions.find(
                                      (i) => i.id === d.institution_id,
                                    )?.legal_name
                                  }
                                </small>
                              </td>
                              <td>{d.deposit_type}</td>
                              <td className="amount">
                                {money(d.amount_paise)}
                              </td>
                              <td>{d.maturity_date ?? "Not applicable"}</td>
                              <td>
                                <Badge value={d.workflow} />
                              </td>
                              <td>↗</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="empty">
                      <span>▤</span>
                      <h3>Your deposit register starts here</h3>
                      <p>
                        Onboard an institution, register its obligation and
                        upload a synthetic deposit proof.
                      </p>
                    </div>
                  )}
                </section>
              )}
              {tab === "Institutions" && (
                <div className="institution-grid">
                  {institutions.map((i) => (
                    <section key={i.id} className="panel">
                      <p className="eyebrow">{i.external_id}</p>
                      <h2>{i.legal_name}</h2>
                      <Badge value={i.registry_status} />
                      <dl>
                        <dt>Programme</dt>
                        <dd>{display(i.context.programme)}</dd>
                        <dt>Academic year</dt>
                        <dd>{i.context.academic_year}</dd>
                        <dt>Property</dt>
                        <dd>{display(i.context.land)}</dd>
                      </dl>
                      <IntegrationPanel
                        institutionId={i.id}
                        canRegistry={maker(i.id) || reviewer(i.id)}
                        onChange={refresh}
                      />
                    </section>
                  ))}
                </div>
              )}
              {tab === "Release cases" && (
                <ReleaseDesk records={records} bindings={me?.bindings ?? []} />
              )}
              {tab === "Reports" && <Reports />}
              {tab === "Audit trail" && (
                <section className="panel">
                  <h2>Immutable activity trail</h2>
                  <p>Latest 100 events in your institutional scope.</p>
                  {audit.map((a) => (
                    <div key={a.id} className="audit-row">
                      <span className="status-dot" />
                      <div>
                        <strong>{display(a.action)}</strong>
                        <small>
                          {a.actor} · {short(a.aggregate_id)}
                        </small>
                      </div>
                      <time>{new Date(a.created_at).toLocaleString()}</time>
                    </div>
                  ))}
                </section>
              )}
            </>
          )}
          {selected && (
            <>
              <div className="detail-strip">
                <div>
                  <span>Declared amount</span>
                  <strong>{money(selected.amount_paise)}</strong>
                </div>
                <div>
                  <span>Scrutiny</span>
                  <Badge value={selected.workflow} />
                </div>
                <div>
                  <span>Verification source</span>
                  <Badge value={selected.verification_status} />
                </div>
                <div>
                  <span>Revision</span>
                  <strong>
                    v{selected.version}{" "}
                    <small>input {selected.input_revision}</small>
                  </strong>
                </div>
              </div>
              <div className="detail-grid">
                <section className="panel">
                  <div className="section-head">
                    <h2>Document evidence</h2>
                    <span className="muted">Private · originals retained</span>
                  </div>
                  {selected.documents.length === 0 && (
                    <p>No proof uploaded yet.</p>
                  )}
                  {selected.documents.map((d) => (
                    <div className="document" key={d.id}>
                      <div className="section-head">
                        <strong>{display(d.category)}</strong>
                        <Badge value={d.active ? d.status : "SUPERSEDED"} />
                      </div>
                      <small className="hash">SHA256 {d.sha256}</small>
                      <p>
                        {d.scan_result ??
                          "Awaiting actual antivirus scan; file remains quarantined."}
                      </p>
                      {d.status === "READY" && (
                        <button
                          onClick={() =>
                            perform(
                              () => download(d.id),
                              "Document download audited.",
                            )
                          }
                        >
                          Download original ↗
                        </button>
                      )}
                      {d.evidence.map((e, index) => (
                        <div className="evidence" key={index}>
                          <span>{display(String(e.field))}</span>
                          <strong>{String(e.value)}</strong>
                          <small>
                            Page {String(e.page)} · {String(e.method)} · offset{" "}
                            {String(e.offset)}
                          </small>
                        </div>
                      ))}
                    </div>
                  ))}
                  {maker(selected.institution_id) &&
                    selected.workflow === "DRAFT" && (
                      <form
                        className="upload-form"
                        onSubmit={(e) => {
                          e.preventDefault();
                          const data = new FormData(e.currentTarget);
                          perform(
                            () =>
                              api(`/deposits/${selected.id}/documents`, data),
                            "Upload quarantined. Worker will scan and extract it.",
                          );
                        }}
                      >
                        <Field label="Evidence category">
                          <select name="category">
                            {[
                              "DEPOSIT_PROOF",
                              "REQUEST_LETTER",
                              "AFFIDAVIT_6",
                              "APPROVAL_LETTER",
                              "SUPPORTING",
                            ].map((c) => (
                              <option key={c}>{c}</option>
                            ))}
                          </select>
                        </Field>
                        <Field label="Supersede previous evidence (optional)">
                          <select name="supersedes_id">
                            <option value="">Add new evidence</option>
                            {selected.documents
                              .filter((d) => d.active)
                              .map((d) => (
                                <option value={d.id} key={d.id}>
                                  {d.category} · {short(d.id)}
                                </option>
                              ))}
                          </select>
                        </Field>
                        <Field label="PDF file · maximum 10 MiB">
                          <input
                            name="file"
                            type="file"
                            accept="application/pdf"
                            required
                          />
                        </Field>
                        <button disabled={busy}>Upload privately</button>
                      </form>
                    )}
                </section>
                <section className="panel">
                  <div className="section-head">
                    <h2>Policy & consistency checks</h2>
                    <Badge
                      value={String(
                        selected.evaluations[0]?.result.outcome ??
                          "NOT_EVALUATED",
                      )}
                    />
                  </div>
                  <p className="policy-note">
                    Deterministic checks, provisional APH 2024–27. Registration
                    review does not certify legal compliance or permit release.
                  </p>
                  {!!selected.evaluations[0]?.result.findings &&
                    (
                      selected.evaluations[0].result.findings as Record<
                        string,
                        unknown
                      >[]
                    ).map((f, i) => (
                      <div
                        className={`finding ${f.severity === "FAIL" ? "blocker" : ""}`}
                        key={i}
                      >
                        <strong>{display(String(f.code))}</strong>
                        <p>{String(f.message)}</p>
                        {f.citation != null && (
                          <small>{String(f.citation)}</small>
                        )}
                        {f.evidence != null && (
                          <pre>{JSON.stringify(f.evidence, null, 2)}</pre>
                        )}
                      </div>
                    ))}
                  {(maker(selected.institution_id) ||
                    reviewer(selected.institution_id)) &&
                    selected.workflow !== "ACCEPTED" && (
                      <button
                        disabled={busy}
                        onClick={() => command("evaluate")}
                      >
                        Run current evaluation
                      </button>
                    )}
                  {!selected.evaluation_fresh &&
                    selected.workflow === "ACCEPTED" &&
                    (maker(selected.institution_id) ||
                      reviewer(selected.institution_id)) && (
                      <div className="policy-note">
                        <p>
                          Policy or evidence revision changed. Historical review
                          is retained, but current release requires fresh
                          scrutiny.
                        </p>
                        <button
                          disabled={busy}
                          onClick={() => command("request-revalidation")}
                        >
                          Request fresh policy scrutiny
                        </button>
                      </div>
                    )}
                  {maker(selected.institution_id) &&
                    selected.workflow === "DRAFT" && (
                      <button
                        disabled={busy}
                        className="primary"
                        onClick={() => command("submit")}
                      >
                        Submit for scrutiny →
                      </button>
                    )}
                  {reviewer(selected.institution_id) &&
                    selected.workflow === "PENDING_SCRUTINY" && (
                      <form
                        className="review-form"
                        onSubmit={(e) => {
                          e.preventDefault();
                          const v = values(e.currentTarget);
                          command("review", {
                            decision: v.decision,
                            reason: v.reason,
                            evidence_reviewed: v.evidence_reviewed === "on",
                          });
                        }}
                      >
                        <Field label="Officer decision">
                          <select name="decision">
                            <option value="RETURN">
                              Return for correction
                            </option>
                            <option value="ACCEPT_REGISTRATION">
                              Accept registration (not bank verification)
                            </option>
                          </select>
                        </Field>
                        <Field label="Reason / correction request">
                          <textarea name="reason" minLength={10} required />
                        </Field>
                        <label className="check">
                          <input type="checkbox" name="evidence_reviewed" />I
                          reviewed the original evidence and provisional
                          findings.
                        </label>
                        <button disabled={busy} className="primary">
                          Record human decision
                        </button>
                      </form>
                    )}
                </section>
              </div>
              {maker(selected.institution_id) &&
                selected.workflow === "DRAFT" && (
                  <section className="panel">
                    <h2>Correct declared inputs</h2>
                    <p>
                      Corrections increment the input revision and invalidate
                      previous evaluations. Originals remain unchanged.
                    </p>
                    <form
                      className="form-grid"
                      key={selected.input_revision}
                      onSubmit={(e) => {
                        e.preventDefault();
                        const v = values(e.currentTarget);
                        command("correct", {
                          amount_paise: Math.round(Number(v.amount) * 100),
                          issue_date: v.issue_date || null,
                          maturity_date: v.maturity_date || null,
                          deposited_on: v.deposited_on || null,
                        });
                      }}
                    >
                      <Field label="Amount (INR)">
                        <input
                          name="amount"
                          type="number"
                          min="0.01"
                          step="0.01"
                          defaultValue={selected.amount_paise / 100}
                          required
                        />
                      </Field>
                      {selected.deposit_type === "FDR" ? (
                        <>
                          <Field label="Issue date">
                            <input
                              name="issue_date"
                              type="date"
                              defaultValue={selected.issue_date ?? ""}
                              required
                            />
                          </Field>
                          <Field label="Maturity date">
                            <input
                              name="maturity_date"
                              type="date"
                              defaultValue={selected.maturity_date ?? ""}
                              required
                            />
                          </Field>
                        </>
                      ) : (
                        <Field label="Deposited on">
                          <input
                            name="deposited_on"
                            type="date"
                            defaultValue={selected.deposited_on ?? ""}
                            required
                          />
                        </Field>
                      )}
                      <button disabled={busy}>Save correction</button>
                    </form>
                  </section>
                )}
              <IntegrationPanel
                institutionId={selected.institution_id}
                depositId={selected.id}
                version={selected.version}
                canBank={reviewer(selected.institution_id)}
                onChange={async () => {
                  await refresh();
                  setSelected(await api<Detail>(`/deposits/${selected.id}`));
                }}
              />
              <IntelligencePanel
                record={selected}
                maker={maker(selected.institution_id)}
                reviewer={reviewer(selected.institution_id)}
                subject={me?.subject ?? ""}
                run={perform}
                busy={busy}
              />
              {selected.decisions.length > 0 && (
                <section className="panel">
                  <h2>Officer decisions</h2>
                  {selected.decisions.map((d, i) => (
                    <div className="audit-row" key={i}>
                      <div>
                        <strong>{display(String(d.decision))}</strong>
                        <p>{String(d.reason)}</p>
                        <small>{String(d.actor)}</small>
                      </div>
                    </div>
                  ))}
                </section>
              )}
            </>
          )}
          <footer>
            <span>FDR Sentinel / SIH26265</span>
            <span>Human accountability at every decision.</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
