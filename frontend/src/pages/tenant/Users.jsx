import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";
import { getTenantPaths } from "../../config/tenantDashboardNavigation";

const fieldClass =
  "rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const fullName = (u) =>
  `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim() || u.username || "—";

export default function Users() {
  const { tenant } = useAuth();
  const paths = getTenantPaths(tenant.slug);

  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");
  const [face, setFace] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  updateTitle("Users");
  useUpdatePageTitle("Users");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get("/tenant/users/");
        setUsers(res.data.users ?? res.data.results ?? res.data);
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load users."));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users.filter((u) => {
      const enrolled = Boolean(u.has_face ?? u.face_enrolled);
      if (face === "enrolled" && !enrolled) return false;
      if (face === "missing" && enrolled) return false;
      if (!q) return true;
      return (
        fullName(u).toLowerCase().includes(q) ||
        (u.email ?? "").toLowerCase().includes(q) ||
        (u.section ?? "").toLowerCase().includes(q)
      );
    });
  }, [users, search, face]);

  const onConfirmDelete = async () => {
    setDeleting(true);
    try {
      await api.delete(`/tenant/users/${toDelete.id}/`);
      setUsers((list) => list.filter((u) => u.id !== toDelete.id));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to delete the user."));
    } finally {
      setDeleting(false);
      setToDelete(null);
    }
  };

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  return (
    <div className="space-y-6 p-6">
      <div className="grid gap-3 sm:grid-cols-[1fr_200px]">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, email or section"
          className={fieldClass}
        />
        <select
          value={face}
          onChange={(e) => setFace(e.target.value)}
          className={fieldClass}
        >
          <option value="">All face statuses</option>
          <option value="enrolled">Face enrolled</option>
          <option value="missing">No face yet</option>
        </select>
      </div>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">All users</span>
            <span className="text-xs text-foreground-subtle">
              {visible.length} {visible.length === 1 ? "user" : "users"}
            </span>
          </div>
          <Link
            to={paths.usersNew}
            className="rounded-sm bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover"
          >
            Add user
          </Link>
        </div>

        {visible.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No users found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Section
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">Face</th>
                  <th className="px-4 py-2.5 text-right font-medium">Status</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((u) => {
                  const enrolled = Boolean(u.has_face ?? u.face_enrolled);
                  return (
                    <tr
                      key={u.id}
                      className="border-b border-white/5 last:border-0 hover:bg-background-elevated"
                    >
                      <td className="px-4 py-3">
                        <Link to={paths.user(u.id)} className="hover:underline">
                          {fullName(u)}
                        </Link>
                        <div className="text-xs text-foreground-subtle">
                          {u.email}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right text-foreground-muted">
                        {u.section || "—"}
                      </td>
                      <td
                        className={`px-4 py-3 text-right ${
                          enrolled ? "text-success" : "text-warning"
                        }`}
                      >
                        {enrolled ? "Enrolled" : "Not enrolled"}
                      </td>
                      <td
                        className={`px-4 py-3 text-right ${
                          u.is_active ? "text-success" : "text-danger"
                        }`}
                      >
                        {u.is_active ? "Active" : "Disabled"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-4">
                          <Link
                            to={paths.userEdit(u.id)}
                            className="text-xs text-foreground-muted hover:text-foreground"
                          >
                            Edit
                          </Link>
                          <button
                            onClick={() => setToDelete(u)}
                            className="cursor-pointer text-xs text-danger hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ConfirmModal
        open={!!toDelete}
        title="Delete user"
        message={`Delete ${toDelete ? fullName(toDelete) : ""}? Their attendance records will be removed too.`}
        confirmText="Delete"
        loading={deleting}
        onConfirm={onConfirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
