import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import SessionTargetPicker from "../../components/SessionTargetPicker";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";
import { getTenantPaths } from "../../config/tenantDashboardNavigation";

const fieldClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";
const labelClass = "mb-1.5 block text-sm text-foreground-muted";

const pad = (n) => String(n).padStart(2, "0");

const toLocalInput = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const toMinutes = (duration) => {
  const m = String(duration ?? "").match(/^(?:(\d+) )?(\d+):(\d+):(\d+)/);
  if (!m) return 10;
  return Number(m[1] ?? 0) * 1440 + Number(m[2]) * 60 + Number(m[3]);
};

export default function SessionEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { tenant } = useAuth();
  const paths = getTenantPaths(tenant.slug);

  const [form, setForm] = useState(null);
  const [members, setMembers] = useState([]);
  const [selected, setSelected] = useState(() => new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  updateTitle("Edit session");
  useUpdatePageTitle("Edit session");

  useEffect(() => {
    const load = async () => {
      try {
        const [sRes, uRes] = await Promise.all([
          api.get(`/attendance/sessions/${id}/`),
          api.get("/tenant/users/"),
        ]);
        const s = sRes.data.session ?? sRes.data;
        const list = uRes.data.users ?? uRes.data.results ?? uRes.data;
        

        setForm({
          name: s.name,
          started_at: toLocalInput(s.started_at),
          ended_at: toLocalInput(s.ended_at),
          late_minutes: toMinutes(s.late_time),
        });
        setSelected(new Set(s.target_ids ?? []));
        setMembers(
          list.filter((u) => !u.is_tenant_admin && u.is_active !== false),
        );
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load the session."));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const onChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
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
    if (selected.size === 0) {
      return setError("Select at least one person for this session.");
    }

    const minutes = Math.max(0, Number(form.late_minutes) || 0);
    const payload = {
      name: form.name.trim(),
      started_at: new Date(form.started_at).toISOString(),
      ended_at: form.ended_at ? new Date(form.ended_at).toISOString() : null,
      late_time: `${Math.floor(minutes / 60)}:${pad(minutes % 60)}:00`,
      target_ids: [...selected],
    };

    setSaving(true);
    try {
      await api.patch(`/tenant/sessions/${id}/`, payload);
      navigate(paths.sessions, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, "Failed to save the session."));
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <Link
        to={paths.sessions}
        className="inline-block text-sm text-foreground-muted hover:text-foreground"
      >
        ← Back to sessions
      </Link>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {loading ? (
        <p className="text-sm text-foreground-muted">Loading…</p>
      ) : !form ? null : (
        <form onSubmit={onSubmit} noValidate className="space-y-6">
          <section className="border border-white/10 bg-background-surface">
            <div className="flex h-12 items-center border-b border-white/10 px-4 text-sm font-medium">
              Details
            </div>
            <div className="space-y-4 p-6">
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

              <div className="grid gap-4 sm:grid-cols-3">
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
                    Ends (optional)
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
                <div>
                  <label htmlFor="late_minutes" className={labelClass}>
                    Late window (min)
                  </label>
                  <input
                    id="late_minutes"
                    type="number"
                    min="0"
                    name="late_minutes"
                    value={form.late_minutes}
                    onChange={onChange}
                    className={fieldClass}
                  />
                </div>
              </div>
            </div>
          </section>

          <SessionTargetPicker
            members={members}
            loading={false}
            selected={selected}
            setSelected={setSelected}
            usersNewPath={paths.usersNew}
          />

          <div className="flex items-center justify-end gap-3">
            <Link
              to={paths.sessions}
              className="rounded-sm px-4 py-2 text-sm text-foreground-muted hover:text-foreground"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="cursor-pointer rounded-sm bg-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
