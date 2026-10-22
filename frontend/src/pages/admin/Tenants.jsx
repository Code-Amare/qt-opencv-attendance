import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";

const fieldClass =
  "rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

export default function Tenants() {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  updateTitle("Tenants");
  useUpdatePageTitle("Tenants");

  useEffect(() => {
    let cancelled = false;

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.get("/admin/tenants/", {
          params: { search: search.trim(), status },
        });
        if (!cancelled) {
          setTenants(res.data.tenants ?? []);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(getErrorMessage(err, "Failed to load tenants."));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, status]);

  return (
    <div className="space-y-6 p-6">
      <div className="grid gap-3 sm:grid-cols-[1fr_200px]">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or slug"
          className={fieldClass}
        />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className={fieldClass}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
          <span className="text-sm font-medium">All tenants</span>
          <span className="text-xs text-foreground-subtle">
            {tenants.length} {tenants.length === 1 ? "tenant" : "tenants"}
          </span>
        </div>

        {loading ? (
          <p className="p-4 text-sm text-foreground-muted">Loading…</p>
        ) : tenants.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No tenants found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Sessions
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Created
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => navigate(`/admin/tenants/${t.id}`)}
                    className="cursor-pointer border-b border-white/5 last:border-0 hover:bg-background-elevated"
                  >
                    <td className="px-4 py-3">
                      <div>{t.name}</div>
                      <div className="text-xs text-foreground-subtle">
                        {t.slug}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {t.session_count ?? 0}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {new Date(t.created_at).toLocaleDateString()}
                    </td>
                    <td
                      className={`px-4 py-3 text-right ${
                        t.is_active ? "text-success" : "text-danger"
                      }`}
                    >
                      {t.is_active ? "Active" : "Suspended"}
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
