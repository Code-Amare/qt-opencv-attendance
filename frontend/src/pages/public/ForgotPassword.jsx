import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const ForgotPassword = () => {
  const { updatePageTitle } = usePageTitle();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    updatePageTitle("Forgot password");
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!email.trim()) return setError("Enter the email address linked to your account.");

    setLoading(true);
    try {
      const res = await api.post("/users/forgot-password/", { email }, { skipAuthRefresh: true });
      setMessage(res.data.detail);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-white/5 px-6 py-4">
        <Link to="/" className="text-base font-semibold tracking-tight">FaceCall</Link>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold tracking-tight">Forgot password</h1>
          <p className="mt-1 text-sm text-foreground-muted">
            Enter your email and we'll send you a link to reset your password.
          </p>

          {message ? (
            <div className="mt-8">
              <Alert variant="success" title="Check your email">
                {message} Look in your inbox and spam folder. The link expires shortly.
              </Alert>
            </div>
          ) : (
            <form onSubmit={onSubmit} noValidate className="mt-8 space-y-4">
              {error && (
                <Alert variant="error" title="Couldn't send the link" onClose={() => setError("")}>
                  {error}
                </Alert>
              )}

              <div>
                <label htmlFor="email" className="mb-1.5 block text-sm text-foreground-muted">Email</label>
                <input
                  id="email"
                  type="email"
                  name="email"
                  autoComplete="email"
                  aria-invalid={!!error}
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (error) setError("");
                  }}
                  className={`w-full rounded-sm border bg-background-elevated px-3 py-2.5 text-sm placeholder:text-foreground-subtle focus:outline-none ${
                    error ? "border-danger/60 focus:border-danger" : "border-white/10 focus:border-primary-hover"
                  }`}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full cursor-pointer rounded-sm bg-primary py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Sending…" : "Send reset link"}
              </button>
            </form>
          )}

          <p className="mt-8 text-sm text-foreground-muted">
            <Link to="/login" className="text-foreground underline underline-offset-4 hover:text-primary-hover">
              Back to sign in
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
};

export default ForgotPassword;