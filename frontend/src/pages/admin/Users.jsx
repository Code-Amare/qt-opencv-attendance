import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const inputClass =
  "rounded-sm border border-white/10 bg-background-elevated px-3 py-2 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

export default function Users() {
  const { updatePageTitle } = usePageTitle();
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");
  const [section, setSection] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [userToDelete, setUserToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    updatePageTitle("Users");
  }, []);

  // reload when the filters change (debounced so we don't fire on every keystroke)
  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/admin/users/", {
          params: { search, section },
        });
        setUsers(res.data.users);
      } catch (err) {
        // the backend returns 404 when no user matches
        if (err.response?.status === 404) {
          setUsers([]);
        } else {
          setError(getErrorMessage(err, "Failed to load users."));
        }
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [search, section]);

  const onConfirmDelete = async () => {
    setDeleting(true);
    setError("");
    try {
      await api.delete(`/admin/users/${userToDelete.id}/`);
      setUsers((prev) => prev.filter((u) => u.id !== userToDelete.id));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to delete the user."));
    } finally {
      setDeleting(false);
      setUserToDelete(null);
    }
  };

  const deleteName = userToDelete
    ? `${userToDelete.first_name} ${userToDelete.last_name}`.trim() ||
      userToDelete.email
    : "";

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link
          to="/admin"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Dashboard
        </Link>
        <div className="mt-2 flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
          <Link
            to="/admin/users/new"
            className="rounded-sm bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Add user
          </Link>
        </div>
      </div>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search name or email"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={`${inputClass} w-full sm:w-72`}
        />
        <input
          type="text"
          placeholder="Section"
          value={section}
          onChange={(e) => setSection(e.target.value)}
          className={`${inputClass} w-full sm:w-40`}
        />
      </div>

      {/* Table */}
      <section className="border border-white/10 bg-background-surface">
        {loading ? (
          <p className="p-4 text-sm text-foreground-muted">Loading…</p>
        ) : users.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No users found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Email</th>
                  <th className="px-4 py-2.5 font-medium">Section</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr
                    key={u.id}
                    className="border-b border-white/5 last:border-0 hover:bg-background-elevated"
                  >
                    <td className="px-4 py-3">
                      {`${u.first_name} ${u.last_name}`.trim() || "—"}
                    </td>
                    <td className="px-4 py-3 text-foreground-muted">
                      {u.email}
                    </td>
                    <td className="px-4 py-3 text-foreground-muted">
                      {u.section || "—"}
                    </td>
                    <td
                      className={`px-4 py-3 ${
                        u.is_active ? "text-success" : "text-foreground-subtle"
                      }`}
                    >
                      {u.is_active ? "Active" : "Inactive"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-4">
                        <Link
                          to={`/admin/users/${u.id}`}
                          className="text-foreground-muted hover:text-foreground"
                        >
                          Edit
                        </Link>
                        <button
                          onClick={() => setUserToDelete(u)}
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

      <ConfirmModal
        open={!!userToDelete}
        title="Delete user"
        message={`Delete ${deleteName}? This cannot be undone.`}
        confirmText="Delete"
        loading={deleting}
        onConfirm={onConfirmDelete}
        onCancel={() => setUserToDelete(null)}
      />
    </div>
  );
}
