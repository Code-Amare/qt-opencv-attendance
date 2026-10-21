import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const fieldClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const labelClass = "mb-1.5 block text-sm text-foreground-muted";

const statusStyle = {
  active: "text-success",
  completed: "text-info",
  cancelled: "text-danger",
};

const pad = (n) => String(n).padStart(2, "0");

// ISO string -> value for <input type="datetime-local">
const toLocalInput = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

// DRF duration ("00:10:00" or "1 00:10:00") -> minutes
const toMinutes = (duration) => {
  const m = String(duration ?? "").match(/^(?:(\d+) )?(\d+):(\d+):(\d+)/);
  if (!m) return 10;
  return Number(m[1] ?? 0) * 1440 + Number(m[2]) * 60 + Number(m[3]);
};

const emptyForm = { name: "", started_at: "", ended_at: "", late_minutes: 10 };

function SessionForm({ session, onClose, onSaved }) {
  const [form, setForm] = useState(
    session
      ? {
          name: session.name,
          started_at: toLocalInput(session.started_at),
          ended_at: toLocalInput(session.ended_at),
          late_minutes: toMinutes(session.late_time),
        }
      : emptyForm,
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const onChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    if (error) setError("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.name.trim() || !form.started_at) {
      return setError("Name and start time are required.");
    }
    if (form.ended_at && new Date(form.ended_at) <= new Date(form.started_at)) {
      return setError("The end time must be after the start time.");
    }

    const minutes = Math.max(0, Number(form.late_minutes) || 0);
    const payload = {
      name: form.name.trim(),
      started_at: new Date(form.started_at).toISOString(),
      ended_at: form.ended_at ? new Date(form.ended_at).toISOString() : null,
      late_time: `${Math.floor(minutes / 60)}:${pad(minutes % 60)}:00`,
    };

    setSaving(true);
    try {
      if (session) {
        await api.patch(`/admin/sessions/${session.id}/`, payload);
      } else {
        await api.post("/attendance/session/create/", payload);
      }
      onSaved();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to save the session."));
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={() => !saving && onClose()}
    >
      <form
        onSubmit={onSubmit}
        noValidate
        role="dialog"
        aria-modal="true"
        className="w-full max-w-md space-y-4 border border-white/10 bg-background-surface p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold tracking-tight">
          {session ? "Edit session" : "New session"}
        </h2>

        {error && (
          <Alert variant="error" title="Error" onClose={() => setError("")}>
            {error}
          </Alert>
        )}

        <div>
          <label htmlFor="name" className={labelClass}>
            Name
          </label>
          <input
            id="name"
            name="name"
            value={form.name}
            onChange={onChange}
            className={fieldClass}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="started_at" className={labelClass}>
              Starts
            </label>
            <input
              id="started_at"
              type="datetime-local"
              name="started_at"
              value={form.started_at}
              onChange={onChange}
              className={fieldClass}
            />
          </div>
          <div>
            <label htmlFor="ended_at" className={labelClass}>
              Ends
            </label>
            <input
              id="ended_at"
              type="datetime-local"
              name="ended_at"
              value={form.ended_at}
              onChange={onChange}
              className={fieldClass}
            />
          </div>
        </div>

        <div>
          <label htmlFor="late_minutes" className={labelClass}>
            Late window (minutes after the end time)
          </label>
          <input
            id="late_minutes"
            type="number"
            min="0"
            name="late_minutes"
            value={form.late_minutes}
            onChange={onChange}
            className={`${fieldClass} sm:w-40`}
          />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="cursor-pointer rounded-sm border border-white/10 px-4 py-2 text-sm hover:bg-background-elevated disabled:cursor-not-allowed disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="cursor-pointer rounded-sm bg-primary px-5 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Saving…" : session ? "Save changes" : "Create session"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Sessions() {
  const navigate = useNavigate();
  const { updatePageTitle } = usePageTitle();
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null); // null = creating
  const [changingId, setChangingId] = useState(null);
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    updatePageTitle("Sessions");
  }, []);

  const load = async () => {
    setError("");
    try {
      const res = await api.get("/admin/sessions/");
      setSessions(res.data.sessions);
    } catch (err) {
      // the backend returns 404 when there are no sessions yet
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

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const openEdit = (s) => {
    setEditing(s);
    setFormOpen(true);
  };

  const onSaved = () => {
    setFormOpen(false);
    load();
  };

  const onChangeState = async (session, status) => {
    setChangingId(session.id);
    setError("");
    try {
      const res = await api.patch(`/admin/sessions/${session.id}/state/`, {
        status,
      });
      setSessions((prev) =>
        prev.map((s) => (s.id === session.id ? res.data.session : s)),
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
      await api.delete(`/admin/sessions/${sessionToDelete.id}/`);
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
      <div>
        <div className="mt-2 flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">Sessions</h1>
          <button
            onClick={openCreate}
            className="cursor-pointer rounded-sm bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            New session
          </button>
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <section className="border border-white/10 bg-background-surface">
        {loading ? (
          <p className="p-4 text-sm text-foreground-muted">Loading…</p>
        ) : sessions.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No sessions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Starts</th>
                  <th className="px-4 py-2.5 font-medium">Ends</th>
                  <th className="px-4 py-2.5 font-medium">Late window</th>
                  <th className="px-4 py-2.5 font-medium">State</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => navigate(`/admin/sessions/${s.id}`)}
                    className="cursor-pointer border-b border-white/5 last:border-0 hover:bg-background-elevated"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/admin/sessions/${s.id}`}
                        className="hover:underline"
                      >
                        {s.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 tabular-nums text-foreground-muted">
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-foreground-muted">
                      {s.ended_at ? new Date(s.ended_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-foreground-muted">
                      {toMinutes(s.late_time)} min
                    </td>
                    <td
                      className="px-4 py-3"
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
                      <div className="flex justify-end gap-4">
                        <button
                          onClick={() => openEdit(s)}
                          className="cursor-pointer text-foreground-muted hover:text-foreground"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => setSessionToDelete(s)}
                          className="cursor-pointer text-danger hover:underline"
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

      {formOpen && (
        <SessionForm
          session={editing}
          onClose={() => setFormOpen(false)}
          onSaved={onSaved}
        />
      )}

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
