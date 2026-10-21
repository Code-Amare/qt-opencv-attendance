import { useState, useEffect } from "react";
import { Link, Navigate } from "react-router-dom";
import GoogleAuthButton from "../../components/GoogleAuthButton";
import PasswordInput from "../../components/PasswordInput";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { usePageTitle } from "../../context/PageTitleContext";

const baseField =
  "w-full rounded-sm border bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:outline-none";

const Register = () => {
  const { user } = useAuth();
  const { updatePageTitle } = usePageTitle();

  const [form, setForm] = useState({
    organization_name: "",
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    password: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    updatePageTitle("Create account");
  }, []);

  if (user.isAuthenticated) {
    if (user.isStaff) {
      return <Navigate to="/admin/dashboard" replace />;
    }

    if (user.tenant && user.isTenantAdmin) {
      return <Navigate to={`/${user.tenant.slug}/admin/dashboard`} replace />;
    }

    if (user.tenant) {
      return <Navigate to={`/${user.tenant.slug}/dashboard`} replace />;
    }

    return <Navigate to="/dashboard" replace />;
  }

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
    if (error) setError("");
    if (fieldErrors[name]) setFieldErrors({ ...fieldErrors, [name]: null });
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setFieldErrors({});

    if (
      !form.organization_name.trim() ||
      !form.username.trim() ||
      !form.email.trim() ||
      !form.password
    ) {
      return setError(
        "Organization name, username, email and password are required.",
      );
    }

    setLoading(true);
    try {
      const res = await api.post("/users/register/", form, {
        skipAuthRefresh: true,
      });
      setSuccess(
        res.data.detail ||
          "Account created. Check your email to confirm your address and sign in.",
      );
    } catch (err) {
      const errors = err.response?.data?.errors;
      if (errors) setFieldErrors(errors);
      setError(
        getErrorMessage(err, "Unable to create your account. Please try again."),
      );
    } finally {
      setLoading(false);
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

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-white/5 px-6 py-4">
        <Link to="/" className="text-base font-semibold tracking-tight">
          FaceCall
        </Link>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg">
          <h1 className="text-2xl font-semibold tracking-tight">
            Create your workspace
          </h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Register your organization on FaceCall.
          </p>

          {success ? (
            <div className="mt-8 space-y-4">
              <Alert variant="info" title="Check your email">
                {success}
              </Alert>
              <Link
                to="/login"
                className="block w-full rounded-sm bg-primary py-2.5 text-center text-sm font-medium text-white transition hover:bg-primary-hover"
              >
                Go to sign in
              </Link>
            </div>
          ) : (
            <>
              <form onSubmit={onSubmit} noValidate className="mt-8 space-y-4">
                {error && (
                  <Alert
                    variant="error"
                    title="Registration failed"
                    onClose={() => setError("")}
                  >
                    {error}
                  </Alert>
                )}

                {renderField("organization_name", "Organization name", {
                  autoComplete: "organization",
                })}

                <div className="grid gap-4 sm:grid-cols-2">
                  {renderField("first_name", "First name", {
                    autoComplete: "given-name",
                  })}
                  {renderField("last_name", "Last name", {
                    autoComplete: "family-name",
                  })}
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  {renderField("username", "Username", {
                    autoComplete: "username",
                  })}
                  {renderField("email", "Email", {
                    type: "email",
                    autoComplete: "email",
                  })}
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="mb-1.5 block text-sm text-foreground-muted"
                  >
                    Password
                  </label>
                  <PasswordInput
                    id="password"
                    name="password"
                    autoComplete="new-password"
                    aria-invalid={!!fieldErrors.password}
                    value={form.password}
                    onChange={onChange}
                    invalid={!!fieldErrors.password}
                  />
                  {fieldErrors.password && (
                    <ul className="mt-1 space-y-0.5 text-xs text-danger">
                      {[].concat(fieldErrors.password).map((msg) => (
                        <li key={msg}>{msg}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full cursor-pointer rounded-sm bg-primary py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "Creating account…" : "Create account"}
                </button>
              </form>

              <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-wider text-foreground-subtle">
                <span className="h-px flex-1 bg-white/10" />
                or
                <span className="h-px flex-1 bg-white/10" />
              </div>

              <GoogleAuthButton />

              <p className="mt-8 text-sm text-foreground-muted">
                Already have an account?{" "}
                <Link
                  to="/login"
                  className="text-foreground underline underline-offset-4 hover:text-primary-hover"
                >
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </main>

      <footer className="border-t border-white/5 px-6 py-4 text-xs text-foreground-subtle">
        <Link to="/privacy" className="hover:text-foreground-muted">
          Privacy
        </Link>
        <span className="mx-2">·</span>
        <Link to="/terms" className="hover:text-foreground-muted">
          Terms
        </Link>
        <span className="mx-2">·</span>
        <Link to="/help" className="hover:text-foreground-muted">
          Help
        </Link>
      </footer>
    </div>
  );
};

export default Register;