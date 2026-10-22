import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";

const PLATFORMS = ["windows", "macos", "linux"];
const ARCHS = ["x64", "arm64"];

const inputClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const emptyAsset = {
  platform: "windows",
  architecture: "x64",
  download_url: "",
  file_size: "",
  checksum_sha256: "",
};

const formatSize = (bytes) =>
  bytes == null
    ? "—"
    : bytes >= 1024 ** 3
      ? `${(bytes / 1024 ** 3).toFixed(2)} GB`
      : `${(bytes / 1024 ** 2).toFixed(1)} MB`;

export default function ReleaseEdit() {
  const { id } = useParams();
  const isNew = !id;
  const navigate = useNavigate();

  const [form, setForm] = useState({ version: "", release_notes: "" });
  const [assets, setAssets] = useState([]);
  const [assetForm, setAssetForm] = useState(emptyAsset);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [addingAsset, setAddingAsset] = useState(false);
  const [assetToDelete, setAssetToDelete] = useState(null);
  const [deletingAsset, setDeletingAsset] = useState(false);
  const [error, setError] = useState("");

  const title = isNew
    ? "New release"
    : form.version
      ? `Release v${form.version}`
      : null;
  updateTitle(title);
  useUpdatePageTitle(title);

  useEffect(() => {
    if (isNew) return;
    const load = async () => {
      try {
        const res = await api.get(`/admin/releases/${id}/`);
        setForm({
          version: res.data.version ?? "",
          release_notes: res.data.release_notes ?? "",
        });
        setAssets(res.data.assets ?? []);
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load the release."));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id, isNew]);

  const onChange = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  const onAssetChange = (e) =>
    setAssetForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (isNew) {
        const res = await api.post("/admin/releases/", form);
        navigate(`/admin/releases/${res.data.id}`, { replace: true });
      } else {
        await api.patch(`/admin/releases/${id}/`, form);
        navigate("/admin/releases");
      }
    } catch (err) {
      setError(getErrorMessage(err, "Failed to save the release."));
    } finally {
      setSaving(false);
    }
  };

  const onAddAsset = async (e) => {
    e.preventDefault();
    setAddingAsset(true);
    setError("");
    try {
      const res = await api.post("/admin/release-assets/", {
        ...assetForm,
        file_size: assetForm.file_size ? Number(assetForm.file_size) : null,
        release: Number(id),
      });
      setAssets((list) => [...list, res.data]);
      setAssetForm(emptyAsset);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to add the download."));
    } finally {
      setAddingAsset(false);
    }
  };

  const onConfirmDeleteAsset = async () => {
    setDeletingAsset(true);
    try {
      await api.delete(`/admin/release-assets/${assetToDelete.id}/`);
      setAssets((list) => list.filter((a) => a.id !== assetToDelete.id));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to delete the download."));
    } finally {
      setDeletingAsset(false);
      setAssetToDelete(null);
    }
  };

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <form
        onSubmit={onSubmit}
        className="border border-white/10 bg-background-surface"
      >
        <div className="flex h-12 items-center border-b border-white/10 px-4 text-sm font-medium">
          Details
        </div>
        <div className="space-y-4 p-6">
          <label className="block text-sm">
            <span className="mb-1.5 block text-foreground-muted">Version</span>
            <input
              name="version"
              value={form.version}
              onChange={onChange}
              placeholder="1.0.0"
              maxLength={20}
              required
              className={inputClass}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1.5 block text-foreground-muted">
              Release notes
            </span>
            <textarea
              name="release_notes"
              value={form.release_notes}
              onChange={onChange}
              rows={6}
              className={inputClass}
            />
          </label>
        </div>
        <div className="flex items-center justify-end gap-3 border-t border-white/10 px-4 py-3">
          <Link
            to="/admin/releases"
            className="rounded-sm px-4 py-2 text-sm text-foreground-muted hover:text-foreground"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="cursor-pointer rounded-sm bg-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Saving…" : isNew ? "Create release" : "Save changes"}
          </button>
        </div>
      </form>

      {isNew ? (
        <p className="text-sm text-foreground-muted">
          Save the release first, then add its downloads.
        </p>
      ) : (
        <section className="border border-white/10 bg-background-surface">
          <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
            <span className="text-sm font-medium">Downloads</span>
            <span className="text-xs text-foreground-subtle">
              {assets.length} {assets.length === 1 ? "download" : "downloads"}
            </span>
          </div>

          {assets.length === 0 ? (
            <p className="p-4 text-sm text-foreground-muted">
              No downloads yet. Add one before publishing.
            </p>
          ) : (
            <ul className="divide-y divide-white/5">
              {assets.map((a) => (
                <li
                  key={a.id}
                  className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
                >
                  <div className="min-w-0">
                    <div className="capitalize">
                      {a.platform} · {a.architecture}
                      <span className="ml-2 text-xs normal-case text-foreground-subtle">
                        {formatSize(a.file_size)}
                      </span>
                    </div>
                    <div className="truncate text-xs text-foreground-subtle">
                      {a.download_url}
                    </div>
                    {a.checksum_sha256 && (
                      <div className="truncate font-mono text-xs text-foreground-subtle">
                        SHA-256: {a.checksum_sha256}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => setAssetToDelete(a)}
                    className="shrink-0 cursor-pointer text-xs text-danger hover:underline"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}

          <form
            onSubmit={onAddAsset}
            className="grid gap-3 border-t border-white/10 p-4 sm:grid-cols-2"
          >
            <select
              name="platform"
              value={assetForm.platform}
              onChange={onAssetChange}
              className={inputClass}
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <select
              name="architecture"
              value={assetForm.architecture}
              onChange={onAssetChange}
              className={inputClass}
            >
              {ARCHS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <input
              name="download_url"
              type="url"
              required
              value={assetForm.download_url}
              onChange={onAssetChange}
              placeholder="Download URL (https://…)"
              className={`${inputClass} sm:col-span-2`}
            />
            <input
              name="file_size"
              type="number"
              min="0"
              value={assetForm.file_size}
              onChange={onAssetChange}
              placeholder="File size in bytes (optional)"
              className={inputClass}
            />
            <input
              name="checksum_sha256"
              maxLength={64}
              value={assetForm.checksum_sha256}
              onChange={onAssetChange}
              placeholder="SHA-256 (optional)"
              className={`${inputClass} font-mono`}
            />
            <button
              type="submit"
              disabled={addingAsset}
              className="cursor-pointer rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60 sm:col-span-2"
            >
              {addingAsset ? "Adding…" : "Add download"}
            </button>
          </form>
        </section>
      )}

      <ConfirmModal
        open={!!assetToDelete}
        title="Delete download"
        message="Remove this download from the release?"
        confirmText="Delete"
        loading={deletingAsset}
        onConfirm={onConfirmDeleteAsset}
        onCancel={() => setAssetToDelete(null)}
      />
    </div>
  );
}
