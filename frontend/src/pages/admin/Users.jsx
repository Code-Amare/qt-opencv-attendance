import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "../../components/Alert";
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
  const [deletingId, setDeletingId] = useState(null);

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

  const onDelete = async (user) => {
    const name = `${user.first_name} ${user.last_name}`.trim() || user.email;
    if (!window.confirm(`Delete ${name}? This cannot be undone.`)) return;

    setDeletingId(user.id);
    setError("");
    try {
      await api.delete(`/admin/users/${user.id}/`);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to delete the user."));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <Link
          to="/admin/users/new"
          className="rounded-sm bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
        >
          Add user
        </Link>
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
                          onClick={() => onDelete(u)}
                          disabled={deletingId === u.id}
                          className="cursor-pointer text-danger hover:underline disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {deletingId === u.id ? "Deleting…" : "Delete"}
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
    </div>
  );
}
