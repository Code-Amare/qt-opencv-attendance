import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import PasswordInput from "../../components/PasswordInput";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const ResetPassword = () => {
  const { code } = useParams();
  const { updatePageTitle } = usePageTitle();

  const [status, setStatus] = useState("checking"); // checking | valid | invalid | done
  const [form, setForm] = useState({ password: "", confirm: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    updatePageTitle("Reset password");

    api
      .post("/users/reset-password/check/", { code }, { skipAuthRefresh: true })
      .then(() => setStatus("valid"))
      .catch(() => setStatus("invalid"));
  }, [code]);

  const onChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    if (error) setError("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (form.password.length < 8) return setError("Your password must be at least 8 characters long.");
    if (form.password !== form.confirm) return setError("The two passwords don't match.");

    setLoading(true);
    try {
      await api.post(`/users/reset-password/${code}/`, { password: form.password }, { skipAuthRefresh: true });
      setStatus("done");
    } catch (err) {
      const msg = getErrorMessage(err);
      if (/invalid or expired/i.test(msg)) setStatus("invalid");
      else setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const primaryLink =
    "mt-6 inline-block rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover";

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-white/5 px-6 py-4">
        <Link to="/" className="text-base font-semibold tracking-tight">FaceCall</Link>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          {status === "checking" && (
            <p className="text-sm text-foreground-muted">Verifying your link…</p>
          )}

          {status === "invalid" && (
            <>
              <h1 className="text-2xl font-semibold tracking-tight">Link invalid or expired</h1>
              <div className="mt-4">
                <Alert variant="error" title="This link can't be used">
                  Password reset links expire and can only be used once. Request a new one to continue.
                </Alert>
              </div>
              <Link to="/forgot-password" className={primaryLink}>Request new link</Link>
            </>
          )}

          {status === "done" && (
            <>
              <h1 className="text-2xl font-semibold tracking-tight">Password updated</h1>
              <div className="mt-4">
                <Alert variant="success" title="All set">
                  Your password has been reset. Sign in with your new password.
                </Alert>
              </div>
              <Link to="/login" className={primaryLink}>Sign in</Link>
            </>
          )}

          {status === "valid" && (
            <>
              <h1 className="text-2xl font-semibold tracking-tight">Reset password</h1>
              <p className="mt-1 text-sm text-foreground-muted">Choose a new password for your account.</p>

              <form onSubmit={onSubmit} noValidate className="mt-8 space-y-4">
                {error && (
                  <Alert variant="error" title="Couldn't reset password" onClose={() => setError("")}>
                    {error}
                  </Alert>
                )}

                <div>
                  <label htmlFor="password" className="mb-1.5 block text-sm text-foreground-muted">
                    New password
                  </label>
                  <PasswordInput id="password" name="password" autoComplete="new-password"
                    value={form.password} onChange={onChange} invalid={!!error} />
                </div>

                <div>
                  <label htmlFor="confirm" className="mb-1.5 block text-sm text-foreground-muted">
                    Confirm password
                  </label>
                  <PasswordInput id="confirm" name="confirm" autoComplete="new-password"
                    value={form.confirm} onChange={onChange} invalid={!!error} />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full cursor-pointer rounded-sm bg-primary py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "Updating…" : "Reset password"}
                </button>
              </form>
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default ResetPassword;