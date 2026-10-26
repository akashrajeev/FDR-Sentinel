# Registry UI implementation

User-approved reference: direction A in `docs/ui-concepts`, with an improved public
entry screen. The concept gallery remains a review artifact; its sample numbers and
records are not embedded in the application. Existing functional tabs and action
permissions are retained; this change does not claim twenty new application routes.

## Applied design

- White navigation rail, navy text, cobalt controls, small corner radii and thin table
  rules. Shared tokens cover institution forms, evidence, clearance steps, reports,
  operational policy, import and technical-operator workspaces.
- Consistent native SVG navigation icons, keyboard-focus indicators, labelled row-open
  actions, keyboard access to release cases and horizontal mobile navigation.
- Overview has actual scoped instrument/review counts, an explicit 90-day reporting
  window, intervention/clearance/overdue counts and recent audit activity. Unavailable
  counts are not converted into successful zeroes. Only six recent register records
  are shown here, with a link to the full scoped register.
- Deposit register uses the existing server search/filter endpoint with 50-row keyset
  pagination. Record creation opens its persisted detail/evidence workflow directly.
  Scoped search, rather than the latest-record preview, finds a specific historical case.
- Record-section anchors expose evidence, policy/scrutiny, source checks, document
  review and prior decisions. The PDF selection colors follow Registry; original page
  geometry, coordinate conversion and independent correction behavior are unchanged.
- Protected workspace loading, failure/retry, empty tables, input focus, blocked actions,
  lineage, required-evidence and source limitations remain visible.
- Report, register and reminder responses are protected against stale asynchronous
  results. Reselecting an already-selected institution keeps its loaded operational
  policy. Reminder filtering applies immediately, including during a service refresh.

## Public entry

The public screen explains deposit management, lifecycle steps and access responsibilities.
It has one clear sign-in action and continues to the existing identity provider. It
collects no credentials, fetches no institutional/financial records before authentication
and displays no fabricated portfolio counts or claims of official bank confirmation.
Synthetic sandbox, provisional policy and no-financial-release boundaries are disclosed.
No external font, image or analytics request is introduced.

## Verification

Run results and known limits belong in STATUS.md. Browser coverage includes the public
home at desktop/mobile sizes, actual OIDC, server-backed register filtering and the
complete existing end-to-end workflows. The test helper finds specific records through
scoped search instead of assuming they are in a six-row overview. SMTP assertions locate
their unique subject using Mailpit search so retained or future-dated messages do not
hide a new test message. No clock/role/approval check is disabled for presentation.

Executed final acceptance: 10 browser journeys passed in 189.42s; 88 backend tests passed
in 112.44s; TypeScript/Vite, Ruff and npm audit passed. The phase's isolated fresh backend
deployment also passed, with final UI refinements verified on the live local stack.
The before-login screen and loaded Registry overview were visually inspected at desktop
and mobile widths. Synthetic screenshot evidence remains in ignored `.local/registry-qa`
and `.local/browser` rather than being bundled into the application.

Production authorization, applicable-rule sign-off and security qualification remain
separate from visual design approval.
