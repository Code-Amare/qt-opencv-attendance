import { useState, useEffect } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import GoogleAuthButton from "../../components/GoogleAuthButton";
import api from "../../lib/axios";
import { useAuth } from "../../context/AuthContext";
import { usePageTitle } from "../../context/PageTitleContext";

const inputClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const EyeIcon = ({ off }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="h-4.5 w-4.5"
    aria-hidden="true"
  >
    {off ? (
      <>
        <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
        <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
        <path d="M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
        <line x1="2" y1="2" x2="22" y2="22" />
      </>
    ) : (
      <>
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    )}
  </svg>
);

const Login = () => {
  const navigate = useNavigate();
  const { user, login } = useAuth();
  const { updatePageTitle } = usePageTitle();

  const [form, setForm] = useState({ username_or_email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    updatePageTitle("Sign in");
  }, []);

  if (user.isAuthenticated) return <Navigate to="/dashboard" replace />;

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/users/login/", form, { skipAuthRefresh: true });
      login(res.data.user);
      navigate("/dashboard");
    } catch (err) {
      const data = err.response?.data;
      setError(data?.detail || data?.message || "Invalid username/email or password.");
    } finally {
      setLoading(false);
    }
  };

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

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <div>
              <label htmlFor="username_or_email" className="mb-1.5 block text-sm text-foreground-muted">
                Username or email
              </label>
              <input
                id="username_or_email"
                type="text"
                name="username_or_email"
                autoComplete="username"
                required
                value={form.username_or_email}
                onChange={onChange}
                className={inputClass}
              />
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <label htmlFor="password" className="text-foreground-muted">Password</label>
                <Link to="/forgot-password" className="text-foreground-muted underline-offset-4 hover:text-foreground hover:underline">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  name="password"
                  autoComplete="current-password"
                  required
                  value={form.password}
                  onChange={onChange}
                  className={`${inputClass} pr-10`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 flex cursor-pointer items-center px-3 text-foreground-subtle hover:text-foreground"
                >
                  <EyeIcon off={showPassword} />
                </button>
              </div>
            </div>

            {error && (
              <p role="alert" className="border-l-2 border-danger bg-danger/10 px-3 py-2 text-sm text-danger">
                {error}
              </p>
            )}

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
            <Link to="/contact" className="text-foreground underline underline-offset-4 hover:text-primary-hover">
              Contact support
            </Link>
          </p>
        </div>
      </main>

      <footer className="border-t border-white/5 px-6 py-4 text-xs text-foreground-subtle">
        <Link to="/privacy" className="hover:text-foreground-muted">Privacy</Link>
        <span className="mx-2">·</span>
        <Link to="/terms" className="hover:text-foreground-muted">Terms</Link>
        <span className="mx-2">·</span>
        <Link to="/help" className="hover:text-foreground-muted">Help</Link>
      </footer>
    </div>
  );
};

export default Login;