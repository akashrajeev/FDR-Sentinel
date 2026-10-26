/* Standalone design artifact. No API client, authentication, persistence or production imports. */
const pages = [
  [
    "01",
    "Access",
    "Access",
    "Institution / officer",
    "Secure access",
    "Sign in through the approved identity provider.",
  ],
  [
    "02",
    "Overview",
    "Overview",
    "Review officer",
    "Deposit operations",
    "A focused view of the records and decisions requiring attention.",
  ],
  [
    "03",
    "Institution directory",
    "Institutions",
    "Review officer",
    "Institutions",
    "Institution records within your assigned scope.",
  ],
  [
    "04",
    "Institution onboarding",
    "Institutions",
    "Institution maker",
    "Declare an institution",
    "Institution declarations remain distinct from independent registry evidence.",
  ],
  [
    "05",
    "Institution & obligation",
    "Institutions",
    "Review officer",
    "Aster Institute",
    "Synthetic institution · Institutional profile and deposit obligation.",
  ],
  [
    "06",
    "Deposit register",
    "Deposits",
    "Review officer",
    "Deposit register",
    "Search instruments, review status and maturity within your assigned scope.",
  ],
  [
    "07",
    "Deposit registration",
    "Deposits",
    "Institution maker",
    "Register a deposit",
    "Record an instrument against its institutional obligation.",
  ],
  [
    "08",
    "Deposit record",
    "Deposits",
    "Review officer",
    "FDR · reference ending 0418",
    "Aster Institute (Synthetic) · Record FDR-2026-0418.",
  ],
  [
    "09",
    "Evidence workspace",
    "Review",
    "Evidence reviewer",
    "Evidence review",
    "Inspect the original document and confirm source-linked transcription.",
  ],
  [
    "10",
    "Scrutiny & correction",
    "Review",
    "Review officer",
    "Registration scrutiny",
    "Review the current evaluation and document discrepancies before deciding.",
  ],
  [
    "11",
    "Release queue",
    "Releases",
    "Release officer",
    "Release cases",
    "Track independent bureau clearances, holds and competent approval.",
  ],
  [
    "12",
    "Clearance & issuance",
    "Releases",
    "PGRC officer",
    "Case REL-2026-0081",
    "FDR · Aster Institute (Synthetic) · Term completed.",
  ],
  [
    "13",
    "Maturity & reminders",
    "Monitoring",
    "Review officer",
    "Maturity monitoring",
    "Track due dates, reminder delivery and overdue follow-up.",
  ],
  [
    "14",
    "Renewal & lineage",
    "Monitoring",
    "Institution / checker",
    "Renewals and replacements",
    "Retain the original record and evidence throughout each replacement.",
  ],
  [
    "15",
    "Management reports",
    "Reports",
    "Scoped auditor",
    "Management reports",
    "Consolidated operational information across your complete assigned scope.",
  ],
  [
    "16",
    "Interventions & policy",
    "Reports",
    "Review officer",
    "Interventions",
    "Missing evidence, delayed verification and overdue reviews in one work queue.",
  ],
  [
    "17",
    "Audit history",
    "Reports",
    "Scoped auditor",
    "Audit history",
    "Traceable submissions, evidence revisions and independent decisions.",
  ],
  [
    "18",
    "Legacy CSV import",
    "Administration",
    "Institution maker",
    "Legacy record import",
    "Validate the entire batch before creating draft deposit records.",
  ],
  [
    "19",
    "Access assignments",
    "Administration",
    "Technical operator",
    "Access assignments",
    "Manage explicit scopes without financial or document authority.",
  ],
  [
    "20",
    "Connected sandboxes",
    "Administration",
    "Assigned officer",
    "Connected sandbox systems",
    "Independent fictional sources, transport status and retained response evidence.",
  ],
].map(([id, name, group, role, title, description]) => ({
  id,
  name,
  group,
  role,
  title,
  description,
}));
const themes = {
  registry: { name: "A · Registry", asset: "a-registry.png" },
  ledger: { name: "B · Ledger", asset: "b-ledger.png" },
  workbench: { name: "C · Workbench", asset: "c-workbench.png" },
};
const groups = [
  ["Overview", "02"],
  ["Institutions", "03"],
  ["Deposits", "06"],
  ["Review", "10"],
  ["Releases", "11"],
  ["Monitoring", "13"],
  ["Reports", "15"],
  ["Administration", "19"],
];
const $ = (selector) => document.querySelector(selector);
let current = "02",
  theme = "registry",
  state = "normal",
  toastTimer;
const escapeHtml = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
const tag = (text, tone = "") => `<span class="tag ${tone}">${text}</span>`;
const button = (text, target, primary = false) =>
  `<button ${target ? `data-view="${target}"` : "data-preview"} class="${primary ? "primary" : ""}">${text}</button>`;
const link = (text, target) =>
  `<button class="link" data-view="${target}">${text}</button>`;
const section = (title, body, action = "") =>
  `<section class="section"><div class="section-head"><h2>${title}</h2>${action}</div>${body}</section>`;
const body = (html) => `<div class="section-body">${html}</div>`;
const notice = (title, copy) =>
  `<div class="notice"><strong>${title}</strong>${copy}</div>`;
