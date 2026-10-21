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

const Login = () => {
  const { user, login } = useAuth();
  const { updatePageTitle } = usePageTitle();

  const [form, setForm] = useState({ username_or_email: "", password: "" });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    updatePageTitle("Sign in");
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
    setForm({ ...form, [e.target.name]: e.target.value });
    if (error) setError("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setNotice("");

    if (!form.username_or_email.trim() || !form.password) {
      return setError("Enter your username or email and your password.");
    }

    setLoading(true);
    try {
      const res = await api.post("/users/login/", form, {
        skipAuthRefresh: true,
      });
      const data = res.data;

      if (data.twofa_required) {
        if (data.error) return setError(data.error);
        setForm({ ...form, password: "" });
        return setNotice(
          data.detail || "A login link has been sent to your email address.",
        );
      }

      login(data.user);
    } catch (err) {
      setError(getErrorMessage(err, "Unable to sign in. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  const fieldClass = `${baseField} ${
    error
      ? "border-danger/60 focus:border-danger"
      : "border-white/10 focus:border-primary-hover"
  }`;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-white/5 px-6 py-4">
        <Link to="/" className="text-base font-semibold tracking-tight">
          FaceCall
        </Link>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Access your FaceCall workspace.
          </p>

          <form onSubmit={onSubmit} noValidate className="mt-8 space-y-4">
            {error && (
              <Alert
                variant="error"
                title="Sign in failed"
                onClose={() => setError("")}
              >
                {error}
              </Alert>
            )}
            {notice && (
              <Alert
                variant="info"
                title="Check your email"
                onClose={() => setNotice("")}
              >
                {notice}
              </Alert>
            )}

            <div>
              <label
                htmlFor="username_or_email"
                className="mb-1.5 block text-sm text-foreground-muted"
              >
                Username or email
              </label>
              <input
                id="username_or_email"
                type="text"
                name="username_or_email"
                autoComplete="username"
                aria-invalid={!!error}
                value={form.username_or_email}
                onChange={onChange}
                className={fieldClass}
              />
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <label htmlFor="password" className="text-foreground-muted">
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-foreground-muted underline-offset-4 hover:text-foreground hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <PasswordInput
                id="password"
                name="password"
                autoComplete="current-password"
                aria-invalid={!!error}
                value={form.password}
                onChange={onChange}
                invalid={!!error}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full cursor-pointer rounded-sm bg-primary py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Signing in…" : "Login"}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-wider text-foreground-subtle">
            <span className="h-px flex-1 bg-white/10" />
            or
            <span className="h-px flex-1 bg-white/10" />
          </div>

          <GoogleAuthButton />

          <p className="mt-8 text-sm text-foreground-muted">
            Accounts are created by your administrator. Need access?{" "}
            <Link
              to="/contact"
              className="text-foreground underline underline-offset-4 hover:text-primary-hover"
            >
              Contact support
            </Link>
          </p>
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

export default Login;
