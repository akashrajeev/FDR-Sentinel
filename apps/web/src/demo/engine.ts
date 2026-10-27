import type { Schemas } from "../api";
import {
  clock,
  defaultPolicy,
  evaluate,
  personas,
  revision,
  sampleDocument,
  seed,
  subject,
  uid,
  type Binding,
  type Persona,
  type State,
} from "./model";
import { readCsv, readPdf } from "./intake";

const storageKey = "sentinel-interactive-demo-v1";
let storageAvailable = true;
function read(): State {
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw) {
      const value = JSON.parse(raw) as State;
      if (
        value.schema === 1 &&
        personas.some(([r]) => r === value.role) &&
        [
          value.institutions,
          value.obligations,
          value.deposits,
          value.cases,
          value.audit,
          value.corrections,
          value.discrepancies,
          value.exchanges,
          value.relations,
          value.tasks,
          value.notifications,
          value.assignments,
        ].every(Array.isArray) &&
        value.policies &&
        value.deposits.every(
          (d) => Array.isArray(d.documents) && Array.isArray(d.evaluations),
        )
      )
        return value;
    }
  } catch {
    storageAvailable = false;
  }
  return seed();
}
let state = read();
const clone = <T>(value: T): T => structuredClone(value);
export const currentPersona = () => state.role;
export const hasDemoStorage = () => storageAvailable;
function save() {
  state.audit = state.audit.slice(0, 300);
  try {
    localStorage.setItem(storageKey, JSON.stringify(state));
    storageAvailable = true;
  } catch {
    storageAvailable = false;
  }
}
export function switchPersona(role: Persona) {
  state.role = role;
  save();
}
export function resetDemo() {
  state = seed();
  syncTasks();
  save();
}
export function bindings(): Binding[] {
  const role = state.role;
  if (role === "operator")
    return [{ role: "OPERATOR", scope_type: "PLATFORM", scope_id: "DEMO" }];
  const mapped =
    role === "institution"
      ? "MAKER"
      : ["pgrc", "vigilance", "grants"].includes(role)
        ? "CASE_VIEWER"
        : role.toUpperCase();
  const result: Binding[] = state.institutions.map((i) => ({
    role: mapped,
    scope_type: "INSTITUTION",
    scope_id: i.id,
  }));
  if (["pgrc", "vigilance", "grants"].includes(role))
    result.push({
      role: "CLEARANCE",
      scope_type: "BUREAU",
      scope_id: role.toUpperCase(),
    });
  result.push(
    ...state.assignments.filter(
      (a) =>
        a.enabled &&
        a.subject === subject(role) &&
        (!a.valid_until || a.valid_until > new Date().toISOString()),
    ),
  );
  return result;
}
function requireRole(...roles: Persona[]) {
  const aliases: Record<string, string> = {
    institution: "MAKER",
    reviewer: "REVIEWER",
    approver: "APPROVER",
    issuer: "ISSUER",
    auditor: "AUDITOR",
    operator: "OPERATOR",
  };
  if (
    !roles.includes(state.role) &&
    !bindings().some((b) => roles.some((r) => b.role === aliases[r]))
  )
    throw new Error(
      `Switch demo persona to ${roles.map((r) => personas.find(([id]) => id === r)![1]).join(" or ")} for this action.`,
    );
}
function requireText(value: unknown, min = 10) {
  if (typeof value !== "string" || value.trim().length < min)
    throw new Error(`Record a reason of at least ${min} characters.`);
}
function checkVersion(
  record: { version: number },
  body: Record<string, unknown>,
) {
  if (
    body.expected_version !== undefined &&
    Number(body.expected_version) !== record.version
  )
    throw new Error(
      "This example changed. Refresh it before recording a decision.",
    );
}
function audit(
  action: string,
  id: string,
  institution = state.institutions[0].id,
  detail: Record<string, unknown> = {},
) {
  state.audit.unshift({
    id: uid(),
    institution_id: institution,
    actor: subject(state.role),
    action: `DEMO_${action}`,
    aggregate_id: id,
    detail: { browser_simulation: true, ...detail },
    request_id: uid(),
    created_at: new Date().toISOString(),
  });
}
function getDeposit(id: string) {
  const d = state.deposits.find((d) => d.id === id);
  if (!d) throw new Error("Demo deposit not found.");
  return d;
}
function getCase(id: string) {
  const c = state.cases.find((c) => c.id === id);
  if (!c) throw new Error("Demo case not found.");
  return c;
}
function blockers(c: State["cases"][number]) {
  const d = getDeposit(c.deposit_id);
  return [
    ...c.required_bureaus
      .filter(
        (b) =>
          !c.clearances.some((x) => x.bureau === b && x.decision === "CLEARED"),
      )
      .map((b) => `${b} clearance pending or rejected`),
    ...c.holds.filter((h) => h.active).map((h) => `Active hold: ${h.reason}`),
    ...["REQUEST_LETTER", "AFFIDAVIT_6", "APPROVAL_LETTER"]
      .filter(
        (category) =>
          !c.documents.some(
            (d) => d.category === category && d.status === "READY",
          ),
      )
      .map((category) => `Missing ${category}`),
    ...(!d.evaluation_fresh || d.workflow !== "ACCEPTED"
      ? ["Fresh accepted deposit scrutiny required"]
      : []),
    ...(d.maturity_date && d.maturity_date > clock
      ? ["FDR term has not completed at the demo clock"]
      : []),
  ];
}
const categories = [
  "UNSAFE_DOCUMENT",
  "VERIFICATION_PENDING",
  "VERIFICATION_FAILED",
  "REGULATORY_CONTEXT",
  "MISSING_DOCUMENT",
  "UNRESOLVED_DISCREPANCY",
  "SCRUTINY_OVERDUE",
  "BUREAU_CLEARANCE",
  "ACTIVE_HOLD",
  "MATURITY",
];
function syncTasks() {
  const desired: {
    id: string;
    category: string;
    deposit_id: string;
    case_id?: string;
    institution_id: string;
  }[] = [];
  for (const d of state.deposits) {
    if (d.documents.some((x) => x.active && x.status !== "READY"))
      desired.push({
        id: `unsafe-${d.id}`,
        category: "UNSAFE_DOCUMENT",
        deposit_id: d.id,
        institution_id: d.institution_id,
      });
    if (
      (!d.evaluation_fresh && d.workflow === "ACCEPTED") ||
      d.evaluations[0]?.result.outcome === "REQUIRES_HUMAN_REVIEW"
    )
      desired.push({
        id: `policy-${d.id}`,
        category: "REGULATORY_CONTEXT",
        deposit_id: d.id,
        institution_id: d.institution_id,
      });
    if (
      state.exchanges.some(
        (x) =>
          x.deposit_id === d.id &&
          ["PENDING", "RETRYING", "DEAD_LETTER"].includes(x.state),
      )
    )
      desired.push({
        id: `source-${d.id}`,
        category: state.exchanges.some(
          (x) => x.deposit_id === d.id && x.state === "DEAD_LETTER",
        )
          ? "VERIFICATION_FAILED"
          : "VERIFICATION_PENDING",
        deposit_id: d.id,
        institution_id: d.institution_id,
      });
    if (!d.documents.some((x) => x.active && x.category === "DEPOSIT_PROOF"))
      desired.push({
        id: `missing-${d.id}`,
        category: "MISSING_DOCUMENT",
        deposit_id: d.id,
        institution_id: d.institution_id,
      });
    if (d.workflow === "PENDING_SCRUTINY")
      desired.push({
        id: `review-${d.id}`,
        category: "SCRUTINY_OVERDUE",
        deposit_id: d.id,
        institution_id: d.institution_id,
      });
    if (
      state.discrepancies.some(
        (x) => x.deposit_id === d.id && x.status === "OPEN",
      )
    )
      desired.push({
        id: `disc-${d.id}`,
        category: "UNRESOLVED_DISCREPANCY",
        deposit_id: d.id,
        institution_id: d.institution_id,
      });
    if (
      d.maturity_date &&
      d.maturity_date <= "2027-01-25" &&
      d.lifecycle_status !== "REPLACED"
    )
      desired.push({
        id: `maturity-${d.id}`,
        category: "MATURITY",
        deposit_id: d.id,
        institution_id: d.institution_id,
      });
  }
  for (const c of state.cases) {
    c.blockers = blockers(c);
    if (c.state === "CLEARANCES_PENDING")
      desired.push({
        id: `bureau-${c.id}`,
        category: "BUREAU_CLEARANCE",
        deposit_id: c.deposit_id,
        case_id: c.id,
        institution_id: c.institution_id,
      });
    if (c.holds.some((h) => h.active))
      desired.push({
        id: `hold-${c.id}`,
        category: "ACTIVE_HOLD",
        deposit_id: c.deposit_id,
        case_id: c.id,
        institution_id: c.institution_id,
      });
  }
  for (const t of state.tasks)
    if (!desired.some((x) => x.id === t.id)) t.state = "RESOLVED";
  for (const d of desired) {
    const previous = state.tasks.find((t) => t.id === d.id);
    const policy = state.policies[d.institution_id] ?? defaultPolicy();
    const field =
      d.category === "BUREAU_CLEARANCE"
        ? "clearance_hours"
        : d.category === "MISSING_DOCUMENT"
          ? "missing_document_hours"
          : d.category === "UNRESOLVED_DISCREPANCY"
            ? "discrepancy_hours"
            : d.category.startsWith("VERIFICATION")
              ? "verification_hours"
              : "review_hours";
    const due = new Date(
      Date.parse("2026-10-24T08:00:00Z") +
        policy.configuration[field] * 3600000,
    ).toISOString();
    if (previous) {
      previous.state = "OPEN";
      previous.due_at = due;
      previous.policy_revision = policy.revision;
    } else
      state.tasks.push({
        ...d,
        case_id: d.case_id ?? null,
        state: "OPEN",
        episode: 1,
        due_at: due,
        observed_at: "2026-10-24T08:00:00Z",
        policy_revision: policy.revision,
        detail: {
          simulation: true,
          message:
            "Resolve the underlying source condition; acknowledgement alone does not clear it.",
        },
        acknowledged_by: null,
        acknowledgement: null,
      });
  }
}
syncTasks();
function report(params: URLSearchParams, all = false) {
  const filtered = state.tasks.filter(
    (t) =>
      (!params.get("institution_id") ||
        t.institution_id === params.get("institution_id")) &&
      (!params.get("deposit_id") ||
        t.deposit_id === params.get("deposit_id")) &&
      (!params.get("category") || t.category === params.get("category")) &&
      (!params.get("state") ||
        params.get("state") === "ALL" ||
        t.state === params.get("state")) &&
      (params.get("overdue") !== "true" || t.due_at.slice(0, 10) < clock),
  );
  const counts: Record<string, number> = {};
  filtered.forEach((t) => (counts[t.category] = (counts[t.category] ?? 0) + 1));
  const limit = Math.max(1, Math.min(50, Number(params.get("limit")) || 50));
  const start = params.get("after")
    ? filtered.findIndex((t) => t.id === params.get("after")) + 1
    : 0;
  const items = all ? filtered : filtered.slice(start, start + limit);
  return {
    items,
    total: filtered.length,
    counts,
    next_cursor:
      !all && filtered.length > start + limit
        ? (items.at(-1)?.id ?? null)
        : null,
    categories,
  };
}
function search(params: URLSearchParams, all = false) {
  const q = (params.get("q") ?? "").trim().toLowerCase();
  const filtered = state.deposits.filter(
    (d) =>
      (!params.get("workflow") || d.workflow === params.get("workflow")) &&
      (!q ||
        [
          d.id,
          d.bank_code,
          d.reference_last4,
          state.institutions.find((i) => i.id === d.institution_id)
            ?.legal_name ?? "",
        ].some((v) => v.toLowerCase().includes(q))),
  );
  const start = params.get("after")
    ? filtered.findIndex((d) => d.id === params.get("after")) + 1
    : 0;
  return all ? filtered : filtered.slice(start, start + 50);
}
function summary(): Schemas["SummaryOut"] {
  const count = (rows: { [key: string]: unknown }[], field: string) =>
    rows.reduce<Record<string, number>>((a, r) => {
      const k = String(r[field]);
      a[k] = (a[k] ?? 0) + 1;
      return a;
    }, {});
  return {
    as_of: clock,
    mode: "BROWSER_DEMO",
    workflow_counts: count(state.deposits, "workflow"),
    stored_lifecycle_counts: count(state.deposits, "lifecycle_status"),
    declared_total_paise: state.deposits
      .reduce((s, d) => s + BigInt(d.amount_paise), 0n)
      .toString(),
    fdr_matured_from_dates: state.deposits.filter(
      (d) => d.maturity_date && d.maturity_date <= clock,
    ).length,
    fdr_upcoming_90_days: state.deposits.filter(
      (d) =>
        d.maturity_date &&
        d.maturity_date > clock &&
        d.maturity_date <= "2027-01-25",
    ).length,
    release_case_counts: count(state.cases, "state"),
    actual_financial_releases: 0,
    external_verification: "SIMULATED",
    completed_synthetic_case_time: { samples: 0, median_seconds: null },
    policy_revision: revision,
    policy_status: "PROVISIONAL_DEMO_FIXTURE",
  };
}
export async function demoApi<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const before = clone(state);
  try {
    advanceJobs();
    if (body instanceof FormData && path.startsWith("/legacy-import/")) {
      requireRole("institution");
      const { records, sha256 } = await readCsv(body);
      if (path.endsWith("/commit") && body.get("expected_sha256") !== sha256)
        throw new Error("CSV changed since preview; validate it again.");
      for (const record of records) route("/deposits", record, "POST");
      if (path.endsWith("/preview")) {
        state = before;
        return {
          sha256,
          rows: records.length,
          declared_total_paise: records
            .reduce(
              (total, row) => total + BigInt(Number(row.amount_paise)),
              0n,
            )
            .toString(),
          note: "Validated locally with synthetic-only references. All rows remain drafts; no server or external source was contacted.",
        } as T;
      }
      syncTasks();
      save();
      return { rows: records.length } as T;
    }
    if (body instanceof FormData) body = await readPdf(body);
    const result = route(
      path,
      body,
      method ?? (body === undefined ? "GET" : "POST"),
    );
    if (body !== undefined) {
      syncTasks();
      save();
    }
    return clone(result) as T;
  } catch (error) {
    state = before;
    throw error;
  }
}
function advanceJobs() {
  let changed = false;
  for (const d of state.deposits)
    for (const doc of d.documents) {
      const due = Number(doc.processing_metadata.demo_complete_at ?? 0);
      if (due && due <= Date.now()) {
        doc.status = "READY";
        doc.scan_result =
          "SIMULATED processing completed for a recognized synthetic sample. No actual antivirus/OCR ran.";
        delete doc.processing_metadata.demo_complete_at;
        d.version++;
        changed = true;
      }
    }
  for (const x of state.exchanges)
    if (x.ready_at && x.ready_at <= Date.now()) {
      x.state = "SUCCEEDED";
      delete x.ready_at;
      x.last_error = null;
      if (x.deposit_id) {
        const d = getDeposit(x.deposit_id);
        d.verification_status = x.result.outcome;
        d.version++;
      }
      changed = true;
    }
  if (changed) {
    syncTasks();
    save();
  }
}
function route(path: string, payload: unknown, method: string): unknown {
  const url = new URL(path, "https://demo.invalid");
  const p = url.pathname.split("/").filter(Boolean),
    params = url.searchParams;
  const b = (payload ?? {}) as Record<string, unknown>;
  const read = method === "GET";
  if (read) {
    if (path === "/me")
      return { subject: subject(state.role), bindings: bindings() };
    if (path === "/health/ready") return { status: "browser demo" };
    if (path === "/health/live") return { status: "browser demo" };
    if (path === "/policies/current")
      return {
        revision,
        status: "PROVISIONAL_DEMO_FIXTURE",
        coverage:
          "Simple 2026-27 private Engineering UG owned-land sample only. Other applicability requires human review.",
      };
    if (path === "/work-queue")
      return state.deposits.filter((d) => d.workflow === "PENDING_SCRUTINY");
    if (path === "/dashboard/summary") return summary();
    if (p[0] === "search") return search(params);
    if (path === "/institutions") return state.institutions;
    if (p[0] === "institutions" && p.length === 2)
      return state.institutions.find((i) => i.id === p[1]);
    if (path === "/obligations") return state.obligations;
    if (path === "/deposits") return state.deposits;
    if (path === "/audit-events") return state.audit;
    if (path === "/release-cases") {
      state.cases.forEach((c) => (c.blockers = blockers(c)));
      return state.cases;
    }
    if (p[0] === "release-cases" && p.length === 2) return getCase(p[1]);
    if (path === "/replacements") return state.relations;
    if (p[0] === "notifications")
      return state.notifications.filter(
        (n) =>
          !params.get("deposit_id") ||
          n.deposit_id === params.get("deposit_id"),
      );
    if (p[0] === "deposits" && p[1]) {
      const d = getDeposit(p[1]);
      if (!p[2]) return d;
      if (p[2] === "intelligence")
        return {
          corrections: state.corrections.filter((c) => c.deposit_id === d.id),
          discrepancies: state.discrepancies.filter(
            (c) => c.deposit_id === d.id,
          ),
          attestations: [],
        };
    }
    if (p[0] === "reports" && p[1] === "interventions") return report(params);
    if (p[0] === "institutions" && p[2] === "operations-policy")
      return state.policies[p[1]] ?? defaultPolicy();
    if (p[0] === "interventions" && p[2] === "notifications")
      return state.notifications.filter((n) => n.intervention_id === p[1]);
    if (p[0] === "integration-requests")
      return state.exchanges
        .filter((x) =>
          ["institution_id", "deposit_id", "case_id"].every(
            (k) => !params.get(k) || x[k as keyof typeof x] === params.get(k),
          ),
        )
        .map((x) =>
          ["PENDING", "RETRYING"].includes(x.state)
            ? { ...x, result: { outcome: "SIMULATED_PENDING" } }
            : x,
        );
    if (path === "/sandbox/catalogue")
      return {
        ledger: state.deposits.map((d) => ({
          id: `SB-${d.reference_last4}`,
          institution_external_id: "SYNTHETIC-001",
          bank_code: d.bank_code,
          reference_last4: d.reference_last4,
          amount_paise: d.id === "fdr00002-demo" ? 350000000 : d.amount_paise,
          status: "SIMULATED",
        })),
      };
    if (path === "/operator/workspace")
      return {
        institutions: state.institutions,
        principals: personas.map(([r, label]) => ({
          subject: subject(r),
          label,
          enabled: true,
        })),
        bindings: state.assignments,
      };
  }
  if (
    b.demo_upload &&
    ["deposits", "release-cases"].includes(p[0]) &&
    p[2] === "documents"
  ) {
    requireRole("institution");
    const c = p[0] === "release-cases" ? getCase(p[1]) : null;
    const d = c ? getDeposit(c.deposit_id) : getDeposit(p[1]);
    if ((c?.state ?? d.workflow) !== "DRAFT")
      throw new Error("Return the record to draft before changing evidence.");
    if (
      ![
        "DEPOSIT_PROOF",
        "REQUEST_LETTER",
        "AFFIDAVIT_6",
        "APPROVAL_LETTER",
        "SUPPORTING",
        "EXTERNAL_BODY_NOC",
        "CLOSURE_ORDER",
        "MERGER_ORDER",
        "CONVERSION_ORDER",
      ].includes(String(b.category))
    )
      throw new Error("Unsupported evidence category.");
    const doc = sampleDocument(d, String(b.category));
    doc.sha256 = String(b.sha256);
    doc.size = Number(b.size);
    doc.status = "QUARANTINED";
    doc.scan_result = b.sample
      ? "Recognized demo PDF. Simulated quarantine; no actual antivirus scan."
      : "Unrecognized local PDF. Quarantined without extraction; no file or its contents are stored.";
    doc.processing_metadata.demo_unrecognized = !b.sample;
    if (b.sample) {
      const fields = b.sample_fields as Record<string, unknown>;
      doc.processing_metadata.demo_snapshot = fields;
      doc.evidence.forEach((e) => {
        if (String(e.field) in fields) e.value = fields[String(e.field)];
      });
      if (!c) doc.processing_metadata.demo_complete_at = Date.now() + 1500;
      else {
        doc.status = "READY";
        doc.scan_result =
          "Recognized synthetic release sample; processing simulated.";
      }
    } else {
      doc.evidence = [];
      doc.processing_metadata.page_sizes = [];
    }
    const docs = c ? c.documents : d.documents;
    const old = docs.find((x) => x.active && x.category === doc.category);
    if (old) {
      old.active = false;
      doc.supersedes_id = String(old.id);
    }
    docs.push(doc);
    if (c) {
      c.version++;
      c.input_revision++;
      c.clearances = [];
    } else {
      d.version++;
      d.input_revision++;
      d.evaluation_fresh = false;
    }
    audit("LOCAL_PDF_INTAKE", c?.id ?? d.id, d.institution_id);
    return doc;
  }
  if (path === "/institutions" && !read) {
    requireRole("institution");
    const input = b as unknown as Schemas["InstitutionIn"];
    if (!input.external_id?.startsWith("SYN"))
      throw new Error("Use a fictional identifier starting SYN.");
    if (state.institutions.some((i) => i.external_id === input.external_id))
      throw new Error("Synthetic identifier already exists.");
    const i: Schemas["InstitutionOut"] = {
      ...input,
      id: uid(),
      registry_status: "INSTITUTION_DECLARED",
    };
    state.institutions.push(i);
    state.policies[i.id] = defaultPolicy();
    audit("INSTITUTION_DECLARED", i.id, i.id);
    return i;
  }
  if (path === "/obligations" && !read) {
    requireRole("institution");
    const i = state.institutions.find((i) => i.id === b.institution_id);
    if (!i) throw new Error("Institution required.");
    // Deliberately restrict this browser fixture; never duplicate the full policy evaluator.
    const simple =
      i.context.academic_year === "2026-27" &&
      i.context.governance === "PRIVATE" &&
      i.context.programme === "ENGINEERING" &&
      i.context.level === "UG" &&
      i.context.land === "OWNED" &&
      !i.context.exceptional_context &&
      b.regulatory_event === "NEW_INSTITUTION" &&
      b.coverage_mode !== "AGGREGATE_REVIEW";
    const o: Schemas["ObligationOut"] = {
      id: uid(),
      institution_id: i.id,
      regulatory_event:
        b.regulatory_event as Schemas["ObligationOut"]["regulatory_event"],
      coverage_mode:
        b.coverage_mode as Schemas["ObligationOut"]["coverage_mode"],
      context: i.context,
      status: simple ? "PROVISIONAL" : "REQUIRES_HUMAN_REVIEW",
      policy_revision: revision,
      required_amount_paise: simple ? 350000000 : null,
    };
    state.obligations.push(o);
    audit("OBLIGATION_RECORDED", o.id, i.id);
    return o;
  }
  if (path === "/deposits" && !read) {
    requireRole("institution");
    const o = state.obligations.find((o) => o.id === b.obligation_id);
    if (!o) throw new Error("Choose an obligation.");
    const amount = Number(b.amount_paise);
    if (
      !["FDR", "RPGF", "RTGS", "ONLINE", "OTHER_LEGACY"].includes(
        String(b.deposit_type),
      )
    )
      throw new Error("Unsupported deposit type.");
    const dateValid = (v: unknown) =>
      typeof v === "string" &&
      /^\d{4}-\d{2}-\d{2}$/.test(v) &&
      Number.isFinite(Date.parse(v)) &&
      new Date(v).toISOString().slice(0, 10) === v;
    if (
      b.deposit_type !== "FDR" &&
      (!dateValid(b.deposited_on) || b.issue_date || b.maturity_date)
    )
      throw new Error(
        "Non-FDR records need a deposit date, without invented FDR dates.",
      );
    if (
      b.deposit_type === "FDR" &&
      (!dateValid(b.issue_date) || !dateValid(b.maturity_date))
    )
      throw new Error("Valid calendar dates required.");
    if (!Number.isSafeInteger(amount) || amount <= 0 || amount > 1e12)
      throw new Error("Enter a positive supported amount in integer paise.");
    if (
      b.deposit_type === "FDR" &&
      (!b.issue_date ||
        !b.maturity_date ||
        String(b.maturity_date) < String(b.issue_date))
    )
      throw new Error("Valid FDR issue and maturity dates required.");
    if (
      !String(b.reference).startsWith("SYN-") ||
      !String(b.bank_code).startsWith("SYN")
    )
      throw new Error("Use SYN- references and a synthetic bank code.");
    if (
      state.deposits.some(
        (d) =>
          d.reference_last4 === String(b.reference).slice(-4) &&
          d.bank_code === b.bank_code,
      )
    )
      throw new Error(
        "This demo bank/reference suffix already exists. Choose a unique synthetic reference.",
      );
    const d: Schemas["DepositDetail"] = {
      id: uid(),
      institution_id: o.institution_id,
      obligation_id: o.id,
      deposit_type: String(b.deposit_type),
      bank_code: String(b.bank_code),
      reference_last4: String(b.reference).slice(-4),
      amount_paise: amount,
      issue_date: b.issue_date ? String(b.issue_date) : null,
      maturity_date: b.maturity_date ? String(b.maturity_date) : null,
      deposited_on: b.deposited_on ? String(b.deposited_on) : null,
      workflow: "DRAFT",
      verification_status: "UNVERIFIED",
      lifecycle_status: "RECORDED",
      version: 1,
      input_revision: 1,
      created_at: new Date().toISOString(),
      current_policy_revision: revision,
      evaluation_fresh: false,
      documents: [],
      evaluations: [],
      decisions: [],
    };
    state.deposits.unshift(d);
    audit("DEPOSIT_RECORDED", d.id);
    return d;
  }
  if (p[0] === "deposits" && p[1] && !read) {
    const d = getDeposit(p[1]);
    checkVersion(d, b);
    const action = p[2];
    if (action === "demo-evidence") {
      requireRole("institution");
      if (d.workflow !== "DRAFT")
        throw new Error("Evidence can be attached only to a draft.");
      const category = String(b.category ?? "DEPOSIT_PROOF");
      const old = d.documents.find((x) => x.active && x.category === category);
      const doc = sampleDocument(d, category);
      if (b.mode === "OCR_AI") {
        doc.processing_metadata.ocr_pages = 1;
        doc.processing_metadata.ai_status = "SIMULATED_ADVISORY";
        doc.processing_metadata.ai_proposals = [
          {
            field: "amount_paise",
            value: String(d.amount_paise),
            quote: `Amount (integer INR paise): ${d.amount_paise}`,
            page: 1,
            model: "SIMULATED_NO_MODEL_CALL",
            quote_linking_method: "BUNDLED_SAMPLE_REGION",
          },
        ];
      }
      if (b.mode === "WORKER_FAILURE") {
        doc.status = "FAILED";
        doc.scan_result =
          "SIMULATED worker failure after five attempts. Reviewer retry required.";
      }
      if (b.mode === "MALWARE") {
        doc.status = "REJECTED";
        doc.scan_result =
          "SIMULATED antivirus rejection. This sample is never downloadable or eligible evidence.";
        doc.evidence = [];
      }
      if (b.mode === "PENDING") {
        doc.status = "QUARANTINED";
        doc.scan_result = "SIMULATED quarantine awaiting worker.";
        doc.processing_metadata.demo_complete_at = Date.now() + 2000;
      }
      if (old) {
        old.active = false;
        doc.supersedes_id = old.id;
      }
      d.documents.push(doc);
      d.input_revision++;
      d.evaluation_fresh = false;
    } else if (action === "evaluate") {
      requireRole("institution", "reviewer");
      evaluate(d, state);
    } else if (action === "submit") {
      requireRole("institution");
      if (
        d.workflow !== "DRAFT" ||
        !d.evaluation_fresh ||
        !d.documents.some(
          (x) =>
            x.active && x.category === "DEPOSIT_PROOF" && x.status === "READY",
        ) ||
        d.documents.some((x) => x.active && x.status !== "READY")
      )
        throw new Error(
          "Fresh evaluation and sample proof required on a draft.",
        );
      d.workflow = "PENDING_SCRUTINY";
    } else if (action === "review") {
      requireRole("reviewer");
      requireText(b.reason);
      if (d.workflow !== "PENDING_SCRUTINY")
        throw new Error("Submit the draft before review.");
      if (b.decision === "ACCEPT_REGISTRATION") {
        if (
          !b.evidence_reviewed ||
          !d.evaluation_fresh ||
          d.evaluations[0]?.result.outcome !== "PASS" ||
          state.discrepancies.some(
            (x) => x.deposit_id === d.id && x.status === "OPEN",
          )
        )
          throw new Error(
            "Review evidence, correct findings, rerun evaluation and resolve discrepancies first.",
          );
        d.workflow = "ACCEPTED";
        d.verification_status = "MANUALLY_REVIEWED";
      } else if (b.decision === "RETURN") d.workflow = "DRAFT";
      else throw new Error("Unknown scrutiny decision.");
      d.decisions.unshift({
        decision: b.decision,
        reason: b.reason,
        actor: subject(state.role),
      });
    } else if (action === "correct") {
      requireRole("institution");
      if (d.workflow !== "DRAFT")
        throw new Error("Return the submission before correction.");
      if (
        !Number.isSafeInteger(b.amount_paise) ||
        Number(b.amount_paise) <= 0 ||
        Number(b.amount_paise) > 1e12
      )
        throw new Error("Positive integer paise required.");
      if (
        d.deposit_type === "FDR" &&
        (!b.issue_date ||
          !b.maturity_date ||
          String(b.maturity_date) < String(b.issue_date))
      )
        throw new Error("Check the FDR dates.");
      d.amount_paise = Number(b.amount_paise);
      d.issue_date = b.issue_date ? String(b.issue_date) : null;
      d.maturity_date = b.maturity_date ? String(b.maturity_date) : null;
      d.deposited_on = b.deposited_on ? String(b.deposited_on) : null;
      d.input_revision++;
      d.evaluation_fresh = false;
    } else if (action === "request-revalidation") {
      requireRole("institution", "reviewer");
      d.workflow = "DRAFT";
      d.evaluation_fresh = false;
      for (const c of state.cases.filter((c) => c.deposit_id === d.id)) {
        audit(
          "CLEARANCES_INVALIDATED_FOR_REVALIDATION",
          c.id,
          c.institution_id,
          { previous_clearances: clone(c.clearances) },
        );
        c.clearances = [];
        c.state = "DRAFT";
        c.approver = null;
        c.version++;
      }
    } else if (action === "bank-check") {
      requireRole("reviewer");
      const match =
        b.ledger_id === `SB-${d.reference_last4}` &&
        d.amount_paise === 350000000 &&
        d.institution_id === "inst0001-demo";
      state.exchanges.unshift({
        id: uid(),
        institution_id: d.institution_id,
        deposit_id: d.id,
        operation: "SIMULATED_BANK_CHECK",
        state:
          b.behavior === "DELAYED"
            ? "PENDING"
            : b.behavior === "TRANSIENT_FAILURE"
              ? "RETRYING"
              : "SUCCEEDED",
        ready_at:
          b.behavior === "NORMAL" || !b.behavior
            ? undefined
            : Date.now() + 3000,
        attempts: b.behavior === "TRANSIENT_FAILURE" ? 2 : 1,
        last_error:
          b.behavior === "TRANSIENT_FAILURE"
            ? "SIMULATED first transport attempt failed; browser retry scheduled."
            : null,
        remote_id: "SIMULATED-NO-REMOTE-SYSTEM",
        ledger_id: String(b.ledger_id),
        result: {
          outcome: match
            ? "SIMULATED_MATCH"
            : "SIMULATED_MISMATCH_OR_NOT_FOUND",
          observed: {
            fixture_only: true,
            amount_paise: d.id === "fdr00002-demo" ? 350000000 : d.amount_paise,
          },
          differences: match
            ? []
            : ["sample source does not match declaration"],
        },
      });
      d.verification_status = ["DELAYED", "TRANSIENT_FAILURE"].includes(
        String(b.behavior),
      )
        ? "PENDING_EXTERNAL"
        : match
          ? "SIMULATED_MATCH"
          : "SIMULATED_MISMATCH";
    } else
      throw new Error("This operation is not implemented in the browser demo.");
    d.version++;
    audit(action.toUpperCase().replaceAll("-", "_"), d.id, d.institution_id);
    return d;
  }
  if (path === "/release-cases" && !read) {
    requireRole("institution");
    const d = getDeposit(String(b.deposit_id));
    if (
      d.workflow !== "ACCEPTED" ||
      state.cases.some((c) => c.deposit_id === d.id)
    )
      throw new Error("Choose an accepted deposit without an existing case.");
    const c: State["cases"][number] = {
      id: uid(),
      deposit_id: d.id,
      institution_id: d.institution_id,
      reason: String(b.reason),
      policy_revision: revision,
      state: "DRAFT",
      version: 1,
      input_revision: d.input_revision,
      required_bureaus: ["PGRC", "VIGILANCE", "GRANTS"],
      maker: subject(state.role),
      approver: null,
      issuer: null,
      output_document_id: null,
      clearances: [],
      holds:
        b.reason !== "TERM_COMPLETED"
          ? [
              {
                id: uid(),
                active: true,
                kind: "REGULATORY_EXCEPTION",
                reason:
                  "Unknown exception requires independent evidence and human review.",
              },
            ]
          : [],
      documents: [],
      blockers: [],
      mode: "BROWSER_SIMULATION_NO_FINANCIAL_AUTHORITY",
    };
    state.cases.unshift(c);
    audit("CASE_CREATED", c.id);
    return c;
  }
  if (p[0] === "release-cases" && p[1] && !read) {
    const c = getCase(p[1]);
    checkVersion(c, b);
    const action = p[2];
    if (action === "demo-evidence") {
      requireRole("institution");
      if (c.state !== "DRAFT") throw new Error("Draft case required.");
      for (const category of [
        "REQUEST_LETTER",
        "AFFIDAVIT_6",
        "APPROVAL_LETTER",
        "EXTERNAL_BODY_NOC",
      ])
        if (!c.documents.some((d) => d.category === category))
          c.documents.push({
            ...sampleDocument(getDeposit(c.deposit_id), category),
          });
    } else if (action === "submit") {
      requireRole("institution");
      if (
        c.state !== "DRAFT" ||
        blockers(c).some(
          (x) => x.startsWith("Missing") || x.startsWith("Fresh"),
        )
      )
        throw new Error(
          "Draft with sample evidence and accepted deposit required.",
        );
      c.state = "CLEARANCES_PENDING";
    } else if (action === "clearances") {
      const bureau = p[3];
      if (
        !bindings().some(
          (b) =>
            b.role === "CLEARANCE" &&
            b.scope_type === "BUREAU" &&
            b.scope_id === bureau,
        )
      )
        throw new Error(
          "Only the matching bureau demo persona can record this clearance.",
        );
      if (
        c.state !== "CLEARANCES_PENDING" ||
        !c.required_bureaus.includes(bureau) ||
        c.clearances.some((x) => x.bureau === bureau)
      )
        throw new Error("No pending decision for this bureau.");
      requireText(b.reason);
      if (
        !c.documents.some(
          (d) => d.id === b.evidence_document_id && d.status === "READY",
        )
      )
        throw new Error("Case evidence required.");
      if (!["CLEARED", "REJECTED"].includes(String(b.decision)))
        throw new Error("Unknown clearance decision.");
      c.clearances.push({
        bureau,
        decision: b.decision,
        actor: subject(state.role),
        reason: b.reason,
        evidence_document_id: b.evidence_document_id,
      });
      if (
        !c.required_bureaus.some(
          (b) =>
            !c.clearances.some(
              (x) => x.bureau === b && x.decision === "CLEARED",
            ),
        )
      )
        c.state = "APPROVAL_REVIEW";
    } else if (action === "return") {
      requireRole("reviewer");
      requireText(b.reason);
      audit("RELEASE_RETURNED_CLEARANCES_INVALIDATED", c.id, c.institution_id, {
        reason: b.reason,
        previous_clearances: clone(c.clearances),
      });
      c.state = "DRAFT";
      c.clearances = [];
      c.approver = null;
    } else if (action === "holds" && p[4] === "resolve") {
      requireRole("approver");
      requireText(b.resolution, 20);
      const hold = c.holds.find((h) => h.id === p[3]);
      const doc = c.documents.find(
        (d) => d.id === b.evidence_document_id && d.status === "READY",
      );
      if (
        !hold ||
        !doc ||
        (hold.kind === "FINANCIAL_EMBEZZLEMENT" &&
          doc.category !== "EXTERNAL_BODY_NOC")
      )
        throw new Error("Required independent hold evidence missing.");
      hold.active = false;
      hold.resolution = b.resolution;
    } else if (action === "holds") {
      requireRole("reviewer", "approver");
      requireText(b.reason);
      if (c.state === "ISSUED_SYNTHETIC")
        throw new Error("Issued example is closed.");
      c.holds.push({
        id: uid(),
        active: true,
        reason: b.reason,
        kind: b.kind,
        actor: subject(state.role),
      });
    } else if (action === "approve") {
      requireRole("approver");
      requireText(b.regulatory_basis, 30);
      if (!["CLEARANCES_PENDING", "APPROVAL_REVIEW"].includes(c.state))
        throw new Error("Case not awaiting approval.");
      const open = blockers(c);
      if (open.length) throw new Error(`Approval blocked: ${open.join("; ")}`);
      if (
        !b.synthetic_acknowledgement ||
        c.maker === subject(state.role) ||
        c.clearances.some((x) => x.actor === subject(state.role))
      )
        throw new Error(
          "Independent approver and synthetic acknowledgement required.",
        );
      c.state = "APPROVED_SYNTHETIC";
      c.approver = subject(state.role);
    } else if (action === "issue-document") {
      requireRole("issuer");
      if (
        c.state !== "APPROVED_SYNTHETIC" ||
        blockers(c).length ||
        c.approver === subject(state.role)
      )
        throw new Error("Independent approval and all gates required.");
      c.state = "ISSUED_SYNTHETIC";
      c.issuer = subject(state.role);
      c.output_document_id = `output-${c.id}`;
    } else if (action === "sandbox-exchange") {
      requireRole("issuer");
      if (c.state !== "ISSUED_SYNTHETIC")
        throw new Error("Issue the synthetic output first.");
      state.exchanges.unshift({
        id: uid(),
        institution_id: c.institution_id,
        case_id: c.id,
        operation: "SIMULATED_CASE_EXCHANGE",
        state:
          b.behavior === "DELAYED"
            ? "PENDING"
            : b.behavior === "TRANSIENT_FAILURE"
              ? "RETRYING"
              : "SUCCEEDED",
        ready_at: ["DELAYED", "TRANSIENT_FAILURE"].includes(String(b.behavior))
          ? Date.now() + 3000
          : undefined,
        attempts: 1,
        last_error:
          b.behavior === "TRANSIENT_FAILURE"
            ? "SIMULATED first-attempt failure."
            : null,
        remote_id: "SIMULATED-NO-REMOTE-SYSTEM",
        ledger_id: b.ledger_id ? String(b.ledger_id) : null,
        result: { outcome: "SIMULATED_RECEIPT_NO_SETTLEMENT" },
      });
    } else throw new Error("Unsupported demo case action.");
    c.version++;
    c.blockers = blockers(c);
    audit(String(action).toUpperCase(), c.id, c.institution_id);
    return c;
  }
  if (p[0] === "institutions" && p[2] === "registry-check" && !read) {
    requireRole("institution", "reviewer");
    const i = state.institutions.find((i) => i.id === p[1]);
    if (!i) throw new Error("Institution not found.");
    const known = i.external_id === "SYNTHETIC-001";
    i.registry_status = known
      ? "SIMULATED_REGISTRY_MATCH"
      : "SIMULATED_NOT_FOUND";
    state.exchanges.unshift({
      id: uid(),
      institution_id: i.id,
      operation: "SIMULATED_REGISTRY_CHECK",
      state:
        b.behavior === "DELAYED"
          ? "PENDING"
          : b.behavior === "TRANSIENT_FAILURE"
            ? "RETRYING"
            : "SUCCEEDED",
      ready_at: ["DELAYED", "TRANSIENT_FAILURE"].includes(String(b.behavior))
        ? Date.now() + 3000
        : undefined,
      attempts: 1,
      last_error: null,
      remote_id: "SIMULATED-NO-REMOTE-SYSTEM",
      ledger_id: null,
      result: {
        outcome: known ? "SIMULATED_MATCH" : "SIMULATED_NOT_FOUND",
        observed: { fixture_only: true, external_id: i.external_id },
      },
    });
    audit("REGISTRY_CHECK", i.id);
    return i;
  }
  if (p[0] === "documents" && p[2] === "corrections" && !read) {
    requireRole("institution", "reviewer");
    const d = state.deposits.find((d) =>
      d.documents.some((x) => x.id === p[1]),
    );
    if (!d || d.workflow === "ACCEPTED")
      throw new Error("Editable sample evidence required.");
    requireText(b.reason);
    if (
      ![
        "amount_paise",
        "issue_date",
        "maturity_date",
        "institution_external_id",
      ].includes(String(b.field))
    )
      throw new Error("Unsupported evidence field.");
    const bounds = b.bounds as number[];
    if (
      !String(b.quote ?? "").trim() ||
      !documentLines(p[1]).join("\n").includes(String(b.quote))
    )
      throw new Error(
        "Source transcription must be present in the bundled sample PDF; unsupported proposals stay unconfirmed.",
      );
    if (
      !Array.isArray(bounds) ||
      bounds.length !== 4 ||
      bounds.some((n) => !Number.isFinite(n) || n < 0) ||
      bounds[2] <= bounds[0] ||
      bounds[3] <= bounds[1] ||
      bounds[2] > 595 ||
      bounds[3] > 842
    )
      throw new Error("Select a valid sample page region.");
    state.corrections.push({
      id: uid(),
      document_id: p[1],
      deposit_id: d.id,
      field: String(b.field),
      value: String(b.value),
      quote: String(b.quote),
      reason: String(b.reason),
      status: "PROPOSED",
      maker: subject(state.role),
      checker: null,
      page: Number(b.page),
      bounds,
    });
    d.version++;
    audit("CORRECTION_PROPOSED", d.id);
    return d;
  }
  if (p[0] === "documents" && p[2] === "retry" && !read) {
    requireRole("reviewer");
    const d = state.deposits.find((d) =>
      d.documents.some((doc) => doc.id === p[1]),
    );
    const doc = d?.documents.find((doc) => doc.id === p[1]);
    if (!d || !doc || doc.status !== "FAILED")
      throw new Error(
        "Only failed processing can be retried; unsafe evidence stays blocked.",
      );
    checkVersion(d, b);
    doc.status = "QUARANTINED";
    doc.processing_metadata.demo_complete_at = Date.now() + 1200;
    doc.scan_result =
      "SIMULATED worker retry queued. No real worker runs in this demo.";
    d.version++;
    d.evaluation_fresh = false;
    audit("DOCUMENT_RETRY_QUEUED", d.id);
    return doc;
  }
  if (p[0] === "integration-requests" && p[2] === "retry" && !read) {
    requireRole("reviewer", "issuer");
    const x = state.exchanges.find((x) => x.id === p[1]);
    if (!x || x.state !== "DEAD_LETTER")
      throw new Error("Only a dead-letter exchange can be retried.");
    if (Number(b.expected_version) !== x.attempts)
      throw new Error("Refresh this exchange first.");
    x.state = "RETRYING";
    x.attempts++;
    x.ready_at = Date.now() + 1500;
    x.last_error = "SIMULATED retry awaiting completion.";
    audit("SOURCE_RETRY_QUEUED", x.id);
    return x;
  }
  if (p[0] === "notifications" && p[2] === "retry" && !read) {
    requireRole("reviewer");
    const n = state.notifications.find((n) => n.id === p[1]);
    if (
      !n ||
      n.delivery.state !== "DEAD_LETTER" ||
      n.delivery.attempts !== Number(b.expected_version)
    )
      throw new Error("Refresh a failed notification before retrying.");
    n.delivery.state = "SIMULATED_NOT_SENT";
    n.delivery.attempts++;
    n.delivery.last_error = null;
    audit("EMAIL_RETRY_SIMULATED", n.id);
    return n;
  }
  if (p[0] === "corrections" && p[2] === "decision" && !read) {
    requireRole("reviewer");
    requireText(b.reason);
    const c = state.corrections.find((c) => c.id === p[1]);
    if (!c || c.maker === subject(state.role) || c.status !== "PROPOSED")
      throw new Error("Independent checker required on a pending proposal.");
    if (!["CONFIRMED", "REJECTED"].includes(String(b.decision)))
      throw new Error("Unknown decision.");
    c.status = String(b.decision);
    c.checker = subject(state.role);
    const d = getDeposit(c.deposit_id);
    d.version++;
    d.input_revision++;
    d.evaluation_fresh = false;
    audit("CORRECTION_DECIDED", d.id);
    return c;
  }
  if (p[0] === "discrepancies" && p[2] === "resolve" && !read) {
    requireRole("reviewer");
    requireText(b.reason);
    const discrepancy = state.discrepancies.find((x) => x.id === p[1]);
    if (!discrepancy) throw new Error("Finding not found.");
    const d = getDeposit(discrepancy.deposit_id);
    if (
      !d.evaluation_fresh ||
      d.evaluations[0]?.result.outcome !== "PASS" ||
      !d.documents.some((x) => x.id === b.evidence_document_id && x.active)
    )
      throw new Error(
        "Correct inputs and obtain a fresh passing sample evaluation first.",
      );
    discrepancy.status = "RESOLVED";
    discrepancy.resolution = String(b.reason);
    d.version++;
    audit("DISCREPANCY_RESOLVED", d.id);
    return discrepancy;
  }
  if (path === "/replacements" && !read) {
    requireRole("institution");
    requireText(b.rationale, 20);
    const old = getDeposit(String(b.old_deposit_id)),
      next = getDeposit(String(b.new_deposit_id));
    if (
      old.id === next.id ||
      old.institution_id !== next.institution_id ||
      old.workflow !== "ACCEPTED" ||
      next.workflow !== "ACCEPTED" ||
      !old.maturity_date ||
      !next.maturity_date ||
      next.maturity_date <= old.maturity_date ||
      old.lifecycle_status === "REPLACED"
    )
      throw new Error(
        "Choose distinct accepted instruments with a later covering maturity.",
      );
    if (state.relations.some((r) => r.old_deposit_id === old.id))
      throw new Error("This example already has a lineage request.");
    const r = {
      id: uid(),
      institution_id: old.institution_id,
      old_deposit_id: old.id,
      new_deposit_id: next.id,
      kind: String(b.kind),
      state: "REQUESTED",
      version: 1,
      maker: subject(state.role),
    };
    state.relations.push(r);
    audit("LINEAGE_REQUESTED", r.id);
    return r;
  }
  if (p[0] === "replacements" && p[2] === "approve" && !read) {
    requireRole("reviewer");
    requireText(b.policy_basis, 20);
    const r = state.relations.find((r) => r.id === p[1]);
    if (!r || r.state !== "REQUESTED" || r.maker === subject(state.role))
      throw new Error("Pending independent lineage review required.");
    checkVersion(r, b);
    getDeposit(r.old_deposit_id).lifecycle_status = "REPLACED";
    getDeposit(r.old_deposit_id).version++;
    r.state = "APPROVED";
    r.version++;
    audit("LINEAGE_AUTHORIZED", r.id);
    return r;
  }
  if (path === "/monitoring/run" && !read) {
    requireRole("reviewer");
    const asOf = String(b.as_of ?? clock);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(asOf))
      throw new Error("Valid demo date required.");
    for (const d of state.deposits) {
      if (!d.maturity_date || d.lifecycle_status === "REPLACED") continue;
      const days = Math.ceil(
        (Date.parse(d.maturity_date) - Date.parse(asOf)) / 86400000,
      );
      d.lifecycle_status =
        days <= 0 ? "MATURED" : days <= 90 ? "APPROACHING_MATURITY" : "ACTIVE";
      const bands = [
        ...(state.policies[d.institution_id]?.configuration.maturity_days ?? [
          90, 30, 7,
        ]),
      ].sort((a, b) => a - b);
      const threshold = days <= 0 ? 0 : bands.find((n) => days <= n);
      if (
        threshold === undefined ||
        state.notifications.some(
          (n) => n.deposit_id === d.id && n.detail.threshold === threshold,
        )
      )
        continue;
      state.notifications.push({
        id: uid(),
        deposit_id: d.id,
        kind: "MATURITY_IN_APP",
        recipient: "demo-institution",
        detail: { days_remaining: days, threshold, as_of: asOf },
        delivery: {
          id: uid(),
          state: "SIMULATED_NOT_SENT",
          attempts: 0,
          last_error: null,
          message_id: "NO_EMAIL_SENT",
        },
      });
    }
    audit("MATURITY_MONITOR", state.institutions[0].id);
    return {};
  }
  if (path === "/operations/scan" && !read) {
    requireRole("reviewer");
    syncTasks();
    const asOf = b.as_of
      ? Date.parse(String(b.as_of))
      : Date.parse(`${clock}T12:00:00Z`);
    if (!Number.isFinite(asOf))
      throw new Error("Valid synthetic scan clock required.");
    for (const t of state.tasks.filter(
      (t) =>
        t.state === "OPEN" &&
        (!b.institution_id || t.institution_id === b.institution_id),
    )) {
      const policy = state.policies[t.institution_id] ?? defaultPolicy();
      if (asOf < Date.parse(t.due_at)) continue;
      const escalated =
        asOf >=
          Date.parse(t.due_at) +
            policy.configuration.escalation_hours * 3600000 &&
        !!policy.configuration.supervisor_subject;
      const kind = escalated ? "SIMULATED_ESCALATION" : "SIMULATED_REMINDER";
      if (
        !state.notifications.some(
          (n) => n.intervention_id === t.id && n.kind === kind,
        )
      )
        state.notifications.push({
          id: uid(),
          intervention_id: t.id,
          deposit_id: t.deposit_id ?? "",
          kind,
          recipient: escalated
            ? policy.configuration.supervisor_subject!
            : "demo-reviewer",
          detail: {
            days_remaining: 0,
            threshold: 0,
            as_of: new Date(asOf).toISOString(),
          },
          delivery: {
            id: uid(),
            state: "SIMULATED_NOT_SENT",
            attempts: 0,
            last_error: null,
            message_id: "NO_EMAIL_SENT",
          },
        });
    }
    audit("INTERVENTION_SCAN", state.institutions[0].id);
    return {};
  }
  if (p[0] === "interventions" && p[2] === "acknowledge" && !read) {
    requireRole("reviewer");
    requireText(b.reason);
    const t = state.tasks.find((t) => t.id === p[1]);
    if (!t) throw new Error("Task not found.");
    t.acknowledged_by = subject(state.role);
    t.acknowledgement = String(b.reason);
    audit("FOLLOW_UP_ACKNOWLEDGED", t.id);
    return t;
  }
  if (p[0] === "institutions" && p[2] === "operations-policy" && !read) {
    requireRole("reviewer");
    requireText(b.reason);
    const policy = state.policies[p[1]] ?? defaultPolicy();
    if (Number(b.expected_revision) !== policy.revision)
      throw new Error("Refresh the policy revision.");
    const config = {
      review_hours: Number(b.review_hours),
      verification_hours: Number(b.verification_hours),
      discrepancy_hours: Number(b.discrepancy_hours),
      missing_document_hours: Number(b.missing_document_hours),
      clearance_hours: Number(b.clearance_hours),
      escalation_hours: Number(b.escalation_hours),
      maturity_days: b.maturity_days as number[],
      supervisor_subject: b.supervisor_subject
        ? String(b.supervisor_subject)
        : null,
    };
    if (
      Object.entries(config).some(
        ([key, val]) =>
          key.endsWith("_hours") &&
          (!Number.isInteger(val) || Number(val) < 1 || Number(val) > 8760),
      ) ||
      !Array.isArray(config.maturity_days) ||
      config.maturity_days.some(
        (n) => !Number.isInteger(n) || n <= 0 || n > 3650,
      ) ||
      (config.supervisor_subject &&
        !policy.supervisor_candidates.includes(config.supervisor_subject))
    )
      throw new Error(
        "Valid product policy configuration and independent supervisor required.",
      );
    policy.configuration = clone(config);
    policy.revision++;
    state.policies[p[1]] = policy;
    audit("PRODUCT_POLICY_CHANGED", p[1]);
    return policy;
  }
  if (path === "/operator/assignments" && !read) {
    requireRole("operator");
    requireText(b.reason);
    if (b.subject === "demo-operator" || b.role === "OPERATOR")
      throw new Error("Self-grants and operator grants are prohibited.");
    const a = {
      id: uid(),
      subject: String(b.subject),
      role: String(b.role),
      scope_type: String(b.scope_type),
      scope_id: String(b.scope_id),
      enabled: b.enabled === true,
      valid_until: b.valid_until
        ? String(b.valid_until)
        : new Date(Date.parse(clock) + 30 * 86400000).toISOString(),
    };
    if (
      !personas.some(([r]) => subject(r) === a.subject) ||
      !["REVIEWER", "AUDITOR", "CLEARANCE", "APPROVER", "ISSUER"].includes(
        a.role,
      )
    )
      throw new Error("Select a supported fictional officer and role.");
    const existing = state.assignments.find(
      (x) =>
        x.subject === a.subject &&
        x.role === a.role &&
        x.scope_type === a.scope_type &&
        x.scope_id === a.scope_id,
    );
    if (existing) Object.assign(existing, a, { id: existing.id });
    else state.assignments.push(a);
    audit("SCOPE_ASSIGNMENT_SIMULATED", a.id);
    return a;
  }
  if (p[0] === "legacy-import" && !read) {
    requireRole("institution");
    if (p[1] === "demo-preview")
      return {
        sha256: "BUNDLED_DEMO_TEMPLATE",
        rows: 1,
        declared_total_paise: "350000000",
        note: "One bundled synthetic FDR. No arbitrary file was parsed. Commit creates a DRAFT requiring evidence and review.",
      };
    if (p[1] === "demo-commit") {
      if (b.expected_sha256 !== "BUNDLED_DEMO_TEMPLATE")
        throw new Error("Preview the bundled sample first.");
      route(
        "/deposits",
        {
          obligation_id: state.obligations[0].id,
          deposit_type: "FDR",
          bank_code: "SYN-BANK",
          reference: "SYN-LEGACY-0090",
          amount_paise: 350000000,
          issue_date: "2016-10-01",
          maturity_date: "2026-10-01",
        },
        "POST",
      );
      audit("BUNDLED_LEGACY_IMPORTED", state.institutions[0].id);
      return { rows: 1 };
    }
  }
  throw new Error(
    "This action needs the backend-connected application. It is not simulated in this browser demo.",
  );
}

