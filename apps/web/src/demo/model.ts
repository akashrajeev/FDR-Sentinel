import type { Schemas } from "../api";

export const revision = "DEMO-FIXTURE-1-PROVISIONAL";
export const clock = "2026-10-27";
export const personas = [
  ["reviewer", "Review officer"],
  ["institution", "Institution maker"],
  ["pgrc", "PGRC officer"],
  ["vigilance", "Vigilance officer"],
  ["grants", "Grants officer"],
  ["approver", "Independent approver"],
  ["issuer", "Document issuer"],
  ["auditor", "Auditor"],
  ["operator", "Technical operator"],
] as const;
export type Persona = (typeof personas)[number][0];
export type Binding = { role: string; scope_type: string; scope_id: string };
export type Correction = {
  id: string;
  document_id: string;
  deposit_id: string;
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
export type Discrepancy = {
  id: string;
  deposit_id: string;
  status: string;
  finding: { code: string; field: string; message: string };
  resolution: string | null;
};
export type Exchange = {
  ready_at?: number;
  id: string;
  institution_id: string;
  deposit_id?: string;
  case_id?: string;
  operation: string;
  state: string;
  attempts: number;
  last_error: string | null;
  remote_id: string;
  ledger_id: string | null;
  result: {
    outcome: string;
    observed?: Record<string, unknown>;
    differences?: string[];
  };
};
export type Relation = {
  id: string;
  institution_id: string;
  old_deposit_id: string;
  new_deposit_id: string;
  kind: string;
  state: string;
  version: number;
  maker: string;
};
export type Task = {
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
export type Notification = {
  id: string;
  kind: string;
  deposit_id: string;
  intervention_id?: string;
  recipient: string;
  detail: { days_remaining: number; threshold: number; as_of: string };
  delivery: {
    id: string;
    state: string;
    attempts: number;
    last_error: string | null;
    message_id: string;
  };
};
export type Policy = {
  revision: number;
  configuration: {
    review_hours: number;
    verification_hours: number;
    discrepancy_hours: number;
    missing_document_hours: number;
    clearance_hours: number;
    escalation_hours: number;
    maturity_days: number[];
    supervisor_subject: string | null;
  };
  supervisor_candidates: string[];
};
export type State = {
  schema: 1;
  role: Persona;
  institutions: Schemas["InstitutionOut"][];
  obligations: Schemas["ObligationOut"][];
  deposits: Schemas["DepositDetail"][];
  cases: (Schemas["ReleaseOut"] & { maker: string })[];
  audit: Schemas["AuditOut"][];
  corrections: Correction[];
  discrepancies: Discrepancy[];
  exchanges: Exchange[];
  relations: Relation[];
  tasks: Task[];
  notifications: Notification[];
  policies: Record<string, Policy>;
  assignments: (Binding & {
    id: string;
    subject: string;
    enabled: boolean;
    valid_until: string | null;
  })[];
};
export const uid = () => crypto.randomUUID();
export const subject = (role: Persona) => `demo-${role}`;
export function defaultPolicy(): Policy {
  return {
    revision: 1,
    configuration: {
      review_hours: 48,
      verification_hours: 24,
      discrepancy_hours: 24,
      missing_document_hours: 24,
      clearance_hours: 48,
      escalation_hours: 24,
      maturity_days: [90, 30, 7],
      supervisor_subject: "demo-auditor",
    },
    supervisor_candidates: ["demo-auditor", "demo-approver"],
  };
}
export function sampleDocument(
  deposit: Schemas["DepositDetail"],
  category = "DEPOSIT_PROOF",
): Schemas["DocumentOut"] {
  return {
    id: uid(),
    deposit_id: deposit.id,
    category,
    active: true,
    supersedes_id: null,
    sha256: "BUNDLED_SYNTHETIC_SAMPLE_NOT_A_SOURCE_DOCUMENT_HASH",
    size: 0,
    status: "READY",
    scan_result:
      "Bundled synthetic example. Antivirus and extraction are simulated; no file was scanned.",
    evidence:
      category === "DEPOSIT_PROOF"
        ? [
            {
              field: "amount_paise",
              value:
                deposit.id === "fdr00002-demo"
                  ? 350000000
                  : deposit.amount_paise,
              page: 1,
              method: "PRECOMPUTED_DEMO",
              offset: 0,
              bounds: [55, 160, 540, 195],
            },
            {
              field: "issue_date",
              value: deposit.issue_date ?? deposit.deposited_on,
              page: 1,
              method: "PRECOMPUTED_DEMO",
              offset: 60,
              bounds: [55, 210, 540, 240],
            },
            {
              field: "maturity_date",
              value: deposit.maturity_date,
              page: 1,
              method: "PRECOMPUTED_DEMO",
              offset: 90,
              bounds: [55, 250, 540, 280],
            },
          ]
        : [],
    processing_metadata: {
      demo_snapshot: {
        amount_paise:
          deposit.id === "fdr00002-demo" ? 350000000 : deposit.amount_paise,
        issue_date: deposit.issue_date ?? deposit.deposited_on,
        maturity_date: deposit.maturity_date,
      },
      page_sizes: [[595, 842]],
      algorithm: "PRECOMPUTED_BROWSER_DEMO",
      ocr_pages: 0,
      ai_status: "SIMULATED_NO_MODEL_CALL",
    },
  };
}
export function evaluate(deposit: Schemas["DepositDetail"], state: State) {
  const obligation = state.obligations.find(
    (o) => o.id === deposit.obligation_id,
  )!;
  const proof = deposit.documents.find(
    (d) => d.active && d.category === "DEPOSIT_PROOF",
  );
  const extracted = proof?.evidence.find(
    (e) => e.field === "amount_paise",
  )?.value;
  const correction = state.corrections.find(
    (c) =>
      c.deposit_id === deposit.id &&
      c.status === "CONFIRMED" &&
      c.field === "amount_paise",
  );
  const findings: Record<string, unknown>[] = [];
  if (!proof)
    findings.push({
      code: "MISSING_PROOF",
      severity: "FAIL",
      message: "Attach the bundled synthetic proof before evaluation.",
    });
  if (deposit.documents.some((d) => d.active && d.status !== "READY"))
    findings.push({
      code: "UNSAFE_EVIDENCE",
      severity: "FAIL",
      message:
        "Processing failed, is pending or evidence is quarantined/rejected. No acceptance until safe sample processing completes.",
    });
  if (
    extracted != null &&
    Number(correction?.value ?? extracted) !== deposit.amount_paise
  )
    findings.push({
      code: "AMOUNT_MISMATCH",
      severity: "FAIL",
      message:
        "Declared amount differs from the sample document. Return to the maker for correction.",
      citation: "Document consistency check; not a bank authentication result.",
    });
  if (obligation.required_amount_paise == null)
    findings.push({
      code: "REQUIRES_HUMAN_REVIEW",
      severity: "REVIEW",
      message:
        "This context is outside the simple demo fixture. Independent source and applicability review required.",
    });
  else if (deposit.amount_paise < obligation.required_amount_paise)
    findings.push({
      code: "SHORTFALL",
      severity: "FAIL",
      message: "Declared amount is below this provisional sample obligation.",
      citation: "APH 2024-27, 1.12 / Table 1.4: provisional fixture only.",
    });
  findings.push({
    code: "PROVISIONAL_SOURCE",
    severity: "INFO",
    message:
      "Browser simulation. Current amendments and real applicability have not been certified.",
    citation: "APH 2024-27 clauses 1.12 / 6.46; illustrative only.",
  });
  deposit.evaluations.unshift({
    id: uid(),
    input_revision: deposit.input_revision,
    policy_revision: revision,
    document_set_hash: "DEMO_ONLY",
    evaluated_at: new Date().toISOString(),
    result: {
      outcome: findings.some((f) => f.severity === "FAIL")
        ? "FAIL"
        : findings.some((f) => f.severity === "REVIEW")
          ? "REQUIRES_HUMAN_REVIEW"
          : "PASS",
      findings,
    },
  });
  deposit.evaluation_fresh = true;
}
export function seed(): State {
  const institution: Schemas["InstitutionOut"] = {
    id: "inst0001-demo",
    external_id: "SYNTHETIC-001",
    legal_name: "Synthetic Institute of Technology",
    registry_status: "SIMULATED_REGISTRY_MATCH",
    context: {
      academic_year: "2026-27",
      governance: "PRIVATE",
      programme: "ENGINEERING",
      level: "UG",
      land: "OWNED",
      exceptional_context: false,
    },
  };
  const state: State = {
    schema: 1,
    role: "reviewer",
    institutions: [institution],
    obligations: [
      {
        id: "oblg0001-demo",
        institution_id: institution.id,
        regulatory_event: "NEW_INSTITUTION",
        coverage_mode: "SINGLE_RECORD",
        context: institution.context,
        status: "PROVISIONAL",
        policy_revision: revision,
        required_amount_paise: 350000000,
      },
    ],
    deposits: [],
    cases: [],
    audit: [],
    corrections: [],
    discrepancies: [],
    exchanges: [],
    relations: [],
    tasks: [],
    notifications: [],
    policies: { [institution.id]: defaultPolicy() },
    assignments: [],
  };
  const definitions = [
    ["fdr00001-demo", "DRAFT", "2026-10-01", 350000000, "0001"],
    ["fdr00002-demo", "PENDING_SCRUTINY", "2026-10-01", 300000000, "0002"],
    ["fdr00003-demo", "ACCEPTED", "2026-10-01", 350000000, "0003"],
    ["fdr00004-demo", "ACCEPTED", "2026-10-01", 350000000, "0004"],
    ["fdr00005-demo", "ACCEPTED", "2026-11-20", 350000000, "0005"],
    ["fdr00006-demo", "ACCEPTED", "2036-10-01", 350000000, "0006"],
    ["rtgs0007-demo", "ACCEPTED", null, 350000000, "0007"],
    ["fdr00008-demo", "DRAFT", "2026-10-01", 350000000, "0008"],
    ["fdr00009-demo", "DRAFT", "2026-10-01", 350000000, "0009"],
    ["fdr00010-demo", "ACCEPTED", "2026-10-01", 350000000, "0010"],
    ["fdr00011-demo", "DRAFT", "2026-10-01", 350000000, "0011"],
    ["rpgf0012-demo", "ACCEPTED", null, 350000000, "0012"],
    ["online13-demo", "ACCEPTED", null, 350000000, "0013"],
    ["legacy14-demo", "DRAFT", null, 350000000, "0014"],
  ] as const;
  for (const [id, workflow, maturity, amount, last4] of definitions) {
    const d: Schemas["DepositDetail"] = {
      id,
      institution_id: institution.id,
      obligation_id: state.obligations[0].id,
      deposit_type: id.startsWith("rpgf")
        ? "RPGF"
        : id.startsWith("online")
          ? "ONLINE"
          : id.startsWith("legacy")
            ? "OTHER_LEGACY"
            : maturity
              ? "FDR"
              : "RTGS",
      bank_code: "SYN-BANK",
      reference_last4: last4,
      amount_paise: amount,
      issue_date: maturity
        ? id === "fdr00006-demo"
          ? "2026-10-01"
          : "2016-10-01"
        : null,
      maturity_date: maturity,
      deposited_on: maturity ? null : "2016-10-01",
      workflow,
      verification_status:
        workflow === "ACCEPTED" ? "MANUALLY_REVIEWED" : "UNVERIFIED",
      lifecycle_status: maturity && maturity < clock ? "MATURED" : "ACTIVE",
      version: 1,
      input_revision: 1,
      created_at: "2026-10-26T09:00:00Z",
      current_policy_revision: revision,
      evaluation_fresh: false,
      documents: [],
      evaluations: [],
      decisions: [],
    };
    if (id !== "fdr00001-demo") {
      d.documents.push(sampleDocument(d));
      evaluate(d, state);
    }
    if (workflow === "ACCEPTED")
      d.decisions.push({
        decision: "ACCEPT_REGISTRATION",
        actor: "demo-reviewer",
        reason: "Preloaded synthetic review example; no legal certification.",
      });
    if (id === "fdr00008-demo") {
      d.documents[0].evidence[0].value = 35000000;
      d.documents[0].processing_metadata.ocr_pages = 1;
      d.documents[0].processing_metadata.ai_status = "SIMULATED_ADVISORY";
      d.documents[0].processing_metadata.ai_proposals = [
        {
          field: "amount_paise",
          value: "350000000",
          quote: "Amount (integer INR paise): 350000000",
          page: 1,
          model: "SIMULATED_NO_MODEL_CALL",
          quote_linking_method: "BUNDLED_SAMPLE_REGION",
        },
      ];
      evaluate(d, state);
    }
    if (id === "fdr00009-demo") {
      d.documents[0].status = "FAILED";
      d.documents[0].scan_result =
        "SIMULATED worker outage. Reviewer retry required.";
      d.evaluation_fresh = false;
    }
    if (id === "fdr00010-demo") d.evaluation_fresh = false;
    if (id === "fdr00011-demo") {
      const o = {
        ...state.obligations[0],
        id: "oblg0002-demo",
        status: "REQUIRES_HUMAN_REVIEW",
        required_amount_paise: null,
        context: { ...institution.context, exceptional_context: true },
      };
      state.obligations.push(o);
      d.obligation_id = o.id;
      evaluate(d, state);
    }
    state.deposits.push(d);
  }
  state.discrepancies.push({
    id: "disc0001-demo",
    deposit_id: "fdr00002-demo",
    status: "OPEN",
    finding: {
      code: "AMOUNT_MISMATCH",
      field: "amount_paise",
      message: "Declared INR 30 lakh; sample evidence states INR 35 lakh.",
    },
    resolution: null,
  });
  for (const [id, dep, held] of [
    ["case0001-demo", "fdr00003-demo", false],
    ["case0002-demo", "fdr00004-demo", true],
    ["case0003-demo", "rtgs0007-demo", false],
  ] as const) {
    const d = state.deposits.find((d) => d.id === dep)!;
    state.cases.push({
      id,
      deposit_id: dep,
      institution_id: institution.id,
      reason: "TERM_COMPLETED",
      policy_revision: revision,
      state: "CLEARANCES_PENDING",
      version: 1,
      input_revision: 1,
      required_bureaus: ["PGRC", "VIGILANCE", "GRANTS"],
      maker: "demo-institution",
      approver: null,
      issuer: null,
      output_document_id: null,
      clearances: ["VIGILANCE", "GRANTS"].map((bureau) => ({
        bureau,
        decision: "CLEARED",
        actor: `demo-${bureau.toLowerCase()}`,
        reason: "Preloaded independent synthetic clearance.",
      })),
      holds: held
        ? [
            {
              id: "hold0001-demo",
              active: true,
              kind: "LEGAL",
              reason:
                "Synthetic legal hold: evidence and independent disposition required.",
            },
          ]
        : [],
      documents: ["REQUEST_LETTER", "AFFIDAVIT_6", "APPROVAL_LETTER"].map(
        (category) => ({ ...sampleDocument(d, category) }),
      ),
      blockers: [
        "PGRC clearance pending",
        ...(held ? ["Active legal hold"] : []),
      ],
      mode: "BROWSER_SIMULATION_NO_FINANCIAL_AUTHORITY",
    });
  }
  state.relations.push({
    id: "link0001-demo",
    institution_id: institution.id,
    old_deposit_id: "fdr00005-demo",
    new_deposit_id: "fdr00006-demo",
    kind: "RENEWAL",
    state: "REQUESTED",
    version: 1,
    maker: "demo-institution",
  });
  state.exchanges.push({
    id: "exchange-dead-letter",
    institution_id: institution.id,
    deposit_id: "fdr00009-demo",
    operation: "SIMULATED_BANK_CHECK",
    state: "DEAD_LETTER",
    attempts: 5,
    last_error: "SIMULATED repeated source outage; reviewer retry required.",
    remote_id: "SIMULATED-NO-REMOTE-SYSTEM",
    ledger_id: "SB-0009",
    result: { outcome: "SIMULATED_MATCH" },
  });
  state.notifications.push({
    id: "email-dead-letter",
    kind: "MATURITY_IN_APP",
    deposit_id: "fdr00005-demo",
    recipient: "demo-institution",
    detail: { days_remaining: 24, threshold: 30, as_of: clock },
    delivery: {
      id: uid(),
      state: "DEAD_LETTER",
      attempts: 5,
      last_error: "SIMULATED SMTP outage. Retry does not send a real email.",
      message_id: "NO_EMAIL_SENT",
    },
  });
  state.audit.push({
    id: uid(),
    institution_id: institution.id,
    actor: "demo-system",
    action: "SYNTHETIC_SCENARIOS_LOADED",
    aggregate_id: institution.id,
    detail: { simulation: true },
    request_id: "DEMO",
    created_at: "2026-10-27T08:00:00Z",
  });
  return state;
}
