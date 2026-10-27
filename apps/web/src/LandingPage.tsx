import { useState } from "react";
import { Brand, Icon } from "./Icon";
import { ThemePicker } from "./ThemePicker";
import { demoOnly, enterDemo } from "./demo/config";

export function LandingPage({
  onSignIn,
  error,
}: {
  onSignIn: () => Promise<void>;
  error: string;
}) {
  const [entering, setEntering] = useState(false);
  const [failure, setFailure] = useState("");
  async function signIn() {
    setEntering(true);
    setFailure("");
    try {
      await onSignIn();
    } catch {
      setFailure("Sign-in is temporarily unavailable. Please try again.");
      setEntering(false);
    }
  }
  return (
    <div className="landing">
      <a className="skip-link" href="#home-content">
        Skip to content
      </a>
      <header className="landing-header">
        <Brand />
        <nav aria-label="Platform information">
          <a href="#workflow">Workflow</a>
          <a href="#access-guide">Who can sign in</a>
          <a href="#demo-environment">About this environment</a>
        </nav>
        <span className="project-label">
          SIH 2026 <span>/</span> SIH26265
        </span>
        <ThemePicker />
      </header>
      <main id="home-content" className="landing-content">
        <section className="landing-hero" aria-labelledby="home-title">
          <div className="landing-intro">
            <p className="eyebrow">INSTITUTIONAL SECURITY DEPOSITS</p>
            <h1 id="home-title">
              Security deposit &amp;
              <br />
              FDR management.
            </h1>
            <p className="landing-description">
              Submit deposit records, review document evidence and follow each
              case through maturity, renewal and release scrutiny.
            </p>
            <div className="landing-entry">
              <button className="primary" onClick={enterDemo}>
                Explore interactive demo <Icon name="arrow" />
              </button>
              {!demoOnly && (
                <button disabled={entering} onClick={signIn}>
                  {entering ? "Connecting to sign-in…" : "Sign in securely"}
                  <Icon name="arrow" />
                </button>
              )}
              <span>
                No account needed for the demo. Explore every role with
                synthetic records.
              </span>
            </div>
            {(failure || error) && (
              <p className="error" role="alert">
                {failure || error}
              </p>
            )}
            <p className="landing-signin-note">
              <Icon name="shield" />{" "}
              {demoOnly
                ? "Interactive browser simulation. No live bank connections or financial authority."
                : "Secure sign-in continues to the identity provider. Demo access stays separate."}
            </p>
          </div>
          <div
            className="lifecycle-preview"
            aria-label="Deposit lifecycle overview"
          >
            <div className="lifecycle-header">
              <Icon name="deposits" />
              <div>
                <strong>A record through its lifecycle</strong>
                <small>
                  Documents, source evidence and decisions stay linked.
                </small>
              </div>
            </div>
            <ol>
              {[
                [
                  "Institution submission",
                  "Declared instrument details and supporting proof.",
                ],
                [
                  "Evidence & scrutiny",
                  "Protected documents, discrepancy review and correction.",
                ],
                [
                  "Independent clearances",
                  "Bureau decisions, holds and competent approval.",
                ],
                [
                  "Recorded outcome",
                  "Authorized synthetic issuance and retained history.",
                ],
              ].map(([title, description], i) => (
                <li key={title}>
                  <span className="lifecycle-number">0{i + 1}</span>
                  <div>
                    <strong>{title}</strong>
                    <p>{description}</p>
                  </div>
                </li>
              ))}
            </ol>
            <div className="lifecycle-footer">
              <Icon name="shield" />
              <span>
                Financial and regulatory decisions require human approval.
              </span>
            </div>
          </div>
        </section>
        <section
          id="workflow"
          className="landing-workflow"
          aria-labelledby="workflow-title"
        >
          <div className="landing-section-heading">
            <p className="eyebrow">THE WORKFLOW</p>
            <h2 id="workflow-title">One connected administrative record.</h2>
            <p>
              Institution declarations, document findings and independent source
              responses remain distinct throughout review.
            </p>
          </div>
          <div className="workflow-columns">
            {[
              [
                "01",
                "Register & submit",
                "Maintain institution-wise obligations and deposit records with the prescribed supporting documents.",
              ],
              [
                "02",
                "Review & resolve",
                "Inspect evidence, return deficient submissions and retain the original record through corrections.",
              ],
              [
                "03",
                "Monitor & renew",
                "Track maturity dates, replacement lineage and reminders for unresolved work.",
              ],
              [
                "04",
                "Clear & authorize",
                "Record independent bureau decisions and approval before any synthetic release output.",
              ],
            ].map(([number, title, text]) => (
              <article key={number}>
                <span>{number}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
        <section
          id="access-guide"
          className="access-guide"
          aria-labelledby="access-title"
        >
          <div className="landing-section-heading">
            <p className="eyebrow">WORKSPACE ACCESS</p>
            <h2 id="access-title">The right view for each responsibility.</h2>
          </div>
          <div className="access-columns">
            <article>
              <Icon name="institutions" />
              <h3>Institution members</h3>
              <p>
                Onboard an institution, submit deposit evidence and follow
                correction, renewal and release requests.
              </p>
            </article>
            <article>
              <Icon name="shield" />
              <h3>Assigned officers</h3>
              <p>
                Review evidence and perform the decisions permitted by your
                institution, case and bureau assignments.
              </p>
            </article>
            <article>
              <Icon name="audit" />
              <h3>Authorized auditors</h3>
              <p>
                Inspect scoped records, management reports and the history of
                submissions and decisions.
              </p>
            </article>
          </div>
        </section>
        <section id="demo-environment" className="landing-environment">
          <div>
            <span className="environment-label">DEMONSTRATION ENVIRONMENT</span>
            <h2>
              {demoOnly
                ? "Explore the workflows. Synthetic records."
                : "Real workflows. Synthetic records."}
            </h2>
          </div>
          <p>
            {demoOnly
              ? "This public demo runs entirely in your browser. Identity, extraction, bank/AICTE responses and processing are simulated. Policy fixtures are provisional and no actual financial release takes place."
              : "The bank and AICTE connections are independent local sandboxes. Official systems are not connected, policy fixtures are provisional, and no actual financial release takes place."}
          </p>
        </section>
      </main>
      <footer className="landing-footer">
        <span>
          FDR Sentinel <span className="footer-divider">/</span> SIH26265
        </span>
        <span>Security Deposit / FDR Management Portal · SIH 2026 project</span>
      </footer>
    </div>
  );
}
