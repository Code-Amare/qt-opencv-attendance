import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";

const badgeStyle = {
  present: "bg-success/10 text-success",
  late: "bg-warning/10 text-warning",
  absent: "bg-danger/10 text-danger",
};

const sessionStyle = {
  active: "text-success",
  completed: "text-info",
  cancelled: "text-danger",
};

const filters = [
  ["", "All"],
  ["present", "Present"],
  ["late", "Late"],
  ["absent", "Absent"],
];

const PAGE_SIZE = 10;

const fmt = (v) =>
  v
    ? new Date(v).toLocaleString([], {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

export default function UserAttendanceHistory() {
  const { userId } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  updateTitle("Attendance History");
  useUpdatePageTitle("Attendance History");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get(`/attendance/users/${userId}/history/`, {
        params: { page, page_size: PAGE_SIZE, status: filter || undefined },
      })
      .then((res) => {
        if (cancelled) return;
        setData(res.data);
        setError("");
      })
      .catch((err) => {
        if (!cancelled)
          setError(getErrorMessage(err, "Failed to load attendance history."));
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [userId, page, filter]);

  const changeFilter = (key) => {
    setFilter(key);
    setPage(1);
  };

  if (!data && loading)
    return <p className="p-6 text-foreground-muted">Loading…</p>;

  if (!data) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="error" title="Error">
          {error || "User not found."}
        </Alert>
        <Link
          to="/admin/sessions"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to sessions
        </Link>
      </div>
    );
  }

  const { user, summary, results, count, total_pages } = data;
  const from = count === 0 ? 0 : (data.page - 1) * data.page_size + 1;
  const to = Math.min(data.page * data.page_size, count);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <button
        onClick={() => navigate(-1)}
        className="cursor-pointer text-sm text-foreground-muted hover:text-foreground"
      >
        ← Go back
      </button>

      <section className="rounded-lg border border-white/10 bg-background-surface p-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          {`${user.first_name} ${user.last_name}`.trim() || `User #${user.id}`}
        </h1>
        <p className="mt-1 text-sm text-foreground-muted">Attendance history</p>
        <div className="mt-4 grid grid-cols-3 gap-3">
          {[
            ["Present", summary.present, "text-success"],
            ["Late", summary.late, "text-warning"],
            ["Absent", summary.absent, "text-danger"],
          ].map(([label, value, color]) => (
            <div key={label} className="rounded-md bg-background-elevated p-4">
              <div className={`text-2xl font-semibold tabular-nums ${color}`}>
                {value}
              </div>
              <div className="text-sm text-foreground-muted">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <div className="flex flex-wrap gap-2">
        {filters.map(([key, label]) => (
          <button
            key={key || "all"}
            onClick={() => changeFilter(key)}
            className={`cursor-pointer rounded-full border px-3 py-1.5 text-sm transition-colors ${
              filter === key
                ? "border-primary bg-primary text-white"
                : "border-white/10 text-foreground-muted hover:bg-background-elevated"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <section
        className={`overflow-hidden rounded-lg border border-white/10 bg-background-surface ${
          loading ? "opacity-60" : ""
        }`}
      >
        {results.length === 0 ? (
          <p className="p-6 text-sm text-foreground-muted">
            No attendance records found.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-5 py-3 font-medium">Session</th>
                  <th className="px-5 py-3 font-medium">Starts</th>
                  <th className="px-5 py-3 font-medium">Session status</th>
                  <th className="px-5 py-3 font-medium">Attendance</th>
                  <th className="px-5 py-3 font-medium">Recorded at</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-white/5 last:border-0 hover:bg-background-elevated"
                  >
                    <td className="px-5 py-3">
                      <Link
                        to={`/admin/sessions/${r.session_id}`}
                        className="hover:text-primary-hover"
                      >
                        {r.session_name}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-foreground-muted">
                      {fmt(r.started_at)}
                    </td>
                    <td
                      className={`px-5 py-3 capitalize ${sessionStyle[r.session_status]}`}
                    >
                      {r.session_status}
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${badgeStyle[r.status]}`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-foreground-muted">
                      {fmt(r.recorded_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between border-t border-white/10 px-5 py-3 text-sm text-foreground-muted">
          <span>
            {from}–{to} of {count}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => p - 1)}
              disabled={data.page <= 1 || loading}
              className="cursor-pointer rounded-md border border-white/10 px-3 py-1 hover:bg-background-elevated disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>
            <span className="tabular-nums">
              {data.page} / {total_pages}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={data.page >= total_pages || loading}
              className="cursor-pointer rounded-md border border-white/10 px-3 py-1 hover:bg-background-elevated disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
