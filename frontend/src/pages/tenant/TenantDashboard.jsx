import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";
import { getTenantPaths } from "../../config/tenantDashboardNavigation";

const sessionStyle = {
  active: "text-success",
  completed: "text-info",
  cancelled: "text-danger",
};

const segments = [
  ["present", "Present", "bg-success", "stroke-success", "text-success"],
  ["late", "Late", "bg-warning", "stroke-warning", "text-warning"],
  ["absent", "Absent", "bg-danger", "stroke-danger", "text-danger"],
];

function Donut({ counts, total }) {
  const r = 40;
  const C = 2 * Math.PI * r;
  let offset = 0;

  return (
    <div className="relative mx-auto h-44 w-44 shrink-0">
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          strokeWidth="12"
          className="stroke-background-subtle"
        />
        {total > 0 &&
          segments.map(([key, , , stroke]) => {
            const len = (counts[key] / total) * C;
            const circle = (
              <circle
                key={key}
                cx="50"
                cy="50"
                r={r}
                fill="none"
                strokeWidth="12"
                strokeDasharray={`${len} ${C - len}`}
                strokeDashoffset={-offset}
                className={stroke}
              />
            );
            offset += len;
            return circle;
          })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-semibold tabular-nums">
          {total > 0 ? Math.round((counts.present / total) * 100) : 0}%
        </span>
        <span className="text-xs text-foreground-muted">on time</span>
      </div>
    </div>
  );
}

export default function TenantDashboard() {
  const navigate = useNavigate();
  const { tenant } = useAuth();
  const paths = getTenantPaths(tenant.slug);

  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  updateTitle("Dashboard");
  useUpdatePageTitle("Dashboard");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get("/tenant/stats/");
        setStats(res.data);
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
    ["Total users", stats.total_users ?? 0],
    ["Active users", stats.active_users ?? 0],
    [
      "Face enrolled",
      `${stats.users_with_face ?? 0} / ${stats.total_users ?? 0}`,
    ],
    ["Sessions", stats.total_sessions ?? 0],
  ];

  const byStatus = stats.attendance_by_status ?? {};
  const counts = {
    present: byStatus.present ?? 0,
    late: byStatus.late ?? 0,
    absent: byStatus.absent ?? 0,
  };
  const total = counts.present + counts.late + counts.absent;

  const recent = stats.recent_sessions ?? [];
  const chartData = [...recent].reverse();

  return (
    <div className="space-y-8 p-6">
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

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center border-b border-white/10 px-4 text-sm font-medium">
          Overall attendance
        </div>
        <div className="grid items-center gap-8 p-6 md:grid-cols-[auto_1fr]">
          <Donut counts={counts} total={total} />
          <div className="grid gap-4 sm:grid-cols-3">
            {segments.map(([key, label, bg, , text]) => (
              <div
                key={key}
                className="border border-white/10 bg-background-elevated p-4"
              >
                <div className="flex items-center gap-2 text-sm text-foreground-muted">
                  <span className={`h-2.5 w-2.5 ${bg}`} />
                  {label}
                </div>
                <div
                  className={`mt-2 text-3xl font-semibold tabular-nums ${text}`}
                >
                  {counts[key]}
                </div>
                <div className="mt-1 text-xs text-foreground-subtle">
                  {total > 0
                    ? `${Math.round((counts[key] / total) * 100)}% of records`
                    : "No records"}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
          <span className="text-sm font-medium">Attendance by session</span>
          <span className="text-xs text-foreground-subtle">
            Last {chartData.length} sessions
          </span>
        </div>
        {chartData.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No sessions yet.</p>
        ) : (
          <div className="p-4">
            <div className="flex h-56 items-end gap-3">
              {chartData.map((s) => {
                const t = s.present + s.late + s.absent;
                return (
                  <Link
                    key={s.id}
                    to={`${paths.sessions}/${s.id}`}
                    title={`${s.name}: ${s.present} present, ${s.late} late, ${s.absent} absent`}
                    className="group flex h-full flex-1 flex-col justify-end"
                  >
                    <div className="mb-1 text-center text-xs tabular-nums text-foreground-subtle">
                      {t}
                    </div>
                    <div className="flex min-h-1 flex-1 flex-col-reverse bg-background-subtle opacity-90 group-hover:opacity-100">
                      {t > 0 &&
                        segments.map(([key, , bg]) => (
                          <div
                            key={key}
                            className={bg}
                            style={{ height: `${(s[key] / t) * 100}%` }}
                          />
                        ))}
                    </div>
                  </Link>
                );
              })}
            </div>
            <div className="mt-2 flex gap-3">
              {chartData.map((s) => (
                <div
                  key={s.id}
                  className="flex-1 truncate text-center text-xs text-foreground-muted"
                  title={s.name}
                >
                  {s.name}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
          <span className="text-sm font-medium">Recent sessions</span>
          <Link
            to={paths.sessions}
            className="text-xs text-foreground-subtle hover:text-foreground"
          >
            View all
          </Link>
        </div>
        {recent.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No sessions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Started
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Present
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">Late</th>
                  <th className="px-4 py-2.5 text-right font-medium">Absent</th>
                  <th className="px-4 py-2.5 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {recent.slice(0, 5).map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => navigate(`${paths.sessions}/${s.id}`)}
                    className="cursor-pointer border-b border-white/5 last:border-0 hover:bg-background-elevated"
                  >
                    <td className="px-4 py-3">{s.name}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-success">
                      {s.present}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-warning">
                      {s.late}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-danger">
                      {s.absent}
                    </td>
                    <td
                      className={`px-4 py-3 text-right capitalize ${sessionStyle[s.status]}`}
                    >
                      {s.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
