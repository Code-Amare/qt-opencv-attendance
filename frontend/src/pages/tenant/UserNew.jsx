import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";
import { getTenantPaths } from "../../config/tenantDashboardNavigation";

const baseField =
  "w-full rounded-sm border bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:outline-none";

const MAX_PICTURE_BYTES = 5 * 1024 * 1024;
const PICTURE_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function UserNew() {
  const navigate = useNavigate();
  const { tenant } = useAuth();
  const paths = getTenantPaths(tenant.slug);
  const fileInput = useRef(null);

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone_number: "",
    section: "",
    date_of_birth: "",
  });
  const [picture, setPicture] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  updateTitle("Add user");
  useUpdatePageTitle("Add user");

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    if (error) setError("");
    if (fieldErrors[name]) setFieldErrors((f) => ({ ...f, [name]: null }));
  };

  const onPickPicture = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!PICTURE_TYPES.includes(file.type)) {
      setFieldErrors((f) => ({
        ...f,
        profile_picture: ["Use a JPEG, PNG or WebP image."],
      }));
      return;
    }
    if (file.size > MAX_PICTURE_BYTES) {
      setFieldErrors((f) => ({
        ...f,
        profile_picture: ["The image must be 5 MB or smaller."],
      }));
      return;
    }

    setFieldErrors((f) => ({ ...f, profile_picture: null }));
    setPicture(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const onClearPicture = () => {
    setPicture(null);
    setPreviewUrl("");
    if (fileInput.current) fileInput.current.value = "";
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setFieldErrors({});

    if (!form.first_name.trim() || !form.email.trim()) {
      return setError("First name and email are required.");
    }

    const data = new FormData();
    Object.entries(form).forEach(([key, value]) => data.append(key, value));
    if (picture) data.append("profile_picture", picture);

    setSaving(true);
    try {
      await api.post("/tenant/users/", data);
      navigate(paths.users, { replace: true });
    } catch (err) {
      const errors = err.response?.data?.errors;
      if (errors) setFieldErrors(errors);
      setError(getErrorMessage(err, "Failed to create the user."));
    } finally {
      setSaving(false);
    }
  };

  const fieldClass = (name) =>
    `${baseField} ${
      fieldErrors[name]
        ? "border-danger/60 focus:border-danger"
        : "border-white/10 focus:border-primary-hover"
    }`;

  const renderField = (name, label, props = {}) => (
    <div>
      <label
        htmlFor={name}
        className="mb-1.5 block text-sm text-foreground-muted"
      >
        {label}
      </label>
      <input
        id={name}
        type="text"
        name={name}
        aria-invalid={!!fieldErrors[name]}
        value={form[name]}
        onChange={onChange}
        className={fieldClass(name)}
        {...props}
      />
      {fieldErrors[name] && (
        <p className="mt-1 text-xs text-danger">
          {[].concat(fieldErrors[name])[0]}
        </p>
      )}
    </div>
  );

  const initial = (form.first_name || form.email || "U")
    .charAt(0)
    .toUpperCase();

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <Link
        to={paths.users}
        className="inline-block text-sm text-foreground-muted hover:text-foreground"
      >
        ← Back to users
      </Link>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <form
        onSubmit={onSubmit}
        noValidate
        className="border border-white/10 bg-background-surface"
      >
        <div className="flex h-12 items-center border-b border-white/10 px-4 text-sm font-medium">
          New user
        </div>

        <div className="space-y-6 p-6">
          <div className="flex items-center gap-5">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-background-elevated">
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt="Profile preview"
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="text-2xl font-semibold text-foreground-muted">
                  {initial}
                </span>
              )}
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-3">
                <input
                  ref={fileInput}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={onPickPicture}
                  className="hidden"
                  id="profile_picture"
                />
                <label
                  htmlFor="profile_picture"
                  className="cursor-pointer rounded-sm border border-white/10 px-4 py-2 text-sm text-foreground hover:bg-background-elevated"
                >
                  {picture ? "Change picture" : "Upload picture"}
                </label>
                {picture && (
                  <button
                    type="button"
                    onClick={onClearPicture}
                    className="cursor-pointer text-sm text-foreground-muted hover:text-foreground"
                  >
                    Remove
                  </button>
                )}
              </div>
              <p className="mt-2 text-xs text-foreground-subtle">
                Optional. JPEG, PNG or WebP, up to 5 MB.
              </p>
              {fieldErrors.profile_picture && (
                <p className="mt-1 text-xs text-danger">
                  {[].concat(fieldErrors.profile_picture)[0]}
                </p>
              )}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {renderField("first_name", "First name", { autoComplete: "off" })}
            {renderField("last_name", "Last name", { autoComplete: "off" })}
          </div>

          {renderField("email", "Email", {
            type: "email",
            autoComplete: "off",
          })}

          <div className="grid gap-4 sm:grid-cols-2">
            {renderField("phone_number", "Phone number (optional)", {
              type: "tel",
              autoComplete: "off",
            })}
            {renderField("section", "Section (optional)", {
              autoComplete: "off",
            })}
          </div>

          {renderField("date_of_birth", "Date of birth (optional)", {
            type: "date",
          })}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-white/10 px-4 py-3">
          <Link
            to={paths.users}
            className="rounded-sm px-4 py-2 text-sm text-foreground-muted hover:text-foreground"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="cursor-pointer rounded-sm bg-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Creating…" : "Create user"}
          </button>
        </div>
      </form>
    </div>
  );
}
