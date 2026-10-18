import { useEffect, useState } from "react";
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
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    updatePageTitle("Add user");
  }, []);

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
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
      const payload = {
        ...form,
        date_of_birth: form.date_of_birth || null, // empty date must be null
      };
      const res = await api.post("/admin/users/", payload);
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
