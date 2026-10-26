import { useEffect, useState } from "react";
import { api, type Schemas } from "./api";
import { Icon } from "./Icon";

type Summary = Schemas["SummaryOut"];
type Interventions = { total: number; counts: Record<string, number> };
export function OverviewMetrics({ summary }: { summary: Summary | null }) {
  return (
    <div className="stats overview-stats">
      {[
        [
          summary
            ? Object.values(summary.workflow_counts).reduce((a, b) => a + b, 0)
            : "—",
          "recorded instruments",
          "Across your assigned scope",
        ],
        [
          summary?.workflow_counts.PENDING_SCRUTINY ?? (summary ? 0 : "—"),
          "awaiting scrutiny",
          "Independent officer review",
        ],
        [
          summary?.fdr_upcoming_90_days ?? "—",
          "due within 90 days",
          "Product monitoring window",
        ],
        [
          summary?.workflow_counts.ACCEPTED ?? (summary ? 0 : "—"),
          "registration accepted",
          "Separate from financial release",
        ],
      ].map(([value, label, note]) => (
        <div key={String(label)}>
          <strong>{value}</strong>
          <span>{label}</span>
          <small>{note}</small>
        </div>
      ))}
    </div>
  );
}

export function AttentionQueue({
  onNavigate,
  refreshKey,
}: {
  onNavigate: (name: string) => void;
  refreshKey: string;
}) {
  const [data, setData] = useState<Interventions | null>(null);
  const [overdue, setOverdue] = useState<number | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([
      api<Interventions>("/reports/interventions?limit=1"),
      api<Interventions>("/reports/interventions?limit=1&overdue=true"),
    ])
      .then(([all, late]) => {
        if (active) {
          setData(all);
          setOverdue(late.total);
          setUnavailable(false);
        }
      })
      .catch(() => {
        if (active) {
          setData(null);
          setOverdue(null);
          setUnavailable(true);
        }
      });
    return () => {
      active = false;
    };
  }, [refreshKey, revision]);
  return (
    <div className="overview-side">
      <section className="panel attention-panel">
        <div className="section-head">
          <h2>Needs attention</h2>
          <button
            className="text-button"
            onClick={() => setRevision((n) => n + 1)}
          >
            Refresh
          </button>
        </div>
        {unavailable ? (
          <p className="error" role="alert">
            Follow-up counts are temporarily unavailable.
          </p>
        ) : (
          <div aria-live="polite">
            {[
              [
                data ? (data.counts.UNRESOLVED_DISCREPANCY ?? 0) : "—",
                "Unresolved discrepancies",
                "Evidence or declaration needs review",
              ],
              [
                data ? (data.counts.BUREAU_CLEARANCE ?? 0) : "—",
                "Pending clearances",
                "Independent bureau decisions",
              ],
              [overdue ?? "—", "Overdue actions", "Product service levels"],
            ].map(([value, label, note]) => (
              <button
                className="attention-row"
                key={String(label)}
                onClick={() => onNavigate("Reports")}
              >
                <strong>{value}</strong>
                <span>
                  {label}
                  <small>{note}</small>
                </span>
                <Icon name="arrow" />
              </button>
            ))}
          </div>
        )}
        <button
          className="attention-link"
          onClick={() => onNavigate("Reports")}
        >
          Open intervention report <Icon name="arrow" />
        </button>
      </section>
      <section className="panel scope-note">
        <Icon name="shield" />
        <h2>Within your assigned scope</h2>
        <p>
          Each count comes from your scoped records. Unknown, pending and
          conflicting evidence requires review.
        </p>
        <button
          className="text-button"
          onClick={() => onNavigate("Release cases")}
        >
          Open release work queue
        </button>
      </section>
    </div>
  );
}

export function RecentActivity({
  events,
  onNavigate,
}: {
  events: Schemas["AuditOut"][];
  onNavigate: (name: string) => void;
}) {
  return (
    <section className="panel recent-activity">
      <div className="section-head">
        <div>
          <h2>Recent activity</h2>
          <p>Latest recorded actions in your institutional scope.</p>
        </div>
        <button
          className="text-button"
          onClick={() => onNavigate("Audit trail")}
        >
          Full audit history
        </button>
      </div>
      {events.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Date & time</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Record</th>
              </tr>
            </thead>
            <tbody>
              {events.slice(0, 5).map((e) => (
                <tr key={e.id}>
                  <td>
                    {new Date(e.created_at).toLocaleString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  <td title={e.actor}>
                    {e.actor.length > 24
                      ? `User · ${e.actor.slice(-8)}`
                      : e.actor}
                  </td>
                  <td>{e.action.replaceAll("_", " ").toLowerCase()}</td>
                  <td title={e.aggregate_id}>
                    {e.aggregate_id.slice(0, 8).toUpperCase()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">
          No recorded activity is available in this scope.
        </p>
      )}
    </section>
  );
}
