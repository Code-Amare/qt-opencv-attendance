import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";
import { getTenantPaths } from "../../config/tenantDashboardNavigation";

const statusStyle = {
  active: "text-success",
  completed: "text-info",
  cancelled: "text-danger",
};

const toMinutes = (duration) => {
  const m = String(duration ?? "").match(/^(?:(\d+) )?(\d+):(\d+):(\d+)/);
  if (!m) return 10;
  return Number(m[1] ?? 0) * 1440 + Number(m[2]) * 60 + Number(m[3]);
};

export default function Sessions() {
  const navigate = useNavigate();
  const { tenant } = useAuth();
  const paths = getTenantPaths(tenant.slug);

  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [changingId, setChangingId] = useState(null);
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  updateTitle("Sessions");
  useUpdatePageTitle("Sessions");

  const load = async () => {
    setError("");
    try {
      const res = await api.get("/attendance/sessions/");
      setSessions(res.data.sessions ?? res.data.results ?? res.data);
    } catch (err) {
      if (err.response?.status === 404) {
        setSessions([]);
      } else {
        setError(getErrorMessage(err, "Failed to load sessions."));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onChangeState = async (session, status) => {
    setChangingId(session.id);
    setError("");
    try {
      const res = await api.patch(`/tenant/sessions/${session.id}/status/`, {
        status,
      });
      const updated = res.data.session ?? res.data;
      setSessions((prev) =>
        prev.map((s) => (s.id === session.id ? { ...s, ...updated } : s)),
      );
    } catch (err) {
      setError(getErrorMessage(err, "Failed to change the session state."));
    } finally {
      setChangingId(null);
    }
  };

  const onConfirmDelete = async () => {
    setDeleting(true);
    setError("");
    try {
      await api.delete(`/tenant/sessions/${sessionToDelete.id}/`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionToDelete.id));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to delete the session."));
    } finally {
      setDeleting(false);
      setSessionToDelete(null);
    }
  };

  return (
    <div className="space-y-6 p-6">
      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">All sessions</span>
            <span className="text-xs text-foreground-subtle">
              {sessions.length} {sessions.length === 1 ? "session" : "sessions"}
            </span>
          </div>
          <Link
            to={paths.sessionsNew}
            className="rounded-sm bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover"
          >
            New session
          </Link>
        </div>

        {loading ? (
          <p className="p-4 text-sm text-foreground-muted">Loading…</p>
        ) : sessions.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No sessions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 text-right font-medium">Starts</th>
                  <th className="px-4 py-2.5 text-right font-medium">Ends</th>
                  <th className="px-4 py-2.5 text-right font-medium">People</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Late window
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">State</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => navigate(paths.session(s.id))}
                    className="cursor-pointer border-b border-white/5 last:border-0 hover:bg-background-elevated"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={paths.session(s.id)}
                        className="hover:underline"
                      >
                        {s.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {s.ended_at ? new Date(s.ended_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {s.target_count ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {toMinutes(s.late_time)} min
                    </td>
                    <td
                      className="px-4 py-3 text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <select
                        value={s.status}
                        disabled={changingId === s.id}
                        onChange={(e) => onChangeState(s, e.target.value)}
                        className={`cursor-pointer rounded-sm border border-white/10 bg-background-elevated px-2 py-1 text-sm capitalize focus:outline-none disabled:opacity-60 ${statusStyle[s.status]}`}
                      >
                        <option value="active">Active</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </td>
                    <td
                      className="px-4 py-3"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-4">
                        <Link
                          to={paths.sessionEdit(s.id)}
                          className="text-xs text-foreground-muted hover:text-foreground"
                        >
                          Edit
                        </Link>
                        <button
                          onClick={() => setSessionToDelete(s)}
                          className="cursor-pointer text-xs text-danger hover:underline"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ConfirmModal
        open={!!sessionToDelete}
        title="Delete session"
        message={`Delete "${sessionToDelete?.name}"? Its attendance records will be deleted too.`}
        confirmText="Delete"
        loading={deleting}
        onConfirm={onConfirmDelete}
        onCancel={() => setSessionToDelete(null)}
      />
    </div>
  );
}
