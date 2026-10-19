import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const LoginViaLink = () => {
  const { code } = useParams();
  const navigate = useNavigate();
  const { updatePageTitle } = usePageTitle();

  const [status, setStatus] = useState("checking"); // checking | invalid
  const [error, setError] = useState("");
  const called = useRef(false); // the code is single-use, so StrictMode must not fire it twice

  useEffect(() => {
    updatePageTitle("Signing in");

    if (called.current) return;
    called.current = true;

    api
      .post(`/users/login/email/${code}/`, null, { skipAuthRefresh: true })
      .then(() => navigate("/admin", { replace: true }))
      .catch((err) => {
        setError(getErrorMessage(err));
        setStatus("invalid");
      });
  }, [code]);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-white/5 px-6 py-4">
        <Link to="/" className="text-base font-semibold tracking-tight">
          FaceCall
        </Link>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          {status === "checking" && (
            <p className="text-sm text-foreground-muted">Signing you in…</p>
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
              <Link
                to="/login"
                className="mt-6 inline-block rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover"
              >
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