const table = (headers, rows) =>
  `<div class="table-scroll"><table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
const pagination = (count = 156) =>
  `<div class="pagination"><span>Showing 1–${Math.min(6, count)} of ${count} illustrative records</span><span><button data-preview>Previous</button> <button data-preview>Next</button></span></div>`;
const kv = (pairs, single = false) =>
  `<dl class="keyvals ${single ? "single" : ""}">${pairs.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("")}</dl>`;
const field = (label, value = "", options = null, full = false) =>
  `<label class="field ${full ? "full" : ""}"><span>${label}</span>${options ? `<select>${options.map((v) => `<option ${v === value ? "selected" : ""}>${v}</option>`).join("")}</select>` : `<input value="${escapeHtml(value)}">`}</label>`;
const reason = (label = "Reason / reviewed basis") =>
  `<label class="field full"><span>${label}</span><textarea placeholder="Record the evidence reviewed and the reason for this action."></textarea><small>Recorded with the actor, timestamp and current input revision.</small></label>`;
const tabs = (labels, active = 0) =>
  `<div class="tabs">${labels.map((l, i) => `<button data-preview class="${i === active ? "active" : ""}">${l}</button>`).join("")}</div>`;
const steps = (labels, active = 0) =>
  `<div class="steps">${labels.map((l, i) => `<span class="${i === active ? "active" : i < active ? "done" : ""}">${i + 1}. ${l}</span>`).join("")}</div>`;
const metrics = (pairs) =>
  `<div class="metrics">${pairs.map(([n, l]) => `<div class="metric"><strong>${n}</strong><span>${l}</span></div>`).join("")}</div>`;
const timeline = (rows) =>
  `<ul class="timeline">${rows.map(([a, b]) => `<li><strong>${a}</strong><small>${b}</small></li>`).join("")}</ul>`;
const filters = () =>
  `<div class="filters"><label class="search">Search records<input placeholder="Institution, instrument or reference"></label><label>Instrument<select><option>All types</option><option>FDR</option><option>RTGS</option></select></label><label>Review status<select><option>All statuses</option><option>Awaiting scrutiny</option><option>Returned</option></select></label></div>`;
const rows = [
  [
    "Aster Institute (Synthetic)",
    "FDR · ••0418",
    "₹35,00,000",
    "01 Oct 2026",
    "Awaiting scrutiny",
    "warn",
  ],
  [
    "Harbor College (Synthetic)",
    "RTGS · ••7361",
    "₹50,00,000",
    "Not applicable",
    "Manually reviewed",
    "info",
  ],
  [
    "Westbridge Institute (Synthetic)",
    "FDR · ••9823",
    "₹25,00,000",
    "15 Nov 2026",
    "Returned for correction",
    "bad",
  ],
  [
    "Aster Institute (Synthetic)",
    "FDR · ••5590",
    "₹35,00,000",
    "22 Dec 2026",
    "Manually reviewed",
    "info",
  ],
  [
    "Harbor College (Synthetic)",
    "FDR · ••6712",
    "₹60,00,000",
    "30 Nov 2026",
    "Awaiting scrutiny",
    "warn",
  ],
  [
    "Westbridge Institute (Synthetic)",
    "RTGS · ••3047",
    "₹20,00,000",
    "Not applicable",
    "Draft",
    "",
  ],
];
const register = () =>
  table(
    [
      "Institution",
      "Instrument / reference",
      "Amount",
      "Maturity",
      "Review status",
      "",
    ],
    rows.map((r) => [
      r[0],
      r[1],
      r[2],
      r[3],
      tag(r[4], r[5]),
      link("Open", "08"),
    ]),
  );
const activity = () =>
  table(
    ["Date / time", "Actor", "Action", "Reference"],
    [
      [
        "27 Oct 2026 · 10:42",
        "R. Sen · Synthetic",
        "Evidence returned for correction",
        "FDR · ••9823",
      ],
      [
        "27 Oct 2026 · 10:31",
        "P. Rao · Synthetic",
        "PGRC clearance recorded",
        "REL-2026-0078",
      ],
      [
        "27 Oct 2026 · 10:20",
        "Institution maker",
        "Proof submitted for scrutiny",
        "FDR · ••0418",
      ],
    ],
  );
const docs = (missingApproval = true) =>
  `<div class="document-list">${[
    ["Deposit proof", "Original PDF · Revision 2 · Page 1", "Ready", "good"],
    ["Request letter", "Original PDF · Revision 1", "Ready", "good"],
    ["Affidavit 6", "Original PDF · Revision 1", "Ready", "good"],
    [
      "Latest approval letter",
      missingApproval
        ? "Required for release scrutiny"
        : "Original PDF · Revision 1",
      missingApproval ? "Missing" : "Ready",
      missingApproval ? "bad" : "good",
    ],
  ]
    .map(
      ([n, m, s, t]) =>
        `<div class="document-row"><span class="doc-icon">PDF</span><div>${n}<small>${m}</small></div>${tag(s, t)} ${link("Review", "09")}</div>`,
    )
    .join("")}</div>`;
const paper = () =>
  `<div class="document-viewer"><article class="paper"><div class="synthetic">SYNTHETIC DOCUMENT · NO FINANCIAL VALUE</div><h3>Synthetic Bank</h3><div class="small">FIXED DEPOSIT RECEIPT</div><hr><div class="paper-meta">Institution: Aster Institute (Synthetic)<br>Reference: SYNTHETIC-FDR-0418</div><div class="region"><div class="small">Principal amount</div><strong>INR 35,00,000.00</strong><div class="small">Selected region · Page 1</div></div><div class="paper-meta">Issue date: 01 October 2016<br>Maturity date: 01 October 2026</div><div class="stamp">Illustrative evidence for design review. Not a bank-issued document.</div></article></div>`;
const content = {
  "01": () =>
    `<div class="login-panel"><div class="brand"><span class="brand-symbol">S</span><strong>FDR Sentinel</strong></div><h1>Sign in to your workspace</h1><p>Institutional security deposits, document scrutiny and controlled release workflows.</p><label class="field"><span>Workspace</span><select><option>FDR Sentinel · Local demonstration</option></select></label>${button("Continue to secure sign-in", null, true)}<p class="small">Authentication continues at the identity provider. This preview never collects a username or password.</p><hr style="border:0;border-top:1px solid var(--line)"><p class="small" style="margin-top:16px">Synthetic environment<br>Bank and AICTE systems are represented by independent local sandboxes.</p></div><div class="access-notes"><span>Institution members</span><span>Assigned officers</span><span>Authorized auditors</span></div>`,
  "02": () =>
    `${metrics([
      ["156", "records"],
      ["23", "awaiting review"],
      ["8", "due within 30 days"],
    ])}<div class="layout"><div>${section("Deposit register", filters() + register() + pagination(), link("View all records", "06"))}${section("Recent activity", activity(), link("Full audit history", "17"))}</div><aside>${section("Needs attention", `<div class="queue-row"><strong>3</strong><span>Unresolved discrepancies<small>Evidence requires correction</small></span>${link("→", "10")}</div><div class="queue-row"><strong>2</strong><span>Pending clearances<small>Independent bureau decisions</small></span>${link("→", "12")}</div><div class="queue-row"><strong>7</strong><span>Overdue actions<small>Product service levels</small></span>${link("→", "16")}</div>`)}${section(
      "Upcoming deadlines",
      body(
        kv(
          [
            ["Within 7 days", "4 instruments"],
            ["Within 8–30 days", "4 instruments"],
          ],
          true,
        ),
      ),
      link("Open monitor", "13"),
    )}</aside></div>`,
  "03": () =>
    `${tabs(["Directory", "Registry evidence"])}${section(
      "Assigned institutions",
      `<div class="filters"><label class="search">Search institutions<input placeholder="Institution name or external identifier"></label><label>Registry status<select><option>All statuses</option><option>Declaration only</option><option>Sandbox match</option></select></label></div>` +
        table(
          [
            "Institution",
            "External identifier",
            "Classification",
            "Registry evidence",
            "",
          ],
          [
            [
              "Aster Institute (Synthetic)",
              "SYNTHETIC-001",
              "Private · Engineering UG",
              tag("Sandbox match", "info"),
              link("Open profile", "05"),
            ],
            [
              "Harbor College (Synthetic)",
              "SYNTHETIC-002",
              "Private · Management PG",
              tag("Declaration only", "warn"),
              link("Open profile", "05"),
            ],
            [
              "Westbridge Institute (Synthetic)",
              "SYNTHETIC-003",
              "Government aided",
              tag("Requires review", "warn"),
              link("Open profile", "05"),
            ],
          ],
        ) +
        pagination(3),
      button("Onboard institution", "04", true),
    )}${notice("Source distinction", "A sandbox result refers to a fictional registry. It is separate from the institution declaration and official AICTE confirmation.")}`,
  "04": () =>
    `${steps(["Institution identity", "Policy context & obligation", "Review declaration"], 1)}<div class="layout"><div class="form">${section("Institution declaration", body(`<div class="form-grid">${field("Legal institution name", "Aster Institute (Synthetic)")}${field("External institution identifier", "SYNTHETIC-001")}${field("Academic year", "2026-27", ["2026-27", "2025-26", "Other / historical"])}${field("Governance", "Private", ["Private", "Government", "Government aided", "Unknown"])}${field("Programme", "Engineering", ["Engineering", "Management", "Other / unknown"])}${field("Level", "UG", ["UG", "PG", "Diploma", "Unknown"])}${field("Land category", "Owned", ["Owned", "Private lease", "Other / unknown"])}${field("Regulatory event", "New institution", ["New institution", "Historical / other"])}${field("Obligation coverage", "Single record", ["Single record", "Aggregate — human review required"])}${field("Exceptional context", "No", ["No", "Yes / unknown"])}</div>`) + `<div class="form-footer"><span>Declaration is not registry confirmation.</span>${button("Review declaration", null, true)}</div>`)}</div><aside>${section("Declaration guidance", body(`<p class="small">Use the applicable institutional context. Unknown or historical conditions go to human review.</p><p class="small muted">No officer privileges are granted through institution onboarding.</p>`))}</aside></div>`,
  "05": () =>
    `${tabs(["Profile & obligation", "Deposit records", "Registry evidence"])}<div class="layout"><div>${section(
      "Institution profile",
      body(
        kv([
          ["Institution identifier", "SYNTHETIC-001"],
          ["Legal entity", "Aster Institute (Synthetic)"],
          ["Programme / level", "Engineering · UG"],
          ["Governance / land", "Private · Owned"],
          ["Academic year", "2026-27"],
          ["Declared owner", "Institution member · Synthetic"],
        ]),
      ),
    )}${section(
      "Deposit obligation",
      body(
        kv([
          ["Event", "New institution"],
          ["Coverage", "Single record"],
          ["Contextual base", "₹35,00,000 · Provisional"],
          ["Policy reference", "APH 2024–27 · 1.12 / Table 1.4"],
          ["Existing records", "3 retained instruments"],
          ["Applicability", "Human review required"],
        ]),
      ) +
        `<div class="form-footer"><span>Policy source and evaluation retained.</span>${button("View deposit records", "06")}</div>`,
    )}</div><aside>${section(
      "Independent registry evidence",
      body(
        `${tag("Sandbox match", "info")}<p class="small" style="margin-top:14px">Independent fictional registry response, received 27 Oct 2026, 10:18.</p>${kv(
          [
            ["Declared information", "Retained separately"],
            ["Official confirmation", "Not connected"],
          ],
          true,
        )}${button("Inspect source response", "20")}`,
      ),
    )}</aside></div>`,
  "06": () =>
    `${tabs(["All instruments", "Awaiting scrutiny", "Returned", "Manually reviewed"])}${section("Instrument-wise records", filters() + register() + pagination(), `<div class="actions">${button("Export")}${button("Register deposit", "07", true)}</div>`)}${notice("Independent status dimensions", "Administrative review, document readiness, source verification and maturity remain separate. Manual review does not mean bank confirmation.")}`,
  "07": () =>
    `${steps(["Instrument details", "Supporting proof", "Review & submit"], 0)}<div class="layout"><div class="form">${section("Instrument details", body(`<div class="form-grid">${field("Institution / obligation", "Aster Institute · New institution", ["Aster Institute · New institution"])}${field("Deposit type", "FDR", ["FDR", "RPGF", "RTGS", "ONLINE", "OTHER_LEGACY"])}${field("Issuing bank code", "SYN-BANK")}${field("Instrument reference", "SYNTHETIC-FDR-0418")}${field("Declared principal (INR)", "35,00,000.00")}${field("Issue date", "01 Oct 2016")}${field("Maturity date", "01 Oct 2026")}${field("Obligation coverage", "Single record", ["Single record"])}<div class="field full"><small>FDR dates are required for FDR only. RTGS and online records use the deposit date and do not receive an invented maturity date.</small></div></div>`) + `<div class="form-footer"><span>Reference shown masked after save.</span><div class="actions">${button("Cancel", "06")}${button("Save draft & add proof", "08", true)}</div></div>`)}</div><aside>${section("Before submission", body(`<ul class="checklist"><li><span>Record declaration</span>${tag("Current", "info")}</li><li><span>Upload prescribed proof</span>${tag("Next")}</li><li><span>Scan and extract</span>${tag("Required")}</li><li><span>Evaluate and submit</span>${tag("Required")}</li></ul>`))}</aside></div>`,
  "08": () =>
    `${tabs(["Record & evidence", "Scrutiny", "Source checks", "History"])}${metrics(
      [
        ["₹35,00,000", "declared principal"],
        ["Awaiting scrutiny", "administrative state"],
        ["Matured", "temporal state"],
      ],
    )}<div class="layout"><div>${section(
      "Instrument declaration",
      body(
        kv([
          ["Type / bank", "FDR · SYN-BANK"],
          ["Reference", "Ending 0418"],
          ["Issue date", "01 Oct 2016"],
          ["Maturity date", "01 Oct 2026"],
          ["Obligation", "New institution · Single record"],
          ["Source status", "Institution declared"],
        ]),
      ),
    )}${section("Document evidence", docs(), button("Upload revision"))}</div><aside>${section(
      "Review status",
      body(
        `${tag("Awaiting scrutiny", "warn")}<p class="small" style="margin-top:14px">Current evaluation has one evidence mismatch requiring correction.</p>${button("Open scrutiny", "10", true)}<hr style="border:0;border-top:1px solid var(--line);margin:20px 0">${kv(
          [
            ["Input revision", "4"],
            ["Evaluation freshness", "Current"],
            ["Originals", "Retained"],
          ],
          true,
        )}`,
      ),
    )}${section("Source check", body(`${tag("Sandbox response available", "info")}<p class="small" style="margin-top:10px">Fictional independent bank record. No genuine bank confirmation.</p>${link("Inspect bank comparison", "20")}`))}</aside></div>`,
  "09": () =>
    `${tabs(["Original & transcription", "Discrepancies", "Revision history"])}<div class="layout viewer-layout"><div>${section("Deposit proof · Revision 2", paper(), `<span class="small muted">Page 1 of 1 · 100%</span>`)}</div><div>${section("Amount transcription", body(`<p class="eyebrow">Source-linked finding</p><div class="compare"><div><small>Institution declaration</small><strong>₹35,00,000</strong></div><div class="diff"><small>Earlier extraction</small><strong>₹30,00,000</strong></div></div><p class="small">Selected evidence region: page 1, original proof. The proposed value remains separate from the declaration.</p><div class="form-grid">${field("Proposed transcription (INR)", "35,00,000.00")}${field("Field", "Principal amount", ["Principal amount", "Issue date", "Maturity date"])}${reason("Evidence correction reason")}</div><div class="actions" style="margin-top:18px">${button("Reject transcription")}${button("Confirm as independent checker", null, true)}</div><p class="small muted" style="margin-top:14px">A maker cannot confirm their own proposal. Confirmation requires a fresh evaluation.</p>`))}${section(
      "Evidence provenance",
      body(
        kv(
          [
            ["Processing", "Scanned PDF · OCR"],
            ["Original hash", "SHA-256 · a31c…90df"],
            ["Location", "Page 1 · selected amount region"],
            ["Authority", "Transcription only; not authenticity"],
          ],
          true,
        ),
      ),
    )}</div></div>`,
  10: () =>
    `${steps(["Declaration", "Evidence review", "Officer decision"], 1)}${notice("Acceptance blocked: evidence discrepancy", "The current proof and declared value disagree. A deficient submission remains available for scrutiny, but cannot be accepted until corrected.")}<div class="layout"><div>${section(
      "Current findings",
      table(
        ["Finding", "Basis", "State", ""],
        [
          [
            "Amount differs",
            "Declaration ₹35,00,000 / extraction ₹30,00,000",
            tag("Open blocker", "bad"),
            link("Inspect evidence", "09"),
          ],
          [
            "Policy context",
            "APH 2024–27 · 1.12 / Table 1.4",
            tag("Provisional", "warn"),
            link("View obligation", "05"),
          ],
          [
            "Original document",
            "Scanned and hash retained",
            tag("Ready", "good"),
            link("Open original", "09"),
          ],
        ],
      ),
    )}${section("Officer observation", body(`<div class="form-grid">${field("Decision", "Return for correction", ["Return for correction", "Accept registration — blocked"])}${field("Evidence reviewed", "Yes", ["Yes", "No"])}${reason("Scrutiny observation")}</div><div class="actions" style="margin-top:18px">${button("Return with reason", null, true)}<button disabled>Accept registration</button></div><p class="small muted" style="margin-top:14px">The reviewer must be independent of the originating maker. Registration acceptance is not bank confirmation or release.</p>`))}</div><aside>${section(
      "Decision history",
      body(
        timeline([
          ["Current submission", "27 Oct 2026 · Institution maker"],
          ["Proof revision 2 received", "27 Oct 2026 · Original retained"],
          ["Earlier correction request", "25 Oct 2026 · R. Sen · Synthetic"],
        ]),
      ),
    )}${section("After correction", body(`<p class="small">Reevaluate the current evidence set, resolve earlier findings with evidence, then record an independent decision.</p>`))}</aside></div>`,
  11: () =>
    `${tabs(["All release cases", "Clearances pending", "Approval review", "Issued synthetic"])}${section(
      "Release work queue",
      filters() +
        table(
          [
            "Case / institution",
            "Instrument",
            "Reason",
            "Clearances",
            "Administrative state",
            "",
          ],
          [
            [
              "REL-2026-0081<small>Aster Institute (Synthetic)</small>",
              "FDR · ••0418",
              "Term completed",
              "2 of 3 cleared",
              tag("PGRC pending", "warn"),
              link("Open case", "12"),
            ],
            [
              "REL-2026-0078<small>Harbor College (Synthetic)</small>",
              "RTGS · ••7361",
              "Term completed",
              "3 of 3 cleared",
              tag("Approval review", "info"),
              link("Open case", "12"),
            ],
            [
              "REL-2026-0072<small>Westbridge Institute (Synthetic)</small>",
              "FDR · ••9823",
              "Closure",
              "Legal hold",
              tag("Blocked", "bad"),
              link("Open case", "12"),
            ],
          ],
        ) +
        pagination(3),
      button("Create release request", "12", true),
    )}${notice("Dates do not authorize release", "Maturity, bank verification, bureau clearance, competent approval and issuer authorization are separate controls. No worker or AI can make the officer decision.")}`,
  12: () =>
    `${steps(["Request & evidence", "Bureau clearances", "Competent approval", "Synthetic issuance"], 1)}${notice("Approval held: PGRC clearance pending", "Vigilance and Grants have cleared this input revision. PGRC must independently record its own decision before approval.")}<div class="layout"><div>${section(
      "Independent bureau decisions",
      table(
        ["Bureau", "Decision", "Actor / evidence", ""],
        [
          [
            "PGRC",
            tag("Pending", "warn"),
            "Assigned PGRC officer",
            button("Record PGRC decision"),
          ],
          [
            "Vigilance",
            tag("Cleared", "good"),
            "V. Rao · Synthetic<small>Signed evidence retained</small>",
            button("Inspect"),
          ],
          [
            "Grants",
            tag("Cleared", "good"),
            "R. Sen · Synthetic<small>Signed evidence retained</small>",
            button("Inspect"),
          ],
        ],
      ),
    )}${section("Required evidence", docs(false))}${section("Conditional holds", body(`<p class="small">Financial, legal, merger, closure and conversion conditions require their own evidence and independent disposition.</p>${button("Inspect holds")}`))}</div><aside>${section(
      "Authorization",
      body(
        kv(
          [
            ["Current state", "Clearances pending"],
            ["Competent approval", "Blocked"],
            ["Issuer", "Not yet authorized"],
            ["Financial settlement", "Not performed"],
          ],
          true,
        ) +
          `<button disabled style="width:100%;margin-top:18px">Approve case</button>`,
      ),
    )}${section("Later workflow states", body(`<details><summary>Inspect approved / issued sample design</summary><p class="small" style="margin-top:14px">After all controls pass, an independent approver records the basis. A different authorized issuer generates the visibly synthetic NOC or RTGS sanction.</p>${button("Preview synthetic output")}${button("Inspect sandbox reconciliation", "20")}<p class="small muted" style="margin-top:12px">No official NOC, bank settlement or real funds movement.</p></details>`))}</aside></div>`,
  13: () =>
    `${metrics([
      ["8", "due within 30 days"],
      ["4", "due within 7 days"],
      ["3", "matured · follow-up required"],
    ])}${section(
      "Maturity register",
      table(
        [
          "Institution / instrument",
          "Maturity",
          "Days remaining",
          "Reminder band",
          "Email delivery",
          "",
        ],
        [
          [
            "Aster Institute · FDR ••0418",
            "01 Oct 2026",
            "26 days overdue",
            tag("Matured", "warn"),
            tag("SMTP accepted", "good"),
            link("Inspect", "16"),
          ],
          [
            "Westbridge · FDR ••9823",
            "15 Nov 2026",
            "19 days",
            "30-day reminder",
            tag("SMTP accepted", "good"),
            link("Open", "08"),
          ],
          [
            "Harbor College · FDR ••6712",
            "30 Nov 2026",
            "34 days",
            "90-day reminder",
            tag("Retry pending", "warn"),
            button("Delivery details"),
          ],
        ],
      ) + pagination(3),
      button("Reminder policy", "16"),
    )}<div class="layout equal">${section(
      "Reminder delivery history",
      body(
        timeline([
          [
            "30-day reminder accepted by SMTP",
            "26 Oct 2026 · Stable message identity",
          ],
          ["7-day reminder queued", "27 Oct 2026 · Retry tracked"],
          ["Overdue escalation", "Independent supervisor · Follow-up only"],
        ]),
      ),
    )}${section("Synthetic clock exercise", body(`<p class="small muted">Demonstration clock only. Advancing this clock cannot approve a release.</p><div class="form-grid">${field("As-of date", "27 Oct 2026")}${field("Assigned scope", "Aster Institute (Synthetic)")}</div><div class="actions" style="margin-top:16px">${button("Run maturity scan")}</div>`))}</div>`,
  14: () =>
    `${tabs(["Pending authorization", "Authorized lineage", "Original records"])}<div class="layout"><div>${section("Replacement proposal", body(`<div class="form-grid">${field("Original instrument", "FDR · ••0418", ["FDR · ••0418"])}${field("Replacement instrument", "FDR · ••7262", ["FDR · ••7262"])}${field("Relationship", "Renewal", ["Renewal", "Replacement", "Auto-renewal recorded"])}${field("Supporting evidence", "Renewal proof · Ready")}${reason("Renewal rationale")}</div><div class="compare" style="margin-top:20px"><div><small>Original principal / maturity</small><strong>₹35,00,000</strong><div class="small muted">01 Oct 2026</div></div><div><small>Replacement principal / maturity</small><strong>₹35,00,000</strong><div class="small muted">01 Oct 2036</div></div></div>${button("Request independent authorization", null, true)}`))}${section(
      "Existing lineage",
      body(
        timeline([
          [
            "Original FDR retained",
            "••1048 · Evidence and review history preserved",
          ],
          [
            "Replacement independently authorized",
            "••0418 · Different checker and policy basis",
          ],
          ["Current renewal proposal", "••7262 · Awaiting independent checker"],
        ]),
      ),
    )} </div><aside>${section("Authorization safeguards", body(`<ul class="checklist"><li><span>New instrument accepted</span>${tag("Required")}</li><li><span>Later instrument date</span>${tag("Required")}</li><li><span>Principal preserved</span>${tag("Required")}</li><li><span>Independent checker</span>${tag("Required")}</li></ul><p class="small muted" style="margin-top:15px">Renewal is subject to applicable policy. It does not mean financial release.</p>`))}</aside></div>`,
  15: () =>
    `${tabs(["Operations summary", "Instrument export", "Interventions"])}${metrics(
      [
        ["156", "total instruments"],
        ["23", "awaiting scrutiny"],
        ["8", "due within 30 days"],
        ["0", "actual financial releases"],
      ],
    )}<div class="layout equal">${section("Administrative workload", body(`<div class="bars"><div style="height:40%"><span>23</span><small>Scrutiny</small></div><div style="height:24%"><span>14</span><small>Draft</small></div><div style="height:75%"><span>119</span><small>Reviewed</small></div></div><p class="small muted" style="margin-top:35px">Illustrative scoped counts. Manual review remains distinct from authenticity.</p>`))}${section(
      "Cases requiring intervention",
      table(
        ["Category", "Open", ""],
        [
          ["Missing documents", "4", link("Inspect", "16")],
          ["Pending verification", "3", link("Inspect", "16")],
          ["Overdue reviews", "7", link("Inspect", "16")],
          ["Pending bureau clearances", "2", link("Inspect", "16")],
        ],
      ),
    )}</div>${section("Scoped instrument export", filters() + register(), `<div class="actions">${button("Export CSV")}${button("Open intervention report", "16", true)}</div>`)}${notice("Measurement boundary", "Workflow duration is derived from synthetic audit timestamps. No human turnaround or administrative savings are inferred from this sample.")}`,
  16: () =>
    `${tabs(["Open interventions", "Resolved history", "Operational policy"])}${section(
      "Intervention queue",
      `<div class="filters"><label class="search">Search / deposit reference<input placeholder="Institution or instrument"></label><label>Category<select><option>All categories</option><option>Missing documents</option><option>Pending verification</option></select></label><label>Follow-up<select><option>Overdue only</option><option>All open</option></select></label></div>` +
        table(
          ["Category / source", "Due", "Follow-up", "Delivery", ""],
          [
            [
              "Missing deposit proof<small>Aster Institute · FDR ••0418</small>",
              "27 Oct · 09:00",
              tag("Escalated", "warn"),
              tag("SMTP accepted", "good"),
              button("Inspect / acknowledge"),
            ],
            [
              "Independent source conflict<small>Harbor College · Check SB-1048</small>",
              "27 Oct · 10:00",
              tag("Open", "bad"),
              tag("Retry pending", "warn"),
              link("Inspect source", "20"),
            ],
            [
              "PGRC clearance pending<small>REL-2026-0081</small>",
              "27 Oct · 12:00",
              tag("Acknowledged", "info"),
              tag("SMTP accepted", "good"),
              link("Open case", "12"),
            ],
          ],
        ) +
        pagination(3),
      button("Export filtered CSV"),
    )}<div class="layout equal">${section("Follow-up acknowledgement", body(`<p class="small">Acknowledgement records responsibility. Only correction or completion of the source workflow resolves the intervention.</p><div class="form-grid">${reason("Follow-up note")}</div><div class="actions" style="margin-top:16px">${button("Acknowledge follow-up")}${button("Inspect resolved history")}</div>`))}${section("Operational policy · Revision 3", body(`<div class="form-grid">${field("Review SLA (hours)", "24")}${field("Verification SLA (hours)", "2")}${field("Escalation delay (hours)", "24")}${field("Maturity reminder days", "90, 30, 7")}${field("Independent supervisor", "Assigned approver · Synthetic", ["Assigned approver · Synthetic", "Assigned auditor · Synthetic"])}${field("Change reason", "Product service levels reviewed")}</div><div class="actions" style="margin-top:16px">${button("Save new policy revision")}</div><p class="small muted" style="margin-top:12px">Product deadlines, not statutory deadlines. Supervisor selection grants no permissions. Revoked access cancels queued operational mail.</p>`))}</div>`,
  17: () =>
    `${section(
      "Traceable actions",
      `<div class="filters"><label class="search">Search reference / actor<input placeholder="Case, instrument or actor"></label><label>Action<select><option>All actions</option><option>Officer decision</option><option>Evidence change</option></select></label><label>Date<input value="27 Oct 2026"></label></div>` +
        activity() +
        table(
          ["Date / time", "Actor", "Action", "Reference"],
          [
            [
              "27 Oct 2026 · 10:12",
              "Technical operator",
              "Scoped assignment changed",
              "Aster Institute",
            ],
            [
              "27 Oct 2026 · 10:08",
              "Review officer",
              "Operational policy revision 3",
              "Policy / institution",
            ],
            [
              "27 Oct 2026 · 10:01",
              "Document worker",
              "Proof processed · Ready",
              "FDR · ••0418",
            ],
          ],
        ) +
        pagination(6),
    )}<div class="layout equal">${section(
      "Selected event",
      body(
        kv([
          ["Actor", "R. Sen · Synthetic"],
          ["Action", "Evidence returned for correction"],
          ["Time", "27 Oct 2026 · 10:42"],
          ["Affected record", "FDR · ••9823"],
          ["Reason", "Principal mismatch in current proof"],
          ["Input revision", "4"],
        ]),
      ),
    )}${section(
      "Record integrity",
      body(
        `<p class="small">Original documents, earlier decisions, policy revisions and audit events remain retained.</p>${kv(
          [
            ["Request reference", "REQ-8B7D…"],
            ["Evidence digest", "SHA-256 · a31c…90df"],
            ["Audit history", "Append-only application access"],
          ],
          true,
        )}<p class="small muted" style="margin-top:16px">Database-owner protection requires separate production anchoring and recovery controls.</p>`,
      ),
    )}</div>`,
  18: () =>
    `${steps(["Select CSV", "Validate batch", "Create drafts"], 1)}<div class="layout"><div>${section(
      "Batch preview",
      body(
        `<div class="file-row"><span>synthetic-deposits-october.csv</span><span class="muted">3 rows · 2.4 KB</span></div><p class="small">Validation is atomic. No records are created during preview.</p>`,
      ) +
        table(
          ["Row", "Type / reference", "Principal", "Validation"],
          [
            ["2", "FDR · SYN-0418", "₹35,00,000", tag("Valid", "good")],
            ["3", "RTGS · SYN-7361", "₹50,00,000", tag("Valid", "good")],
            [
              "4",
              "FDR · SYN-9823",
              "₹0",
              tag("Amount must be positive", "bad"),
            ],
          ],
        ) +
        `<div class="form-footer"><span>2 valid · 1 requires correction</span><button disabled>Create 3 draft records</button></div>`,
    )}${notice("Correct the file and preview again", "The whole batch is rejected if any row fails validation. Commit must use the unchanged, validated file hash.")}</div><aside>${section("Required columns", body(`<p class="small">Obligation, deposit type, bank code, reference, amount in paise and dates appropriate to instrument type.</p>${button("Download template")}<p class="small muted" style="margin-top:15px">Imports create DRAFT records. Evidence, evaluation and officer review remain required.</p><details><summary>All-valid preview state</summary><p class="small" style="margin-top:12px">After correction: 3 valid rows · unchanged preview hash.</p>${button("Preview draft commit")}</details>`))}</aside></div>`,
  19: () =>
    `<div class="layout"><div>${section("New / revised assignment", body(`<div class="form-grid">${field("Principal", "Assigned review officer · Synthetic", ["Assigned review officer · Synthetic", "Assigned auditor · Synthetic"])}${field("Role", "Reviewer", ["Reviewer", "Auditor", "Clearance officer", "Approver", "Issuer"])}${field("Scope type", "Institution", ["Institution", "Case", "Bureau"])}${field("Assigned scope", "Aster Institute (Synthetic)", ["Aster Institute (Synthetic)"])}${field("Valid until", "26 Nov 2026")}${field("Assignment state", "Enabled", ["Enabled", "Disabled"])}${reason("Assignment reason")}</div><div class="actions" style="margin-top:18px">${button("Save scoped assignment", null, true)}</div><p class="small muted" style="margin-top:14px">Self-grants and operator-role grants are prohibited. Bureau authority also requires institution or case access.</p>`))}${section(
      "Current scope assignments",
      table(
        ["Principal", "Role", "Scope", "Expiry", "State"],
        [
          [
            "R. Sen · Synthetic",
            "Reviewer",
            "Aster Institute",
            "26 Nov 2026",
            tag("Enabled", "good"),
          ],
          [
            "P. Rao · Synthetic",
            "Clearance",
            "PGRC + case assignment",
            "26 Nov 2026",
            tag("Enabled", "good"),
          ],
          [
            "A. Shah · Synthetic",
            "Auditor",
            "Aster Institute",
            "26 Nov 2026",
            tag("Enabled", "good"),
          ],
        ],
      ),
    )}</div><aside>${section("Technical administration", body(`<p class="small">Operator access manages assignments only. It does not expose deposit evidence or grant financial decision authority.</p><p class="small muted">Every change records the operator, scope, reason and validity.</p>`))}</aside></div>`,
  20: () =>
    `${notice("Independent fictional sources", "These are real local API exchanges over synthetic registry and bank records. They are not official AICTE receipts, bank PKI or confirmation of real instruments.")}<div class="layout"><div>${section(
      "Declared vs independent source",
      table(
        ["Field", "Institution declaration", "Bank sandbox record"],
        [
          ["Principal", "₹35,00,000", "₹30,00,000"],
          ["Bank", "SYN-BANK", "SYN-BANK"],
          ["Reference suffix", "••0418", "••0418"],
          ["Maturity", "01 Oct 2026", "01 Oct 2026"],
        ],
      ) +
        body(
          `${tag("Mismatch · review required", "bad")}<p class="small" style="margin-top:12px">The source record is independently stored. It is never rewritten to echo the declaration.</p>`,
        ),
    )}${section(
      "Exchange history",
      table(
        ["Operation", "Transport", "Outcome", "Attempts", ""],
        [
          [
            "Bank verification",
            tag("Completed", "good"),
            tag("Mismatch", "bad"),
            "2",
            button("Inspect evidence"),
          ],
          [
            "Institution registry",
            tag("Completed", "good"),
            tag("Sandbox match", "info"),
            "1",
            button("Inspect evidence"),
          ],
          [
            "Issued-case receipt",
            tag("Waiting", "warn"),
            "Pending",
            "1",
            button("Request details"),
          ],
        ],
      ),
    )}</div><aside>${section(
      "Request details",
      body(
        kv(
          [
            ["Source", "Independent synthetic sandbox"],
            ["Correlation", "SB-REQ-1048"],
            ["Response signature", "Local HMAC checked"],
            ["Input revision", "4 · current"],
            ["Authority", "Advisory source evidence only"],
          ],
          true,
        ),
      ),
    )}${section("After human issuance", body(`<p class="small">Only the recorded issuer may send an issued case for sandbox receipt/reconciliation.</p><button disabled>Reconcile issued case</button><p class="small muted" style="margin-top:12px">No actual release or settlement state is set.</p>`))}</aside></div>`,
};
function icon(index) {
  const paths = [
    "M3 11 12 3l9 8M5 10v11h14V10M10 21v-7h4v7",
    "M3 8l9-5 9 5M4 9h16M5 10v9m5-9v9m4-9v9m5-9v9M3 21h18",
    "M6 3h9l4 4v14H6zM14 3v6h5M9 13h7m-7 4h7",
    "M5 4h14v17H5zM8 8h8m-8 4h4m-4 4h6",
    "M4 6h16v15H4zM8 3v6m8-6v6M7 13h10m-10 4h6",
    "M4 21V11h4v10m4 0V4h4v17m4 0v-7h3v7",
    "M4 4h16v17H4zM8 8h8m-8 4h8m-8 4h5",
    "M4 6h16M4 12h16M4 18h16M8 3v6m8 0v6M9 15v6",
  ];
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[index]}"></path></svg>`;
}
function actions(page) {
  const map = {
    "02": button("Register deposit", "07", true),
    "03": button("Onboard institution", "04", true),
    "05": button("View registry evidence", "20"),
    "06": button("Register deposit", "07", true),
    "08": button("Open scrutiny", "10", true),
    "09": button("Download original"),
    10: button("Back to register", "06"),
    11: button("New release request", "12", true),
    12: button("Case history", "17"),
    13: button("Reminder policy", "16"),
    14: button("Original record", "08"),
    15: button("Export CSV"),
    16: button("Run scoped scan"),
    17: button("Inspect retained evidence", "09"),
    18: button("Choose another file"),
    19: button("Assignment history", "17"),
    20: button("Source catalogue"),
  };
  return map[page.id] || "";
}
function render() {
  const page = pages.find((p) => p.id === current) || pages[1];
  current = page.id;
  document.body.dataset.theme = theme;
  $("#screen").value = current;
  $("#state").value = state;
  document
    .querySelectorAll("[data-theme-choice]")
    .forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.themeChoice === theme)),
    );
  $("#screen-count").textContent = `${Number(current)} / ${pages.length}`;
  $("#role").textContent = page.role;
  $("#breadcrumb").textContent = `Workspace / ${page.group} / ${page.name}`;
  $("#nav").innerHTML = groups
    .map(
      ([g, id], i) =>
        `<button data-view="${id}" title="${g}" aria-label="${g}" class="${page.group === g ? "active" : ""}">${icon(i)}<span class="nav-text">${g}</span></button>`,
    )
    .join("");
  let markup = content[current]();
  if (state === "empty")
    markup = `<div class="empty"><p class="eyebrow">${page.name}</p><h2>No records in this view</h2><p class="muted small">Adjust the scope or filters. Nothing has been created in this design preview.</p>${button("Clear filters")}</div>`;
  if (state === "loading")
    markup = `<div class="skeleton" aria-busy="true"><p class="small muted">Loading scoped records…</p><div></div><div></div><div></div><div></div><div></div></div>`;
  if (state === "error")
    markup =
      notice(
        current === "09"
          ? "Document unavailable — quarantined"
          : "Service temporarily unavailable",
        current === "09"
          ? "The original remains protected until scanning and processing succeed. Submission and approval stay blocked."
          : "Retained data and existing decisions remain unchanged. Retry the service; no successful verification or approval is inferred.",
      ) +
      `<div class="empty"><h2>${current === "09" ? "Processing required" : "Unable to load this view"}</h2><p class="small muted">Request reference REQ-8B7D · Retriable service condition</p>${button("Retry preview")} <button disabled>Continue / approve</button></div>`;
  $("#content").innerHTML =
    (current === "01"
      ? ""
      : `<div class="page-heading"><div><p class="eyebrow">${page.group} · ${page.role}</p><h1>${page.title}</h1><p class="subtitle">${page.description}</p></div><div class="actions">${actions(page)}</div></div>`) +
    markup;
  history.replaceState(null, "", `#${theme}/${current}/${state}`);
}
function navigate(id) {
  if (pages.some((p) => p.id === id)) {
    current = id;
    state = "normal";
    render();
    window.scrollTo({ top: 0, behavior: "instant" });
  }
}
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("#toast").style.display = "none"), 4200);
}
$("#screen").innerHTML = pages
  .map((p) => `<option value="${p.id}">${p.id} · ${p.name}</option>`)
  .join("");
