import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const inputClass =
  "rounded-sm border border-white/10 bg-background-elevated px-3 py-2 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const sessionStyle = {
  active: "text-success",
  completed: "text-info",
  cancelled: "text-danger",
};

const statusStyle = {
  present: "text-success",
  late: "text-warning",
  absent: "text-danger",
  unset: "text-foreground-subtle",
};

const filters = [
  ["all", "All"],
  ["present", "Present"],
  ["late", "Late"],
  ["absent", "Absent"],
  ["unset", "Not set"],
];

export default function SessionDetail() {
  const { id } = useParams();
  const { updatePageTitle } = usePageTitle();

  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [savingId, setSavingId] = useState(null);

  useEffect(() => {
    updatePageTitle("Session");
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/attendance/session/${id}/`);
        // this endpoint answers 200 with an "error" key for an unknown session
        if (res.data.error) {
          setError(res.data.error);
          return;
        }
        setData(res.data);
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load the session."));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [id]);

  const counts = useMemo(() => {
    const c = { all: 0, present: 0, late: 0, absent: 0, unset: 0 };
    (data?.attendance ?? []).forEach((a) => {
      c.all += 1;
      c[a.status ?? "unset"] += 1;
    });
    return c;
  }, [data]);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data?.attendance ?? []).filter((a) => {
      if (filter !== "all" && (a.status ?? "unset") !== filter) return false;
      if (q && !(a.first_name ?? "").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [data, filter, search]);

  const onOverride = async (userId, status) => {
    if (!status) return;
    setSavingId(userId);
    setError("");
    try {
      await api.put("/admin/attendance/override/", {
        user_id: userId,
        session_id: Number(id),
        status,
      });
      setData((prev) => ({
        ...prev,
        attendance: prev.attendance.map((a) =>
          a.user_id === userId ? { ...a, status } : a,
        ),
      }));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to update the attendance."));
    } finally {
      setSavingId(null);
    }
  };

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  if (!data) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error || "Session not found."}
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

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link
          to="/admin/sessions"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to sessions
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {data.session_name}
          </h1>
          <span
            className={`text-sm capitalize ${sessionStyle[data.session_status]}`}
          >
            {data.session_status}
          </span>
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Summary */}
      <section className="grid border-l border-t border-white/10 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Present", counts.present, "text-success"],
          ["Late", counts.late, "text-warning"],
          ["Absent", counts.absent, "text-danger"],
          ["Not set", counts.unset, "text-foreground-subtle"],
        ].map(([label, value, color]) => (
          <div
            key={label}
            className="border-b border-r border-white/10 bg-background-surface p-6"
          >
            <div className={`text-3xl font-semibold tabular-nums ${color}`}>
              {value}
            </div>
            <div className="mt-1 text-sm text-foreground-muted">{label}</div>
          </div>
        ))}
      </section>

      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {filters.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`cursor-pointer rounded-sm border px-3 py-1.5 text-sm ${
                filter === key
                  ? "border-primary bg-primary text-white"
                  : "border-white/10 text-foreground-muted hover:bg-background-elevated"
              }`}
            >
              {label} · {counts[key]}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Search name"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={`${inputClass} w-full sm:w-64`}
        />
      </div>

      {/* Users */}
      <section className="border border-white/10 bg-background-surface">
        {rows.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No users found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Set status
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => {
                  const key = a.status ?? "unset";
                  return (
                    <tr
                      key={a.user_id}
                      className="border-b border-white/5 last:border-0 hover:bg-background-elevated"
                    >
                      <td className="px-4 py-3">{a.first_name || "—"}</td>
                      <td
                        className={`px-4 py-3 capitalize ${statusStyle[key]}`}
                      >
                        {a.status ?? "Not set"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <select
                          value={a.status ?? ""}
                          disabled={savingId === a.user_id}
                          onChange={(e) =>
                            onOverride(a.user_id, e.target.value)
                          }
                          className="cursor-pointer rounded-sm border border-white/10 bg-background-elevated px-2 py-1 text-sm focus:outline-none disabled:opacity-60"
                        >
                          <option value="" disabled>
                            Not set
                          </option>
                          <option value="present">Present</option>
                          <option value="late">Late</option>
                          <option value="absent">Absent</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
