import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import ConfirmModal from "../../components/ConfirmModal";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const fieldClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const labelClass = "mb-1.5 block text-sm text-foreground-muted";

const statusStyle = {
  present: "text-success",
  late: "text-warning",
  absent: "text-danger",
};

export default function UserEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { updatePageTitle } = usePageTitle();
  const fileInputRef = useRef(null);

  const [form, setForm] = useState(null);
  const [info, setInfo] = useState({
    has_face: false,
    embeddings_updated_at: null,
  });
  const [attendances, setAttendances] = useState([]);
  const [currentPicture, setCurrentPicture] = useState(null);
  const [profilePicture, setProfilePicture] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    updatePageTitle("Edit user");
  }, []);

  // preview of a newly selected image
  useEffect(() => {
    if (!profilePicture) return setPreview(null);
    const url = URL.createObjectURL(profilePicture);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [profilePicture]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/admin/users/${id}/`);
        const u = res.data.user;
        setForm({
          first_name: u.first_name ?? "",
          last_name: u.last_name ?? "",
          email: u.email ?? "",
          section: u.section ?? "",
          phone_number: u.phone_number ?? "",
          date_of_birth: u.date_of_birth ?? "",
          is_active: !!u.is_active,
        });
        setCurrentPicture(u.profile_picture ?? null);
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

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
    if (error) setError("");
    if (notice) setNotice("");
  };

  const onFileChange = (e) => {
    setProfilePicture(e.target.files[0] ?? null);
    if (error) setError("");
    if (notice) setNotice("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setNotice("");

    if (!form.email.trim()) {
      return setError("Email is required.");
    }

    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("first_name", form.first_name);
      formData.append("last_name", form.last_name);
      formData.append("email", form.email);
      formData.append("section", form.section);
      formData.append("phone_number", form.phone_number);
      formData.append("date_of_birth", form.date_of_birth || "");
      // Django's BooleanField.to_python only accepts "True"/"False"/"1"/"0"/"t"/"f"
      // from multipart data — lowercase "true"/"false" would raise a validation error.
      formData.append("is_active", form.is_active ? "True" : "False");

      // Only send the file when the user actually picked a new one.
      // Otherwise omit the field so the existing image is preserved.
      if (profilePicture) {
        formData.append("profile_picture", profilePicture);
      }

      await api.patch(`/admin/users/${id}/`, formData);

      if (profilePicture) {
        // Refresh the picture from the server so it shows the saved image.
        const res = await api.get(`/admin/users/${id}/`);
        setCurrentPicture(res.data.user.profile_picture ?? null);
        setProfilePicture(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }

      setNotice("User updated.");
    } catch (err) {
      setError(getErrorMessage(err, "Failed to update the user."));
    } finally {
      setSaving(false);
    }
  };

  const onConfirmDelete = async () => {
    setDeleting(true);
    setError("");
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

  if (!form) {
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

  const fullName = `${form.first_name} ${form.last_name}`.trim() || form.email;
  const shownPicture = preview || currentPicture;

  return (
    <div className="space-y-8 p-6">
      <div>
        <Link
          to="/admin/users"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to users
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">
          Edit user
        </h1>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Form */}
        <form
          onSubmit={onSubmit}
          noValidate
          className="space-y-4 border border-white/10 bg-background-surface p-6 lg:col-span-2"
        >
          {error && (
            <Alert variant="error" title="Error" onClose={() => setError("")}>
              {error}
            </Alert>
          )}
          {notice && (
            <Alert variant="info" title="Saved" onClose={() => setNotice("")}>
              {notice}
            </Alert>
          )}

          {/* Profile picture: the circle is the only clickable thing */}
          <div className="flex justify-center">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Change profile picture"
              className="group relative h-24 w-24 cursor-pointer overflow-hidden rounded-full border border-white/10 bg-background-elevated"
            >
              {shownPicture ? (
                <img
                  src={shownPicture}
                  alt={fullName}
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="flex h-full w-full items-center justify-center text-xs text-foreground-subtle">
                  No photo
                </span>
              )}
              <span className="absolute inset-0 flex items-center justify-center bg-black/50 text-xs text-white opacity-0 transition group-hover:opacity-100">
                {shownPicture ? "Change" : "Upload"}
              </span>
            </button>
            <input
              ref={fileInputRef}
              id="profile_picture"
              name="profile_picture"
              type="file"
              accept="image/*"
              onChange={onFileChange}
              className="hidden"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="first_name" className={labelClass}>
                First name
              </label>
              <input
                id="first_name"
                name="first_name"
                value={form.first_name}
                onChange={onChange}
                className={fieldClass}
              />
            </div>
            <div>
              <label htmlFor="last_name" className={labelClass}>
                Last name
              </label>
              <input
                id="last_name"
                name="last_name"
                value={form.last_name}
                onChange={onChange}
                className={fieldClass}
              />
            </div>
          </div>

          <div>
            <label htmlFor="email" className={labelClass}>
              Email
            </label>
            <input
              id="email"
              type="email"
              name="email"
              value={form.email}
              onChange={onChange}
              className={fieldClass}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="section" className={labelClass}>
                Section
              </label>
              <input
                id="section"
                name="section"
                value={form.section}
                onChange={onChange}
                className={fieldClass}
              />
            </div>
            <div>
              <label htmlFor="phone_number" className={labelClass}>
                Phone number
              </label>
              <input
                id="phone_number"
                name="phone_number"
                value={form.phone_number}
                onChange={onChange}
                className={fieldClass}
              />
            </div>
          </div>

          <div>
            <label htmlFor="date_of_birth" className={labelClass}>
              Date of birth
            </label>
            <input
              id="date_of_birth"
              type="date"
              name="date_of_birth"
              value={form.date_of_birth}
              onChange={onChange}
              className={`${fieldClass} sm:w-56`}
            />
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              name="is_active"
              checked={form.is_active}
              onChange={onChange}
              className="accent-primary"
            />
            Active
          </label>

          <div className="flex items-center justify-between pt-2">
            <button
              type="submit"
              disabled={saving}
              className="cursor-pointer rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="cursor-pointer text-sm text-danger hover:underline"
            >
              Delete user
            </button>
          </div>
        </form>

        <div className="space-y-8">
          {/* Face status */}
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

          {/* Attendance history */}
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
