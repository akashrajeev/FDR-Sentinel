import { useEffect, useState } from "react";
import { currentPersona, demoApi, hasDemoStorage } from "./engine";
import { personas, type Persona } from "./model";
import type { Schemas } from "../api";
import "./demo.css";

type Props = {
  revision: string;
  onRole: (role: Persona) => Promise<void>;
  onReset: () => Promise<void>;
  onScenario: (target: string, role: Persona) => Promise<void>;
};
const scenarios: {
  name: string;
  target: string;
  role: Persona;
  note: string;
}[] = [
  {
    name: "New submission",
    target: "fdr00001-demo",
    role: "institution",
    note: "Attach the sample proof, run evaluation and submit. Switch to Review officer to accept registration.",
  },
  {
    name: "OCR and advisory AI",
    target: "fdr00008-demo",
    role: "institution",
    note: "Inspect the sample page and advisory proposal. Prepare a human correction with its evidence region; a different reviewer must confirm it. No model is called in this deployment.",
  },
  {
    name: "Worker and source recovery",
    target: "fdr00009-demo",
    role: "reviewer",
    note: "Retry failed document processing, then retry the dead-letter source exchange. States progress in the browser; no actual worker or external service runs.",
  },
  {
    name: "Policy revalidation",
    target: "fdr00010-demo",
    role: "reviewer",
    note: "This accepted sample is stale. Request fresh scrutiny; historical officer decisions remain visible while the record returns to draft for reevaluation.",
  },
  {
    name: "Unknown regulatory context",
    target: "fdr00011-demo",
    role: "reviewer",
    note: "The sample evaluator returns REQUIRES HUMAN REVIEW for this exceptional context. It cannot certify unknown applicability or authorize release.",
  },
  {
    name: "Evidence mismatch",
    target: "fdr00002-demo",
    role: "reviewer",
    note: "The declaration says INR 30 lakh; evidence says INR 35 lakh. Return it, switch to Institution maker, correct to 35 lakh and reevaluate. Resolve the discrepancy as reviewer before acceptance.",
  },
  {
    name: "PGRC blocks release",
    target: "case0001-demo",
    role: "approver",
    note: "Attempt approval with a reason and acknowledgement. PGRC is pending. Continue the guided journey to clear PGRC, approve independently and issue a sample NOC.",
  },
  {
    name: "Active legal hold",
    target: "case0002-demo",
    role: "approver",
    note: "Clearing PGRC still leaves a legal hold. Resolve it with sample evidence before approval can proceed.",
  },
  {
    name: "RTGS sanction branch",
    target: "case0003-demo",
    role: "approver",
    note: "The RTGS record has no invented FDR maturity. Complete PGRC, approval and separate issuance to download a sample sanction.",
  },
  {
    name: "Renewal and maturity",
    target: "Release cases",
    role: "reviewer",
    note: "Authorize the preloaded renewal with a policy basis. The original stays in the register as REPLACED. Run the maturity monitor to see simulated reminders.",
  },
  {
    name: "Reports and escalation",
    target: "Reports",
    role: "reviewer",
    note: "Filter tasks, inspect source evidence, acknowledge follow-up and run the intervention scan. Acknowledgement does not resolve a source condition. CSV exports work locally.",
  },
  {
    name: "Institution onboarding",
    target: "Institutions",
    role: "institution",
    note: "Declare a fictional institution using a SYN- identifier. Only the simple Engineering UG fixture is evaluated; other contexts require human review.",
  },
  {
    name: "Scoped assignments",
    target: "Operator",
    role: "operator",
    note: "Explore operator provisioning using fictional principals. These browser assignments are demonstrations, never backend access grants.",
  },
  {
    name: "Legacy import",
    target: "Legacy import",
    role: "institution",
    note: "Preview the bundled sample or upload a synthetic CSV using the downloaded template. Local validation, unchanged-file checks, duplicate rejection and draft-only import are supported.",
  },
];
export default function DemoControls({
  revision,
  onRole,
  onReset,
  onScenario,
}: Props) {
  const [scenario, setScenario] = useState(
    scenarios.find((s) => s.name === "PGRC blocks release")!,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reset, setReset] = useState(false);
  const [guide, setGuide] = useState(false);
  const [inbox, setInbox] = useState(false);
  const [notices, setNotices] = useState<
    {
      id: string;
      kind: string;
      recipient: string;
      delivery: { state: string };
      detail: unknown;
    }[]
  >([]);
  useEffect(() => {
    if (!inbox) return;
    let active = true;
    const load = () =>
      demoApi<typeof notices>("/notifications")
        .then((n) => {
          if (active) setNotices(n);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    load();
    const timer = setInterval(load, 2000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [inbox, revision]);
  const role = currentPersona();
  async function act(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function next() {
    const cases = await demoApi<Schemas["ReleaseOut"][]>("/release-cases");
    const c = cases.find(
      (c) =>
        c.id ===
        (scenario.target.startsWith("case")
          ? scenario.target
          : "case0001-demo"),
    )!;
    const role: Persona =
      c.state === "ISSUED_SYNTHETIC"
        ? "auditor"
        : c.state === "APPROVED_SYNTHETIC"
          ? "issuer"
          : c.required_bureaus.some(
                (b) =>
                  !c.clearances.some(
                    (x) => x.bureau === b && x.decision === "CLEARED",
                  ),
              )
            ? "pgrc"
            : "approver";
    await onScenario(role === "auditor" ? "Audit trail" : c.id, role);
  }
  return (
    <section
      className="demo-controls"
      aria-label="Interactive demo controls"
      data-revision={revision}
    >
      <div className="demo-control-head">
        <div>
          <p className="eyebrow">JUDGES’ WORKSPACE</p>
          <h2>Explore the working interface</h2>
          <p>
            Every action here is a browser simulation. Your changes stay with
            you.
          </p>
        </div>
        <label className="field">
          <span>Demo persona</span>
          <select
            value={role}
            disabled={busy}
            onChange={(e) => act(() => onRole(e.target.value as Persona))}
          >
            {personas.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="demo-scenario-row">
        <label className="field">
          <span>Explore a scenario</span>
          <select
            value={scenario.name}
            disabled={busy}
            onChange={(e) => {
              const next = scenarios.find((s) => s.name === e.target.value)!;
              setScenario(next);
              setGuide(true);
              act(() => onScenario(next.target, next.role));
            }}
          >
            <option value="" disabled>
              Choose a scenario
            </option>
            {scenarios.map((s) => (
              <option key={s.name}>{s.name}</option>
            ))}
          </select>
        </label>
        <button
          className="primary"
          disabled={busy}
          onClick={() => {
            setGuide(true);
            act(() => onScenario(scenario.target, scenario.role));
          }}
        >
          Start guided walkthrough
        </button>
        <button disabled={busy} onClick={() => setReset(!reset)}>
          Reset demo
        </button>
        <button onClick={() => setInbox(!inbox)}>
          Simulated notification inbox
        </button>
      </div>
      {guide && (
        <div className="demo-guide">
          <strong>{scenario.name}</strong>
          <p>{scenario.note}</p>
          {scenario.target.startsWith("case") && (
            <button disabled={busy} onClick={() => act(next)}>
              Continue guided journey →
            </button>
          )}
          <button className="text-button" onClick={() => setGuide(false)}>
            Hide guidance
          </button>
        </div>
      )}
      {reset && (
        <div
          className="demo-guide"
          role="group"
          aria-label="Confirm demo reset"
        >
          <p>
            Reset this browser’s synthetic records and history to the starting
            examples?
          </p>
          <button
            disabled={busy}
            onClick={() =>
              act(async () => {
                await onReset();
                setReset(false);
                setGuide(false);
              })
            }
          >
            Reset synthetic workspace
          </button>
          <button onClick={() => setReset(false)}>Keep progress</button>
        </div>
      )}
      {!hasDemoStorage() && (
        <p role="status">
          Browser storage is unavailable. You can explore, but progress will
          reset when this page closes.
        </p>
      )}
      {inbox && (
        <section
          className="demo-guide"
          aria-label="Simulated notification inbox"
        >
          <h3>Notification inbox · no emails sent</h3>
          {notices.length ? (
            notices.map((n) => (
              <article className="document" key={n.id}>
                <strong>{n.kind.replaceAll("_", " ")}</strong>
                <p>
                  To {n.recipient} · {n.delivery.state}
                </p>
                <pre>{JSON.stringify(n.detail, null, 2)}</pre>
              </article>
            ))
          ) : (
            <p>
              Run the maturity monitor or intervention scan to create synthetic
              reminders and escalations.
            </p>
          )}
        </section>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <details>
        <summary>
          What runs here, and what runs in the full application?
        </summary>
        <p>
          This static Vercel deployment runs React, local synthetic transitions,
          search, charts and exports. Sample extraction, identity, source
          checks, reminders and issuance are simulated. File intake and
          synthetic CSV validation run locally. No files are uploaded and no
          email or money is sent. Browser role selection and local history are
          not secure authentication or tamper-resistant audit.
        </p>
        <p>
          The full local application uses FastAPI, PostgreSQL, OIDC, private
          storage, antivirus/OCR, workers and independent fictional sandbox
          APIs. Its regulatory fixtures remain provisional; real bank/AICTE
          authorization and production qualification are separate.
        </p>
        <p>
          Demo date: 27 October 2026. Reset affects only this browser. Other
          visitors have independent workspaces. Changes in other tabs are not
          synchronized.
        </p>
      </details>
    </section>
  );
}
