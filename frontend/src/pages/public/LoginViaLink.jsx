import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { usePageTitle } from "../../context/PageTitleContext";

const LoginViaLink = () => {
  const { code } = useParams();
  const navigate = useNavigate();
  const { updatePageTitle } = usePageTitle();
  const { login, getUser } = useAuth();

  const [status, setStatus] = useState("ready"); // ready | loading | done | invalid
  const [error, setError] = useState("");

  useEffect(() => {
    updatePageTitle("Sign in");
  }, []);

  const navigateAfterLogin = () => {
    if (user.isStaff) {
      navigate("/admin/dashboard", { replace: true });
    }
    navigate("/dashboard", { replace: true });
  };
  const confirmLogin = async () => {
    if (status === "loading") return;
    setStatus("loading");
    try {
      const res = await api.post(`/users/login/email/${code}/`, null, {
        skipAuthRefresh: true,
      });

      // put the user in AuthContext
      if (res.data?.user) login(res.data.user);
      else await getUser(); // fallback: fetch /users/me/

      setStatus("done");
    } catch (err) {
      setError(getErrorMessage(err));
      setStatus("invalid");
    }
  };

  const primaryBtn =
    "mt-6 w-full cursor-pointer rounded-sm bg-primary px-5 py-2.5 text-center text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60";

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-white/5 px-6 py-4">
        <Link to="/" className="text-base font-semibold tracking-tight">
          FaceCall
        </Link>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          {(status === "ready" || status === "loading") && (
            <>
              <h1 className="text-2xl font-semibold tracking-tight">
                Confirm your login
              </h1>
              <p className="mt-1 text-sm text-foreground-muted">
                Click the button below to sign in to your account.
              </p>
              <button
                type="button"
                onClick={confirmLogin}
                disabled={status === "loading"}
                className={primaryBtn}
              >
                {status === "loading" ? "Signing in…" : "Log in"}
              </button>
            </>
          )}

          {status === "done" && (
            <>
              <h1 className="text-2xl font-semibold tracking-tight">
                You're logged in
              </h1>
              <div className="mt-4">
                <Alert variant="success" title="All set">
                  You have been signed in successfully.
                </Alert>
              </div>
              <button
                type="button"
                onClick={navigateAfterLogin}
                className={primaryBtn}
              >
                Go to dashboard
              </button>
            </>
          )}

          {status === "invalid" && (
            <>
              <h1 className="text-2xl font-semibold tracking-tight">
                Login link invalid or expired
              </h1>
              <div className="mt-4">
                <Alert variant="error" title="This link can't be used">
                  {error ||
                    "Login links expire and can only be used once. Sign in again to get a new one."}
                </Alert>
              </div>
              <Link to="/login" className={`${primaryBtn} inline-block`}>
                Back to login
              </Link>
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default LoginViaLink;
