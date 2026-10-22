import { useEffect, useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";

const fieldClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const labelClass = "mb-1.5 block text-sm text-foreground-muted";

// Adjust the values to match your model's gender choices
const GENDERS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
];

const toForm = (user) => ({
  first_name: user.firstName ?? "",
  last_name: user.lastName ?? "",
  phone_number: user.phoneNumber ?? "",
  date_of_birth: user.dateOfBirth ?? "",
  gender: user.gender ?? "",
});

export default function ProfileEdit() {
  const { user, loading, login } = useAuth();
  const fileInputRef = useRef(null);

  const [form, setForm] = useState(() => toForm(user));
  const [profilePicture, setProfilePicture] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useUpdatePageTitle("Edit Profile");

  // The user may finish loading after this page mounts
  useEffect(() => {
    if (user.isAuthenticated) setForm(toForm(user));
  }, [user.id]);

  // Preview of a newly selected image
  useEffect(() => {
    if (!profilePicture) return setPreview(null);
    const url = URL.createObjectURL(profilePicture);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [profilePicture]);

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  // Only administrators may edit
  if (!user.isAuthenticated) return <Navigate to="/login" replace />;
  if (!user.isStaff) return <Navigate to="/admin/profile" replace />;

  const clearMessages = () => {
    if (error) setError("");
    if (notice) setNotice("");
  };

  const onChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    clearMessages();
  };

  const onFileChange = (e) => {
    const file = e.target.files[0] ?? null;
    if (file && !file.type.startsWith("image/")) {
      e.target.value = "";
      return setError("Please choose an image file.");
    }
    setProfilePicture(file);
    clearMessages();
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setNotice("");

    if (!form.first_name.trim() || !form.last_name.trim()) {
      return setError("First name and last name are required.");
    }

    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("first_name", form.first_name.trim());
      formData.append("last_name", form.last_name.trim());
      formData.append("phone_number", form.phone_number.trim());
      formData.append("date_of_birth", form.date_of_birth || "");
      formData.append("gender", form.gender);

      // Only send the file when a new one was picked,
      // otherwise the existing image is preserved.
      if (profilePicture) {
        formData.append("profile_picture", profilePicture);
      }

      const res = await api.patch(`/users/${user.id}/`, formData);

      // Refresh the shared auth state (sidebar, user menu, profile page)
      login(res.data.user);

      setProfilePicture(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setNotice("Profile updated.");
    } catch (err) {
      setError(getErrorMessage(err, "Failed to update the profile."));
    } finally {
      setSaving(false);
    }
  };

  const fullName = user.fullName?.trim() || user.email;
  const shownPicture = preview || user.profilePicture;

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link
          to="/admin/profile"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to profile
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">
          Edit profile
        </h1>
      </div>

      <form
        onSubmit={onSubmit}
        noValidate
        className="mx-auto w-full max-w-2xl space-y-4 border border-white/10 bg-background-surface p-6"
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
        <div className="flex flex-col items-center gap-2">
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
          {profilePicture && (
            <button
              type="button"
              onClick={() => {
                setProfilePicture(null);
                if (fileInputRef.current) fileInputRef.current.value = "";
              }}
              className="cursor-pointer text-xs text-foreground-muted hover:text-foreground"
            >
              Discard new photo
            </button>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="first_name" className={labelClass}>
              First name
            </label>
            <input
              id="first_name"
              name="first_name"
              autoComplete="given-name"
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
              autoComplete="family-name"
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
            value={user.email ?? ""}
            disabled
            className={`${fieldClass} cursor-not-allowed opacity-60`}
          />
          <p className="mt-1 text-xs text-foreground-subtle">
            Email can't be changed here.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="phone_number" className={labelClass}>
              Phone number
            </label>
            <input
              id="phone_number"
              name="phone_number"
              type="tel"
              autoComplete="tel"
              value={form.phone_number}
              onChange={onChange}
              className={fieldClass}
            />
          </div>
          <div>
            <label htmlFor="gender" className={labelClass}>
              Gender
            </label>
            <select
              id="gender"
              name="gender"
              value={form.gender}
              onChange={onChange}
              className={fieldClass}
            >
              <option value="">Not specified</option>
              {GENDERS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
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

        <div className="pt-2">
          <button
            type="submit"
            disabled={saving}
            className="cursor-pointer rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
