import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";

export default function Releases() {
  const [releases, setReleases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  updateTitle("Releases");
  useUpdatePageTitle("Releases");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get("/admin/releases/");
        setReleases(res.data.results ?? res.data);
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load releases."));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const togglePublish = async (r) => {
    setBusyId(r.id);
    setError("");
    try {
      const action = r.is_published ? "unpublish" : "publish";
      const res = await api.post(`/admin/releases/${r.id}/${action}/`);
      setReleases((list) => list.map((x) => (x.id === r.id ? res.data : x)));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to update the release."));
    } finally {
      setBusyId(null);
    }
  };

  const onConfirmDelete = async () => {
    setDeleting(true);
    try {
      await api.delete(`/admin/releases/${toDelete.id}/`);
      setReleases((list) => list.filter((x) => x.id !== toDelete.id));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to delete the release."));
    } finally {
      setDeleting(false);
      setToDelete(null);
    }
  };

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

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
            <span className="text-sm font-medium">Desktop releases</span>
            <span className="text-xs text-foreground-subtle">
              {releases.length} {releases.length === 1 ? "release" : "releases"}
            </span>
          </div>
          <Link
            to="/admin/releases/new"
            className="rounded-sm bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover"
          >
            New release
          </Link>
        </div>

        {releases.length === 0 ? (
          <p className="p-4 text-sm text-foreground-muted">No releases yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                  <th className="px-4 py-2.5 font-medium">Version</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Created
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Downloads
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">Status</th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Published
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {releases.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-white/5 last:border-0 hover:bg-background-elevated"
                  >
                    <td className="px-4 py-3 font-medium tabular-nums">
                      <Link
                        to={`/admin/releases/${r.id}`}
                        className="hover:underline"
                      >
                        v{r.version}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {r.assets?.length ?? 0}
                    </td>
                    <td
                      className={`px-4 py-3 text-right ${
                        r.is_published
                          ? "text-success"
                          : "text-foreground-subtle"
                      }`}
                    >
                      {r.is_published ? "Published" : "Draft"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                      {r.published_at
                        ? new Date(r.published_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-4">
                        <button
                          onClick={() => togglePublish(r)}
                          disabled={busyId === r.id}
                          className="cursor-pointer text-xs text-primary hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {r.is_published ? "Unpublish" : "Publish"}
                        </button>
                        <Link
                          to={`/admin/releases/${r.id}`}
                          className="text-xs text-foreground-muted hover:text-foreground"
                        >
                          Edit
                        </Link>
                        <button
                          onClick={() => setToDelete(r)}
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
        open={!!toDelete}
        title="Delete release"
        message={`Delete v${toDelete?.version}? Its downloads will be removed too.`}
        confirmText="Delete"
        loading={deleting}
        onConfirm={onConfirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
