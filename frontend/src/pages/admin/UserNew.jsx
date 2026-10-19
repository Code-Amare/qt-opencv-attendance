import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Alert from "../../components/Alert";
import PasswordInput from "../../components/PasswordInput";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const fieldClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const labelClass = "mb-1.5 block text-sm text-foreground-muted";

export default function UserNew() {
  const navigate = useNavigate();
  const { updatePageTitle } = usePageTitle();
  const fileInputRef = useRef(null);

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    section: "",
    phone_number: "",
    date_of_birth: "",
    is_active: true,
  });
  const [profilePicture, setProfilePicture] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    updatePageTitle("Add user");
  }, []);

  // preview of the selected image
  useEffect(() => {
    if (!profilePicture) return setPreview(null);
    const url = URL.createObjectURL(profilePicture);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [profilePicture]);

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
    if (error) setError("");
  };

  const onFileChange = (e) => {
    setProfilePicture(e.target.files[0] ?? null);
    if (error) setError("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.email.trim() || !form.password) {
      return setError("Email and password are required.");
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("first_name", form.first_name);
      formData.append("last_name", form.last_name);
      formData.append("email", form.email);
      formData.append("password", form.password);
      formData.append("section", form.section);
      formData.append("phone_number", form.phone_number);
      // an empty date can't be sent as "" in multipart, so omit it
      if (form.date_of_birth) {
        formData.append("date_of_birth", form.date_of_birth);
      }
      formData.append("is_active", form.is_active ? "True" : "False");
      if (profilePicture) {
        formData.append("profile_picture", profilePicture);
      }

      const res = await api.post("/admin/users/", formData);
      navigate(`/admin/users/${res.data.user.id}`);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to create the user."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link
          to="/admin/users"
          className="text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to users
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">Add user</h1>
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

        {/* Profile picture: the circle is the only clickable thing */}
        <div className="flex justify-center">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            aria-label="Choose profile picture"
            className="group relative h-24 w-24 cursor-pointer overflow-hidden rounded-full border border-white/10 bg-background-elevated"
          >
            {preview ? (
              <img
                src={preview}
                alt="Profile preview"
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="flex h-full w-full items-center justify-center text-xs text-foreground-subtle">
                No photo
              </span>
            )}
            <span className="absolute inset-0 flex items-center justify-center bg-black/50 text-xs text-white opacity-0 transition group-hover:opacity-100">
              {preview ? "Change" : "Upload"}
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
            autoComplete="off"
            value={form.email}
            onChange={onChange}
            className={fieldClass}
          />
        </div>

        <div>
          <label htmlFor="password" className={labelClass}>
            Password
          </label>
          <PasswordInput
            id="password"
            name="password"
            autoComplete="new-password"
            value={form.password}
            onChange={onChange}
            invalid={!!error}
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

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="cursor-pointer rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Creating…" : "Create user"}
          </button>
          <Link
            to="/admin/users"
            className="rounded-sm border border-white/10 px-5 py-2.5 text-sm hover:bg-background-elevated"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
