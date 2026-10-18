import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const sessionStyle = {
  active: "text-success",
  completed: "text-info",
  cancelled: "text-danger",
};

const attendanceStyle = {
  present: "bg-success",
  late: "bg-warning",
  absent: "bg-danger",
};

export default function Dashboard() {
  const { updatePageTitle } = usePageTitle();
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    updatePageTitle("Dashboard");
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const statsRes = await api.get("/admin/stats/");
        setStats(statsRes.data);

        // the backend returns 404 when there are no sessions yet
        try {
          const sessionsRes = await api.get("/admin/sessions/");
          setSessions(sessionsRes.data.sessions);
        } catch (err) {
          if (err.response?.status !== 404) throw err;
        }
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load the dashboard."));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  if (error || !stats) {
    return (
      <div className="p-6">
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error || "No data available."}
        </Alert>
      </div>
    );
  }

  const cards = [
    ["Total users", stats.total_users],
    ["Active users", stats.active_users],
    ["Face enrolled", `${stats.users_with_face} / ${stats.total_users}`],
    ["Sessions", stats.total_sessions],
  ];

  const byStatus = stats.attendance_by_status ?? {};
  const totalRecords = Object.values(byStatus).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-8 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <div className="flex gap-3">
          <Link
            to="/admin/users"
            className="rounded-sm border border-white/10 px-4 py-2 text-sm hover:bg-background-elevated"
          >
            Manage users
          </Link>
          <Link
            to="/admin/sessions"
            className="rounded-sm bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Sessions
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <section className="grid border-l border-t border-white/10 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(([label, value]) => (
          <div
            key={label}
            className="border-b border-r border-white/10 bg-background-surface p-6"
          >
            <div className="text-3xl font-semibold tabular-nums">{value}</div>
            <div className="mt-1 text-sm text-foreground-muted">{label}</div>
          </div>
        ))}
      </section>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Attendance breakdown */}
        <section className="border border-white/10 bg-background-surface">
          <div className="border-b border-white/10 px-4 py-3 text-sm font-medium">
            Attendance breakdown
          </div>
          <div className="space-y-4 p-4">
            {totalRecords === 0 ? (
              <p className="text-sm text-foreground-muted">
                No attendance recorded yet.
              </p>
            ) : (
              ["present", "late", "absent"].map((key) => {
                const count = byStatus[key] ?? 0;
                const pct = Math.round((count / totalRecords) * 100);
                return (
                  <div key={key}>
                    <div className="flex justify-between text-sm">
                      <span className="capitalize">{key}</span>
                      <span className="tabular-nums text-foreground-muted">
                        {count} · {pct}%
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 bg-background-subtle">
                      <div
                        className={`h-full ${attendanceStyle[key]}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* Recent sessions */}
        <section className="border border-white/10 bg-background-surface lg:col-span-2">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <span className="text-sm font-medium">Recent sessions</span>
            <Link
              to="/admin/sessions"
              className="text-xs text-foreground-subtle hover:text-foreground"
            >
              View all
            </Link>
          </div>
          {sessions.length === 0 ? (
            <p className="p-4 text-sm text-foreground-muted">
              No sessions yet.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Started</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {sessions.slice(0, 5).map((s) => (
                  <tr
                    key={s.id}
                    className="border-b border-white/5 last:border-0"
                  >
                    <td className="px-4 py-3">{s.name}</td>
                    <td className="px-4 py-3 tabular-nums text-foreground-muted">
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                    <td
                      className={`px-4 py-3 capitalize ${sessionStyle[s.status]}`}
                    >
                      {s.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}
