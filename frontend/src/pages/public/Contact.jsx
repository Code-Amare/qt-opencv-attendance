import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

const subjects = [
  "Request account access",
  "Forgot password / locked out",
  "Report a problem",
  "General question",
];

const Contact = () => {
  const { updatePageTitle } = usePageTitle();

  const [form, setForm] = useState({ name: "", email: "", subject: subjects[0], message: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    updatePageTitle("Contact");
  }, []);

  const onChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    if (error) setError("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.name.trim() || !form.email.trim() || !form.message.trim()) {
      return setError("Please fill in your name, email and message.");
    }
    if (form.message.trim().length < 10) {
      return setError("Your message is too short. Add a few more details.");
    }

    setLoading(true);
    try {
      await api.post("/users/contact/", form, { skipAuthRefresh: true });
      setSent(true);
    } catch (err) {
      setError(getErrorMessage(err, "Could not send your message. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  const fieldClass =
    "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
    "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b border-white/5 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link to="/" className="text-base font-semibold tracking-tight">FaceCall</Link>
          <Link to="/login" className="text-sm text-foreground-muted hover:text-foreground">Sign in</Link>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl flex-1 gap-12 px-6 py-16 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <h1 className="text-3xl font-semibold tracking-tight">Contact us</h1>
          <p className="mt-3 text-sm text-foreground-muted">
            Accounts are created by your administrator. Use this form to request access,
            get help signing in, or report a problem.
          </p>

          <dl className="mt-10 space-y-6 border-t border-white/10 pt-6 text-sm">
            <div>
              <dt className="text-foreground-subtle">Email</dt>
              <dd className="mt-1">
                <a href="mailto:support@facecall.com" className="hover:text-primary-hover">
                  support@facecall.com
                </a>
              </dd>
            </div>
            <div>
              <dt className="text-foreground-subtle">Response time</dt>
              <dd className="mt-1">Within 1–2 business days</dd>
            </div>
          </dl>
        </div>

        <div className="lg:col-span-3">
          {sent ? (
            <div className="space-y-6 border border-white/10 bg-background-surface p-8">
              <Alert variant="success" title="Message sent">
                Thanks for reaching out. We'll reply to {form.email} soon.
              </Alert>
              <Link
                to="/"
                className="inline-block rounded-sm border border-white/10 px-4 py-2 text-sm hover:bg-background-elevated"
              >
                Back to home
              </Link>
            </div>
          ) : (
            <form onSubmit={onSubmit} noValidate className="space-y-4 border border-white/10 bg-background-surface p-8">
              {error && (
                <Alert variant="error" title="Message not sent" onClose={() => setError("")}>
                  {error}
                </Alert>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="name" className="mb-1.5 block text-sm text-foreground-muted">Full name</label>
                  <input id="name" name="name" autoComplete="name"
                    value={form.name} onChange={onChange} className={fieldClass} />
                </div>
                <div>
                  <label htmlFor="email" className="mb-1.5 block text-sm text-foreground-muted">Email</label>
                  <input id="email" name="email" type="email" autoComplete="email"
                    value={form.email} onChange={onChange} className={fieldClass} />
                </div>
              </div>

              <div>
                <label htmlFor="subject" className="mb-1.5 block text-sm text-foreground-muted">Subject</label>
                <select id="subject" name="subject" value={form.subject} onChange={onChange} className={fieldClass}>
                  {subjects.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="message" className="mb-1.5 block text-sm text-foreground-muted">Message</label>
                <textarea id="message" name="message" rows={6}
                  value={form.message} onChange={onChange} className={`${fieldClass} resize-y`} />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="cursor-pointer rounded-sm bg-primary px-6 py-2.5 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Sending…" : "Send message"}
              </button>
            </form>
          )}
        </div>
      </main>

      <footer className="border-t border-white/5 px-6 py-4 text-xs text-foreground-subtle">
        <div className="mx-auto flex max-w-6xl gap-2">
          <Link to="/privacy" className="hover:text-foreground-muted">Privacy</Link>
          <span>·</span>
          <Link to="/terms" className="hover:text-foreground-muted">Terms</Link>
          <span>·</span>
          <Link to="/help" className="hover:text-foreground-muted">Help</Link>
        </div>
      </footer>
    </div>
  );
};

export default Contact;