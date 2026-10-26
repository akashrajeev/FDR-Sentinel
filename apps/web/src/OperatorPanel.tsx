import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

type Workspace = {
  institutions: { id: string; legal_name: string; external_id: string }[];
  principals: { subject: string; enabled: boolean; label: string }[];
  bindings: {
    id: string;
    subject: string;
    role: string;
    scope_type: string;
    scope_id: string;
    enabled: boolean;
    valid_until: string | null;
  }[];
};
export function OperatorPanel() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [scopeType, setScopeType] = useState("INSTITUTION");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(
    async () => setWorkspace(await api<Workspace>("/operator/workspace")),
    [],
  );
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, [refresh]);
  const submit = async (body: Record<string, unknown>) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api("/operator/assignments", body);
      await refresh();
      setNotice("Scoped assignment committed with operator audit evidence.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="panel">
      <h2>Technical operator workspace</h2>
      <p>
        Assign independent officers to declared institutions or cases. Operator
        access does not grant financial decisions or document access.
        Self-grants and operator-role grants are prohibited.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {workspace && (
        <>
          <form
            className="form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              const data = Object.fromEntries(new FormData(e.currentTarget));
              submit({ ...data, enabled: true });
            }}
          >
            <label className="field">
              <span>Officer principal</span>
              <select name="subject" aria-label="Officer principal" required>
                {workspace.principals
                  .filter((p) => p.enabled)
                  .map((p) => (
                    <option key={p.subject} value={p.subject}>
                      {p.label} · {p.subject.slice(-8)}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field">
              <span>Assigned role</span>
              <select name="role" aria-label="Assigned role">
                <option>REVIEWER</option>
                <option>AUDITOR</option>
                <option>CLEARANCE</option>
                <option>APPROVER</option>
                <option>ISSUER</option>
              </select>
            </label>
            <label className="field">
              <span>Scope type</span>
              <select
                name="scope_type"
                aria-label="Scope type"
                value={scopeType}
                onChange={(e) => setScopeType(e.target.value)}
              >
                <option>INSTITUTION</option>
                <option>CASE</option>
                <option>BUREAU</option>
              </select>
            </label>
            <label className="field">
              <span>Assigned scope</span>
              {scopeType === "INSTITUTION" ? (
                <select name="scope_id" aria-label="Assigned scope" required>
                  {workspace.institutions.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.legal_name} · {i.external_id}
                    </option>
                  ))}
                </select>
              ) : scopeType === "BUREAU" ? (
                <select name="scope_id" aria-label="Assigned scope">
                  <option>PGRC</option>
                  <option>VIGILANCE</option>
                  <option>GRANTS</option>
                  <option>APPROVAL_BUREAU</option>
                  <option>COUNCIL</option>
                </select>
              ) : (
                <input
                  name="scope_id"
                  placeholder="Exact existing case ID"
                  required
                />
              )}
            </label>
            <label className="field full">
              <span>Assignment reason</span>
              <textarea
                name="reason"
                minLength={10}
                maxLength={2000}
                required
              />
            </label>
            <p>
              Assignments expire after 30 days. Bureau authority also needs
              institution/case access; existing maker/checker separation remains
              enforced.
            </p>
            <button disabled={busy}>Assign scoped officer</button>
          </form>
          <h3>Current scope assignments</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Principal</th>
                  <th>Role</th>
                  <th>Scope</th>
                  <th>Validity</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {workspace.bindings.map((b) => (
                  <tr key={b.id}>
                    <td>
                      {workspace.principals.find((p) => p.subject === b.subject)
                        ?.label ?? b.subject}
                    </td>
                    <td>{b.role}</td>
                    <td>
                      {b.scope_type} · {b.scope_id}
                    </td>
                    <td>
                      {b.enabled
                        ? (b.valid_until ??
                          "Operator-provisioned ongoing scope")
                        : "DISABLED"}
                    </td>
                    <td>
                      {b.role !== "MAKER" && b.role !== "OPERATOR" && (
                        <button
                          disabled={busy}
                          onClick={() => {
                            const reason = window.prompt(
                              "Reason for changing this assignment (at least 10 characters)",
                            );
                            if (reason)
                              submit({
                                subject: b.subject,
                                role: b.role,
                                scope_type: b.scope_type,
                                scope_id: b.scope_id,
                                enabled: !b.enabled,
                                reason,
                              });
                          }}
                        >
                          {b.enabled ? "Disable" : "Enable"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
