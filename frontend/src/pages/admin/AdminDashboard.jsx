import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";

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

function TenantTable({ title, tenants, onOpen, showViewAll }) {
  return (
    <section className="flex h-full flex-col border border-white/10 bg-background-surface">
      <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
        <span className="text-sm font-medium">{title}</span>
        {showViewAll && (
          <Link
            to="/admin/tenants"
            className="text-xs text-foreground-subtle hover:text-foreground"
          >
            View all
          </Link>
        )}
      </div>
      {tenants.length === 0 ? (
        <p className="p-4 text-sm text-foreground-muted">No tenants yet.</p>
      ) : (
        <div className="flex-1 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                <th className="px-4 py-2.5 font-medium">Name</th>
                <th className="px-4 py-2.5 text-right font-medium">Sessions</th>
                <th className="px-4 py-2.5 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => onOpen(t.id)}
                  className="cursor-pointer border-b border-white/5 last:border-0 hover:bg-background-elevated"
                >
                  <td className="px-4 py-3">
                    <div>{t.name}</div>
                    <div className="text-xs text-foreground-subtle">
                      {t.slug}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                    {t.session_count ?? 0}
                  </td>
                  <td
                    className={`px-4 py-3 text-right ${
                      t.is_active ? "text-success" : "text-danger"
                    }`}
                  >
                    {t.is_active ? "Active" : "Suspended"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function SuperAdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  updateTitle("Dashboard");
  useUpdatePageTitle("Super Admin Dashboard");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get("/admin/stats/");
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

  const tenants = stats.tenants ?? {};
  const users = stats.users ?? {};
  const members = users.members ?? 0;
  const withFace = users.with_face ?? 0;

  const cards = [
    ["Tenants", tenants.total ?? 0],
    ["Active tenants", tenants.active ?? 0],
    ["Suspended tenants", tenants.suspended ?? 0],
    ["Sessions", stats.sessions ?? 0],
    ["Members", members],
    ["Tenant admins", users.admins ?? 0],
    ["Face enrolled", `${withFace} / ${members}`],
    [
      "Enrollment rate",
      `${members > 0 ? Math.round((withFace / members) * 100) : 0}%`,
    ],
  ];

  const byStatus = stats.attendance_by_status ?? {};
  const counts = {
    present: byStatus.present ?? 0,
    late: byStatus.late ?? 0,
    absent: byStatus.absent ?? 0,
  };
  const total = counts.present + counts.late + counts.absent;

  const openTenant = (id) => navigate(`/admin/tenants/${id}`);

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
          Attendance across all tenants
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

      <div className="grid items-stretch gap-8 lg:grid-cols-2">
        <TenantTable
          title="Newest tenants"
          tenants={stats.newest_tenants ?? []}
          onOpen={openTenant}
          showViewAll
        />
        <TenantTable
          title="Busiest tenants"
          tenants={stats.busiest_tenants ?? []}
          onOpen={openTenant}
        />
      </div>
    </div>
  );
}