$("#screen").addEventListener("change", (e) => navigate(e.target.value));
$("#state").addEventListener("change", (e) => {
  state = e.target.value;
  render();
});
$("#previous").addEventListener("click", () =>
  navigate(pages[(Number(current) + pages.length - 2) % pages.length].id),
);
$("#next").addEventListener("click", () =>
  navigate(pages[Number(current) % pages.length].id),
);
document.addEventListener("click", (e) => {
  const choice = e.target.closest("[data-theme-choice]");
  if (choice) {
    theme = choice.dataset.themeChoice;
    render();
    return;
  }
  const target = e.target.closest("[data-view]");
  if (target) {
    navigate(target.dataset.view);
    return;
  }
  if (e.target.closest("[data-preview]"))
    toast(
      "Design preview only. No records, permissions, emails or decisions were changed.",
    );
});
$("#board").addEventListener("click", () => {
  $("#board-image").src = themes[theme].asset;
  $("#board-title").textContent =
    themes[theme].name + " · generated visual direction";
  $("#image-dialog").showModal();
});
$("#close-board").addEventListener("click", () => $("#image-dialog").close());
const fragment = location.hash.slice(1).split("/");
if (themes[fragment[0]]) theme = fragment[0];
if (pages.some((p) => p.id === fragment[1])) current = fragment[1];
if (["normal", "empty", "loading", "error"].includes(fragment[2]))
  state = fragment[2];
render();
