# FDR Sentinel — UI options for review

These are **design mockups**, not a redesign deployed to the live app. No application
source, authentication, API, permissions or financial workflow was changed. All numbers,
records, people and proposed action states here are illustrative synthetic examples.

Open `http://localhost:8096` while the local preview server is running, or open
`index.html` directly. Switch A/B/C and choose any of the 20 views. Every view has normal,
empty, loading and unavailable states. Buttons navigate mockup screens or display a
preview notice; they never call the application API. No login credentials are collected.

| Direction | Design intent | Main choices |
|---|---|---|
| A · Registry | Restrained institutional clarity | White rail/canvas, navy typography, cobalt action, clear tables and split review workspace |
| B · Ledger | Financial dossier with stronger character | Warm neutral surfaces, charcoal text, oxblood actions, serif headings, horizontal navigation and editorial rules |
| C · Workbench | Compact officer console | Matte graphite, accessible steel-blue controls, narrow rail, dense rows and persistent source context |

The three PNGs were generated with the built-in image-generation tool. Full prompts are
in PROMPTS.md. The curated HTML/CSS/JS gallery extends each visual direction across the
whole application. It is a layout specification rather than a claim that the raster
concept and code preview match pixel-for-pixel. Generated image microcopy can vary;
the gallery corrects instrument semantics, such as no invented RTGS maturity date.

## Complete page / workflow coverage

The current application combines several workflows in long tabs. These 20 design views
separate that information for review; they are **not 20 already implemented routes**.

| View | Existing workflow / proposed presentation |
|---|---|
| 01 Access | Portal entry with continuation to OIDC; no replacement credential form |
| 02 Overview | Scoped counts, register, attention queue and audit activity |
| 03 Institution directory | Institution list and declared/registry distinction |
| 04 Onboarding | Institution, policy context and initial obligation declaration |
| 05 Institution profile / obligation | Institutional factors, provisional rule reference and registry evidence |
| 06 Deposit register | Instrument list, search, filtering and export |
| 07 Deposit registration | Type-specific declaration, draft and supporting-proof sequence |
| 08 Deposit record | Independent administrative/source/temporal states and evidence revisions |
| 09 Evidence workspace | Original preview, selected region, typed transcription and independent confirmation |
| 10 Scrutiny / correction | Evaluation findings, return with reason and blocked acceptance |
| 11 Release queue | Cases, clearances, holds and administrative progress |
| 12 Clearance / issuance | Independent bureau decisions, blocked approval, later synthetic issuance / reconciliation states |
| 13 Maturity / reminders | Due dates, product-policy bands, SMTP attempts and bounded synthetic clock |
| 14 Renewal / replacement | Independent authorization, original evidence and lineage |
| 15 Management reports | Scoped totals, workload, CSV and measurement limitations |
| 16 Interventions / policy | Source follow-up, acknowledgement, resolution history, SLAs and supervisor configuration |
| 17 Audit | Actor/time/action/reason and retained evidence provenance |
| 18 Legacy import | CSV validation, per-row errors, unchanged-hash commit and draft-only result |
| 19 Access assignments | Technical operator scopes, expiry and separation from financial authority |
| 20 Sandbox integrations | Independent observed/declaration comparison, delayed/retry states and source limitations |

Before implementation, select one direction or a specific combination. Preserve human
approval, current permissions, synthetic source labels, evidence provenance, immutable
history and failure/empty/loading states. Copy exact production fields, validation and
action permissions from existing API contracts when implementing; mockup buttons are
not permission specifications. New presentation groupings should not introduce new
business capabilities. Responsive, keyboard and real-service regression checks remain
required during the future implementation phase.

Preview QA: all 60 desktop combinations (20 views × 3 directions), 21 representative
mobile combinations at 390px, the state selector and concept-image dialog were checked
in Chromium. No page script errors or whole-page horizontal overflow were observed.
Evidence is retained under ignored `.local/ui-concepts`. This is design-artifact QA,
not another execution of the application PostgreSQL/workflow suite.
