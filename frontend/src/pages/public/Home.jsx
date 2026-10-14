import { useEffect } from "react";
import { Link } from "react-router-dom";
import { usePageTitle } from "../../context/PageTitleContext.jsx";

const records = [
  { name: "Selam Tesfaye", time: "08:02", status: "Present" },
  { name: "Daniel Bekele", time: "08:04", status: "Present" },
  { name: "Hanna Girma", time: "08:11", status: "Present" },
  { name: "Yonas Alemu", time: "08:19", status: "Late" },
  { name: "Meron Abebe", time: "—", status: "Absent" },
];

const features = [
  ["Face enrollment", "Capture a few frames per person. Embeddings are generated and stored server-side."],
  ["Live recognition", "Faces are matched in real time and confirmed over consecutive frames to avoid false marks."],
  ["Session-based attendance", "Every record is tied to a session, so each class or meeting has its own log."],
  ["User management", "Search, edit and manage enrolled users and their face status from one table."],
  ["Reports", "Review attendance per session and per user, with a full audit trail."],
  ["Secure by design", "Cookie-based auth with CSRF protection and optional two-factor authentication."],
];

const stats = [
  ["< 1s", "Recognition time"],
  ["20", "Frame confirmation"],
  ["0", "Cards or sign-in sheets"],
];

const statusStyle = {
  Present: "text-success",
  Late: "text-warning",
  Absent: "text-danger",
};

export default function Home() {
  const { updatePageTitle } = usePageTitle();
  useEffect(() => updatePageTitle("FaceCall — Face recognition attendance"), []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-10 border-b border-white/5 bg-background">
        <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <Link to="/" className="text-base font-semibold tracking-tight">FaceCall</Link>
          <div className="hidden items-center gap-8 text-sm text-foreground-muted sm:flex">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#how" className="hover:text-foreground">How it works</a>
            <a href="#security" className="hover:text-foreground">Security</a>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Link to="/login" className="px-3 py-1.5 text-foreground-muted hover:text-foreground">Sign in</Link>
            <Link to="/register" className="rounded-sm bg-primary px-3.5 py-1.5 font-medium text-white hover:bg-primary-hover">
              Get started
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 lg:grid-cols-2 lg:py-28">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-foreground-subtle">
            Attendance management
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            Attendance that records itself.
          </h1>
          <p className="mt-5 max-w-md text-foreground-muted">
            FaceCall identifies people by face and logs attendance per session,
            with a central dashboard for users, sessions and reports.
          </p>
          <div className="mt-8 flex gap-3">
            <Link to="/register" className="rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover">
              Create account
            </Link>
            <Link to="/login" className="rounded-sm border border-white/10 px-5 py-2.5 text-sm text-foreground hover:bg-background-elevated">
              Sign in
            </Link>
          </div>
        </div>

        {/* Product preview */}
        <div className="border border-white/10 bg-background-surface">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <span className="text-sm font-medium">Session · Morning Class</span>
            <span className="text-xs text-foreground-subtle">Live</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                <th className="px-4 py-2.5 font-medium">Name</th>
                <th className="px-4 py-2.5 font-medium">Time</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.name} className="border-b border-white/5 last:border-0">
                  <td className="px-4 py-3">{r.name}</td>
                  <td className="px-4 py-3 tabular-nums text-foreground-muted">{r.time}</td>
                  <td className={`px-4 py-3 ${statusStyle[r.status]}`}>{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-white/5 bg-background-surface">
        <div className="mx-auto grid max-w-6xl divide-white/5 sm:grid-cols-3 sm:divide-x">
          {stats.map(([value, label]) => (
            <div key={label} className="px-6 py-8">
              <div className="text-3xl font-semibold tabular-nums">{value}</div>
              <div className="mt-1 text-sm text-foreground-muted">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-24">
        <h2 className="text-2xl font-semibold tracking-tight">Everything you need to run attendance</h2>
        <div className="mt-10 grid border-l border-t border-white/10 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(([title, text]) => (
            <div key={title} className="border-b border-r border-white/10 p-6">
              <h3 className="font-medium">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-foreground-muted">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t border-white/5 bg-background-surface">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
          <ol className="mt-10 grid gap-10 sm:grid-cols-3">
            {[
              ["Enroll", "Add users and capture their face from the dashboard."],
              ["Start a session", "Load the embeddings and enter the session ID."],
              ["Review", "Attendance is recorded automatically and available as reports."],
            ].map(([t, d], i) => (
              <li key={t}>
                <span className="text-sm tabular-nums text-foreground-subtle">0{i + 1}</span>
                <h3 className="mt-2 font-medium">{t}</h3>
                <p className="mt-2 text-sm text-foreground-muted">{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Security */}
      <section id="security" className="mx-auto max-w-6xl px-6 py-24">
        <div className="flex flex-col items-start justify-between gap-6 border border-white/10 bg-background-surface p-8 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Ready to get started?</h2>
            <p className="mt-1 text-sm text-foreground-muted">Create an account and enroll your first user in minutes.</p>
          </div>
          <Link to="/register" className="shrink-0 rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover">
            Create account
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5">
        <div className="mx-auto flex max-w-6xl flex-col justify-between gap-4 px-6 py-8 text-sm text-foreground-subtle sm:flex-row">
          <span>© {new Date().getFullYear()} FaceCall</span>
          <div className="flex gap-6">
            <Link to="/privacy" className="hover:text-foreground-muted">Privacy</Link>
            <Link to="/terms" className="hover:text-foreground-muted">Terms</Link>
            <Link to="/help" className="hover:text-foreground-muted">Help</Link>
            <Link to="/contact" className="hover:text-foreground-muted">Contact</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}