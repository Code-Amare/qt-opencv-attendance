import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";

export default function TenantDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [tenant, setTenant] = useState(null);
  const [admins, setAdmins] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  updateTitle("Tenants");
  useUpdatePageTitle("Tenant");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/admin/tenants/${id}/`);
        setTenant(res.data.tenant);
        setAdmins(res.data.admins ?? []);
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load the tenant."));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [id]);

  const closeDelete = () => {
    if (deleting) return;
    setDeleteOpen(false);
    setConfirmText("");
    setDeleteError("");
  };

  const onDelete = async () => {
    setDeleting(true);
    setDeleteError("");
    try {
      await api.delete(`/admin/tenants/${id}/`, {
        data: { confirm: tenant.slug },
      });
      navigate("/admin/tenants", { replace: true });
    } catch (err) {
      setDeleteError(getErrorMessage(err, "Failed to delete the tenant."));
      setDeleting(false);
    }
  };

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  if (error || !tenant) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="error" title="Error">
          {error || "Tenant not found."}
        </Alert>
        <Link
          to="/admin/tenants"
          className="inline-block text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to tenants
        </Link>
      </div>
    );
  }

  const cards = [
    ["Status", tenant.is_active ? "Active" : "Suspended"],
    ["Sessions", tenant.session_count ?? 0],
    ["Admins", admins.length],
    ["Created", new Date(tenant.created_at).toLocaleDateString()],
  ];

  return (
    <div className="space-y-8 p-6">
      <div>
        <Link
          to="/admin/tenants"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to tenants
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">
          {tenant.name}
        </h1>
        <p className="mt-1 text-sm text-foreground-subtle">{tenant.slug}</p>
      </div>

      <section className="grid border-l border-t border-white/10 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(([label, value]) => (
          <div
            key={label}
            className="border-b border-r border-white/10 bg-background-surface p-6"
          >
            <div
              className={`text-2xl font-semibold tabular-nums ${
                label === "Status"
                  ? tenant.is_active
                    ? "text-success"
                    : "text-danger"
                  : ""
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
          Admins
        </div>
        {admins.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">
            This tenant has no admins.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Email</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Verified
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {admins.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-white/5 last:border-0"
                  >
                    <td className="px-4 py-3">
                      {`${a.first_name} ${a.last_name}`.trim() || "—"}
                    </td>
                    <td className="px-4 py-3 text-foreground-muted">
                      {a.email}
                    </td>
                    <td
                      className={`px-4 py-3 text-right ${
                        a.email_verified ? "text-success" : "text-warning"
                      }`}
                    >
                      {a.email_verified ? "Yes" : "Pending"}
                    </td>
                    <td
                      className={`px-4 py-3 text-right ${
                        a.is_active ? "text-success" : "text-danger"
                      }`}
                    >
                      {a.is_active ? "Active" : "Disabled"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="border border-danger/40 bg-background-surface">
        <div className="flex h-12 items-center border-b border-danger/40 px-4 text-sm font-medium text-danger">
          Danger zone
        </div>
        <div className="flex flex-col items-start justify-between gap-4 p-6 sm:flex-row sm:items-center">
          <div>
            <div className="text-sm font-medium">Delete this tenant</div>
            <p className="mt-1 text-sm text-foreground-muted">
              Permanently removes the tenant, all of its users, sessions and
              attendance records. This can't be undone.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setDeleteOpen(true)}
            className="shrink-0 cursor-pointer rounded-sm bg-danger px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
          >
            Delete tenant
          </button>
        </div>
      </section>

      {deleteOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
          onClick={closeDelete}
        >
          <div
            className="w-full max-w-md border border-white/10 bg-background-surface p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold tracking-tight">
              Delete {tenant.name}?
            </h2>
            <p className="mt-2 text-sm text-foreground-muted">
              This permanently deletes the tenant, its users, sessions and
              attendance records. Type{" "}
              <span className="font-mono text-foreground">{tenant.slug}</span>{" "}
              to confirm.
            </p>

            {deleteError && (
              <div className="mt-4">
                <Alert
                  variant="error"
                  title="Delete failed"
                  onClose={() => setDeleteError("")}
                >
                  {deleteError}
                </Alert>
              </div>
            )}

            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={tenant.slug}
              autoFocus
              className="mt-4 w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm placeholder:text-foreground-subtle focus:border-danger focus:outline-none"
            />

            <div className="mt-6 grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={closeDelete}
                disabled={deleting}
                className="cursor-pointer rounded-sm border border-white/10 px-5 py-2.5 text-sm text-foreground hover:bg-background-elevated disabled:cursor-not-allowed disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onDelete}
                disabled={deleting || confirmText !== tenant.slug}
                className="cursor-pointer rounded-sm bg-danger px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
