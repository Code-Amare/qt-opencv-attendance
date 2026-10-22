import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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

export default function UserEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user: me, tenant, getUser } = useAuth();
  const paths = getTenantPaths(tenant.slug);
  const fileInput = useRef(null);

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    section: "",
    phone_number: "",
    date_of_birth: "",
  });
  const [email, setEmail] = useState("");
  const [currentPicture, setCurrentPicture] = useState("");
  const [newPicture, setNewPicture] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [removePicture, setRemovePicture] = useState(false);

  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  updateTitle("Edit user");
  useUpdatePageTitle("Edit user");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/tenant/users/${id}/`);
        const u = res.data.user ?? res.data;
        setForm({
          first_name: u.first_name ?? "",
          last_name: u.last_name ?? "",
          section: u.section ?? "",
          phone_number: u.phone_number ?? "",
          date_of_birth: u.date_of_birth ?? "",
        });
        setEmail(u.email ?? "");
        setCurrentPicture(u.profile_picture ?? "");
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load the user."));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [id]);

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
    setNewPicture(file);
    setRemovePicture(false);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const onClearNewPicture = () => {
    setNewPicture(null);
    setPreviewUrl("");
    if (fileInput.current) fileInput.current.value = "";
  };

  const onRemoveCurrent = () => {
    onClearNewPicture();
    setRemovePicture(true);
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setFieldErrors({});

    if (!form.first_name.trim()) {
      return setError("First name is required.");
    }

    const data = new FormData();
    Object.entries(form).forEach(([key, value]) => data.append(key, value));
    if (newPicture) data.append("profile_picture", newPicture);
    if (removePicture) data.append("remove_profile_picture", "true");

    setSaving(true);
    try {
      await api.patch(`/users/${id}/`, data);
      if (me.id === Number(id)) await getUser();
      navigate(paths.user(id), { replace: true });
    } catch (err) {
      const body = err.response?.data;
      if (body?.errors) setFieldErrors(body.errors);
      setError(
        body?.is_no_change
          ? "No changes were made."
          : getErrorMessage(err, "Failed to update the user."),
      );
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

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  if (error && !email) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="error" title="Error">
          {error}
        </Alert>
        <Link
          to={paths.users}
          className="inline-block text-sm text-foreground-muted hover:text-foreground"
        >
          ← Back to users
        </Link>
      </div>
    );
  }

  const shownPicture = previewUrl || (removePicture ? "" : currentPicture);
  const initial = (form.first_name || email || "U").charAt(0).toUpperCase();

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <Link
        to={paths.user(id)}
        className="inline-block text-sm text-foreground-muted hover:text-foreground"
      >
        ← Back to user
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
          Edit user
        </div>

        <div className="space-y-6 p-6">
          <div className="flex items-center gap-5">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-background-elevated">
              {shownPicture ? (
                <img
                  src={shownPicture}
                  alt="Profile"
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
                  {shownPicture ? "Change picture" : "Upload picture"}
                </label>

                {newPicture && (
                  <button
                    type="button"
                    onClick={onClearNewPicture}
                    className="cursor-pointer text-sm text-foreground-muted hover:text-foreground"
                  >
                    Undo
                  </button>
                )}

                {!newPicture && currentPicture && !removePicture && (
                  <button
                    type="button"
                    onClick={onRemoveCurrent}
                    className="cursor-pointer text-sm text-danger hover:underline"
                  >
                    Remove
                  </button>
                )}

                {removePicture && (
                  <button
                    type="button"
                    onClick={() => setRemovePicture(false)}
                    className="cursor-pointer text-sm text-foreground-muted hover:text-foreground"
                  >
                    Undo remove
                  </button>
                )}
              </div>
              <p className="mt-2 text-xs text-foreground-subtle">
                JPEG, PNG or WebP, up to 5 MB.
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

          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm text-foreground-muted"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              disabled
              className={`${baseField} cursor-not-allowed border-white/10 opacity-60`}
            />
            <p className="mt-1 text-xs text-foreground-subtle">
              The email can't be changed.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {renderField("phone_number", "Phone number", {
              type: "tel",
              autoComplete: "off",
            })}
            {renderField("section", "Section", { autoComplete: "off" })}
          </div>

          {renderField("date_of_birth", "Date of birth", { type: "date" })}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-white/10 px-4 py-3">
          <Link
            to={paths.user(id)}
            className="rounded-sm px-4 py-2 text-sm text-foreground-muted hover:text-foreground"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="cursor-pointer rounded-sm bg-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