function csv(rows: Record<string, unknown>[]) {
  const columns = Object.keys(rows[0] ?? { note: "" });
  const cell = (value: unknown) =>
    `"${String(value ?? "")
      .replace(/^[=+\-@\t\r]/, "'$&")
      .replaceAll('"', '""')}"`;
  return new Blob(
    [
      [
        columns.map(cell).join(","),
        ...rows.map((r) => columns.map((c) => cell(r[c])).join(",")),
      ].join("\r\n"),
    ],
    { type: "text/csv;charset=utf-8" },
  );
}
export function demoCsv(path: string) {
  const url = new URL(path, "https://demo.invalid");
  audit("CSV_EXPORTED", state.institutions[0].id);
  save();
  if (url.pathname.includes("interventions"))
    return csv(
      report(url.searchParams, true).items.map((t) => ({
        ...t,
        detail: JSON.stringify(t.detail),
      })),
    );
  return csv(
    search(url.searchParams, true).map((d) => ({
      record: d.id,
      bank: d.bank_code,
      reference_last4: d.reference_last4,
      amount_paise: d.amount_paise,
      workflow: d.workflow,
      verification: d.verification_status,
      mode: "BROWSER_SIMULATION",
    })),
  );
}
export function documentLines(id: string): string[] {
  const d = state.deposits.find(
    (d) => d.id === id || d.documents.some((doc) => doc.id === id),
  );
  const c = state.cases.find(
    (c) =>
      c.id === id ||
      c.output_document_id === id ||
      c.documents.some((doc) => doc.id === id),
  );
  const deposit = d ?? (c ? getDeposit(c.deposit_id) : null);
  if (!deposit) throw new Error("Sample document not found.");
  const doc =
    d?.documents.find((doc) => doc.id === id) ??
    c?.documents.find((doc) => doc.id === id);
  if (doc && doc.status !== "READY")
    throw new Error(
      "Quarantined, rejected or failed evidence is not downloadable.",
    );
  const amount =
    doc?.evidence && Array.isArray(doc.evidence)
      ? ((doc.evidence as Record<string, unknown>[]).find(
          (e) => e.field === "amount_paise",
        )?.value ?? deposit.amount_paise)
      : deposit.amount_paise;
  const snapshot =
    doc &&
    typeof doc.processing_metadata === "object" &&
    doc.processing_metadata
      ? ((doc.processing_metadata as Record<string, unknown>).demo_snapshot as
          Record<string, unknown> | undefined)
      : undefined;
  return [
    "FDR SENTINEL - SYNTHETIC DEMO",
    "NO FINANCIAL VALUE / NO OFFICIAL AUTHORITY",
    "",
    c?.output_document_id === id
      ? ["FDR", "RPGF"].includes(deposit.deposit_type)
        ? "SAMPLE NOC - NOT AN OFFICIAL DOCUMENT"
        : "SAMPLE SANCTION - NOT AN OFFICIAL DOCUMENT"
      : String(doc?.category ?? "SAMPLE EVIDENCE"),
    `Deposit: ${deposit.id}`,
    `Institution: ${deposit.institution_id}`,
    `Amount (integer INR paise): ${snapshot?.amount_paise ?? amount}`,
    `Issue / deposit date: ${snapshot?.issue_date ?? deposit.issue_date ?? deposit.deposited_on}`,
    `Maturity date: ${snapshot?.maturity_date ?? deposit.maturity_date ?? "Not applicable"}`,
    "",
    "Bundled browser demonstration. Extraction is precomputed.",
    "No antivirus, bank API, AI model or financial release executed.",
  ];
}
