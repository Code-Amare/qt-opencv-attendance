import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";

const statusStyle = {
  present: "text-success",
  late: "text-warning",
  absent: "text-danger",
};

export default function UserDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [info, setInfo] = useState({
    has_face: false,
    embeddings_updated_at: null,
  });
  const [attendances, setAttendances] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useUpdatePageTitle("User detail");
  const title = user?.username ? `User: ${user.username}` : null;
  updateTitle(title);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/admin/users/${id}/`);
        setUser(res.data.user);
        setInfo({
          has_face: res.data.has_face,
          embeddings_updated_at: res.data.embeddings_updated_at,
        });
        setAttendances(res.data.attendances ?? []);
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load the user."));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const onConfirmDelete = async () => {
    setDeleting(true);
    try {
      await api.delete(`/admin/users/${id}/`);
      navigate("/admin/users");
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
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error || "User not found."}
        </Alert>
        <Link
          to="/admin/users"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to users
        </Link>
      </div>
    );
  }

  const fullName = `${user.first_name} ${user.last_name}`.trim() || user.email;

  const details = [
    ["Email", user.email],
    ["Username", user.username],
    ["Section", user.section],
    ["Phone number", user.phone_number],
    [
      "Date of birth",
      user.date_of_birth && new Date(user.date_of_birth).toLocaleDateString(),
    ],
    ["Email verified", user.email_verified ? "Yes" : "No"],
  ];

  return (
    <div className="space-y-8 p-6">
      <div>
        <Link
          to="/admin/users"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Go back
        </Link>
        <div className="mt-2 flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">
            User details
          </h1>
          <div className="flex gap-3">
            <Link
              to={`/admin/users/${id}/edit`}
              className="rounded-sm bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
            >
              Edit
            </Link>
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="cursor-pointer rounded-sm border border-white/10 px-4 py-2 text-sm text-danger hover:bg-background-elevated"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        <section className="border border-white/10 bg-background-surface p-6 lg:col-span-2">
          <div className="flex items-center gap-4">
            {user.profile_picture ? (
              <img
                src={user.profile_picture}
                alt={fullName}
                className="h-24 w-24 shrink-0 rounded-full border border-white/10 object-cover"
              />
            ) : (
              <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-full border border-white/10 bg-background-elevated text-xs text-foreground-subtle">
                No photo
              </div>
            )}
            <div>
              <div className="text-xl font-semibold">{fullName}</div>
              <div
                className={`text-sm ${
                  user.is_active ? "text-success" : "text-foreground-subtle"
                }`}
              >
                {user.is_active ? "Active" : "Inactive"}
              </div>
            </div>
          </div>

          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            {details.map(([label, value]) => (
              <div key={label}>
                <dt className="text-sm text-foreground-muted">{label}</dt>
                <dd className="mt-0.5 text-sm">{value || "—"}</dd>
              </div>
            ))}
          </dl>
        </section>

        <div className="space-y-8">
          <section className="border border-white/10 bg-background-surface">
            <div className="border-b border-white/10 px-4 py-3 text-sm font-medium">
              Face enrollment
            </div>
            <div className="space-y-1 p-4 text-sm">
              <div className={info.has_face ? "text-success" : "text-warning"}>
                {info.has_face ? "Enrolled" : "Not enrolled"}
              </div>
              {info.embeddings_updated_at && (
                <div className="text-foreground-muted">
                  Updated{" "}
                  {new Date(info.embeddings_updated_at).toLocaleString()}
                </div>
              )}
            </div>
          </section>

          <section className="border border-white/10 bg-background-surface">
            <div className="border-b border-white/10 px-4 py-3 text-sm font-medium">
              Attendance history
            </div>
            {attendances.length === 0 ? (
              <p className="p-4 text-sm text-foreground-muted">
                No records yet.
              </p>
            ) : (
              <ul className="max-h-72 divide-y divide-white/5 overflow-y-auto text-sm">
                {attendances.map((a) => (
                  <li key={a.id} className="flex justify-between px-4 py-3">
                    <span className="tabular-nums text-foreground-muted">
                      {new Date(a.recorded_at).toLocaleString()}
                    </span>
                    <span className={`capitalize ${statusStyle[a.status]}`}>
                      {a.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>

      <ConfirmModal
        open={confirmDelete}
        title="Delete user"
        message={`Delete ${fullName}? This cannot be undone.`}
        confirmText="Delete"
        loading={deleting}
        onConfirm={onConfirmDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}
