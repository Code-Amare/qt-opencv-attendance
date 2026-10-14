import { useState, useEffect } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import GoogleAuthButton from "../../components/GoogleAuthButton";
import api from "../../lib/axios";
import { useAuth } from "../../context/AuthContext";
import { usePageTitle } from "../../context/PageTitleContext";

const inputClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const Login = () => {
  const navigate = useNavigate();
  const { user, login } = useAuth();
  const { updatePageTitle } = usePageTitle();

  const [form, setForm] = useState({ username_or_email: "", password: "" });
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
              <input
                id="password"
                type="password"
                name="password"
                autoComplete="current-password"
                required
                value={form.password}
                onChange={onChange}
                className={inputClass}
              />
            </div>

            {error && (
              <p role="alert" className="border-l-2 border-danger bg-danger/10 px-3 py-2 text-sm text-danger">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="cursor-pointer w-full rounded-sm bg-primary py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:opacity-60"
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
            No account?{" "}
            <Link to="/register" className="text-foreground underline underline-offset-4 hover:text-primary-hover">
              Create one
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