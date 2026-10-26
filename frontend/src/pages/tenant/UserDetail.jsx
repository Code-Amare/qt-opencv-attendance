import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";
import { getTenantPaths } from "../../config/tenantDashboardNavigation";

const formatDate = (value) =>
  value ? new Date(value).toLocaleDateString() : "—";

const formatDateTime = (value) =>
  value
    ? new Date(value).toLocaleString([], {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

const badgeStyle = {
  present: "bg-success/10 text-success",
  late: "bg-warning/10 text-warning",
  absent: "bg-danger/10 text-danger",
};

const RECENT_LIMIT = 5;

export default function UserDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { tenant } = useAuth();
  const paths = getTenantPaths(tenant.slug);

  const [user, setUser] = useState(null);
  const [history, setHistory] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  updateTitle("User");
  useUpdatePageTitle("User");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/tenant/users/${id}/`);
        setUser(res.data.user ?? res.data);
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load the user."));
      } finally {
        setLoading(false);
      }
    };

    const loadHistory = async () => {
      try {
        const res = await api.get(`/attendance/users/${id}/history/`, {
          params: { page: 1, page_size: RECENT_LIMIT },
        });
        setHistory(res.data);
      } catch (err) {
        setHistoryError(
          getErrorMessage(err, "Failed to load attendance history."),
        );
      }
    };

    load();
    loadHistory();
  }, [id]);

  const onConfirmDelete = async () => {
    setDeleting(true);
    try {
      await api.delete(`/tenant/users/${id}/`);
      navigate(paths.users, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, "Failed to delete the user."));
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  if (!user) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="error" title="Error">
          {error || "User not found."}
        </Alert>
        <Link
          to={paths.users}
          className="inline-block text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to users
        </Link>
      </div>
    );
  }

  const name =
    `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim() ||
    user.username ||
    "—";
  const enrolled = Boolean(user.has_face ?? user.face_enrolled);
  const initial = name.charAt(0).toUpperCase();

  const cards = [
    ["Status", user.is_active ? "Active" : "Disabled", user.is_active],
    ["Face", enrolled ? "Enrolled" : "Not enrolled", enrolled],
    [
      "Email",
      user.email_verified ? "Verified" : "Pending",
      Boolean(user.email_verified),
    ],
    ["Joined", formatDate(user.date_joined), null],
  ];

  const details = [
    ["Email", user.email || "—"],
    ["Username", user.username || "—"],
    ["Section", user.section || "—"],
    ["Phone number", user.phone_number || "—"],
    ["Date of birth", formatDate(user.date_of_birth)],
  ];

  const recent = history?.results ?? [];

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      <Link
        to={paths.users}
        className="inline-block text-sm text-foreground-muted hover:text-foreground"
      >
        ← Back to users
      </Link>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full bg-background-elevated">
            {user.profile_picture ? (
              <img
                src={user.profile_picture}
                alt={name}
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="text-xl font-semibold text-foreground-muted">
                {initial}
              </span>
            )}
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{name}</h1>
            <p className="mt-0.5 text-sm text-foreground-subtle">
              {user.email}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to={paths.userEdit(id)}
            className="rounded-sm border border-white/10 px-4 py-2 text-sm text-foreground hover:bg-background-elevated"
          >
            Edit
          </Link>
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="cursor-pointer rounded-sm bg-danger px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
          >
            Delete
          </button>
        </div>
      </div>

      <section className="grid border-l border-t border-white/10 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(([label, value, good]) => (
          <div
            key={label}
            className="border-b border-r border-white/10 bg-background-surface p-6"
          >
            <div
              className={`text-xl font-semibold tabular-nums ${
                good === null ? "" : good ? "text-success" : "text-warning"
              }`}
            >
              {value}
            </div>
            <div className="mt-1 text-sm text-foreground-muted">{label}</div>
          </div>
        ))}
      </section>

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center border-b border-white/10 px-4 text-sm font-medium">
          Details
        </div>
        <dl className="divide-y divide-white/5">
          {details.map(([term, text]) => (
            <div
              key={term}
              className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-3 sm:gap-4"
            >
              <dt className="text-foreground-muted">{term}</dt>
              <dd className="sm:col-span-2">{text}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
          <span className="text-sm font-medium">Recent attendance</span>
          <Link
            to={paths.userAttendance(id)}
            className="text-sm text-foreground-muted hover:text-foreground"
          >
            View all →
          </Link>
        </div>

        {historyError ? (
          <p className="p-4 text-sm text-danger">{historyError}</p>
        ) : !history ? (
          <p className="p-4 text-sm text-foreground-muted">Loading…</p>
        ) : (
          <>
            <div className="grid grid-cols-3 divide-x divide-white/5 border-b border-white/10 text-center">
              {[
                ["Present", history.summary.present, "text-success"],
                ["Late", history.summary.late, "text-warning"],
                ["Absent", history.summary.absent, "text-danger"],
              ].map(([label, value, color]) => (
                <div key={label} className="px-4 py-3">
                  <div
                    className={`text-lg font-semibold tabular-nums ${color}`}
                  >
                    {value}
                  </div>
                  <div className="text-xs text-foreground-muted">{label}</div>
                </div>
              ))}
            </div>

            {recent.length === 0 ? (
              <p className="p-4 text-sm text-foreground-muted">
                No attendance records yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                      <th className="px-4 py-2.5 font-medium">Session</th>
                      <th className="px-4 py-2.5 font-medium">Starts</th>
                      <th className="px-4 py-2.5 font-medium">Status</th>
                      <th className="px-4 py-2.5 font-medium">Recorded at</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((r) => (
                      <tr
                        key={r.id}
                        className="border-b border-white/5 last:border-0 hover:bg-background-elevated"
                      >
                        <td className="px-4 py-3">{r.session_name}</td>
                        <td className="px-4 py-3 text-foreground-muted">
                          {formatDateTime(r.started_at)}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${badgeStyle[r.status]}`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-foreground-muted">
                          {formatDateTime(r.recorded_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      <ConfirmModal
        open={confirmDelete}
        title="Delete user"
        message={`Delete ${name}? Their attendance records will be removed too.`}
        confirmText="Delete"
        loading={deleting}
        onConfirm={onConfirmDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}
