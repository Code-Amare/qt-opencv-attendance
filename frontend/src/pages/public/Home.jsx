import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../lib/axios";
import { usePageTitle } from "../../context/PageTitleContext";

// Adjust to match your Django urls.py (maps to HomeStatsView)
const HOME_URL = "/site/home/";

const features = [
  [
    "Face enrollment",
    "Administrators enroll students and teachers by capturing a few frames per person.",
  ],
  [
    "Live recognition",
    "Faces are matched in real time and confirmed over consecutive frames to avoid false marks.",
  ],
  [
    "Session-based attendance",
    "Every record is tied to a session, so each class or meeting has its own log.",
  ],
  [
    "User management",
    "Admins create and manage students and teachers, and their face status, from one table.",
  ],
  [
    "Reports",
    "Review attendance per session and per user, with a full audit trail.",
  ],
  [
    "Secure by design",
    "Cookie-based auth with CSRF protection and optional two-factor authentication.",
  ],
];

const steps = [
  [
    "Admin adds users",
    "Administrators create student and teacher accounts and enroll their faces.",
  ],
  [
    "Start a session",
    "Teachers open a session and attendance recognition begins.",
  ],
  ["Review", "Attendance is recorded automatically and available as reports."],
];

const STATUS_ROWS = [
  { key: "present", label: "Present", text: "text-success", bar: "bg-success" },
  { key: "late", label: "Late", text: "text-warning", bar: "bg-warning" },
  { key: "absent", label: "Absent", text: "text-danger", bar: "bg-danger" },
];

const fmt = (n) => (typeof n === "number" ? n.toLocaleString() : "—");

export default function Home() {
  const { updatePageTitle } = usePageTitle();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(
    () => updatePageTitle("FaceCall — Face recognition attendance"),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    api
      .get(HOME_URL, { skipAuthRefresh: true })
      .then((res) => !cancelled && setData(res.data))
      .catch(() => {}) // the page still works with placeholders
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const checkins = data ? data.present + data.late : null;

  const stats = [
    [fmt(data?.sessions), "Sessions held"],
    [fmt(data?.enrolled), "People enrolled"],
    [fmt(checkins), "Check-ins recorded"],
  ];

  const total = data ? data.present + data.late + data.absent : 0;

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-10 border-b border-white/5 bg-background">
        <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <Link to="/" className="text-base font-semibold tracking-tight">
            FaceCall
          </Link>
          <div className="hidden items-center gap-8 text-sm text-foreground-muted sm:flex">
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <a href="#how" className="hover:text-foreground">
              How it works
            </a>
            <Link to="/release" className="hover:text-foreground">
              Download
            </Link>
            <a href="#access" className="hover:text-foreground">
              Access
            </a>
          </div>
          <Link
            to="/login"
            className="rounded-sm bg-primary px-4 py-1.5 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Sign in
          </Link>
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
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/login"
              className="rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover"
            >
              Sign in
            </Link>
            <Link
              to="/release"
              className="rounded-sm border border-white/10 px-5 py-2.5 text-sm text-foreground hover:bg-background-elevated"
            >
              Download the app
            </Link>
            <a
              href="#features"
              className="px-3 py-2.5 text-sm text-foreground-muted hover:text-foreground"
            >
              See features
            </a>
          </div>
        </div>

        {/* Preview: overall totals only, no session or user data */}
        <div className="border border-white/10 bg-background-surface">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <span className="text-sm font-medium">Attendance overview</span>
            <span className="text-xs text-foreground-subtle">All sessions</span>
          </div>

          {loading ? (
            <p className="px-4 py-10 text-sm text-foreground-muted">Loading…</p>
          ) : !data || total === 0 ? (
            <p className="px-4 py-10 text-sm text-foreground-muted">
              No attendance recorded yet.
            </p>
          ) : (
            <div className="px-4 py-5">
              <div className="flex h-2 w-full overflow-hidden bg-background-elevated">
                {STATUS_ROWS.map(({ key, bar }) => (
                  <div
                    key={key}
                    className={bar}
                    style={{ width: `${(data[key] / total) * 100}%` }}
                  />
                ))}
              </div>

              <ul className="mt-5 divide-y divide-white/5 text-sm">
                {STATUS_ROWS.map(({ key, label, text }) => (
                  <li
                    key={key}
                    className="flex items-center justify-between py-3"
                  >
                    <span className={text}>{label}</span>
                    <span className="tabular-nums">{fmt(data[key])}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
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
        <h2 className="text-2xl font-semibold tracking-tight">
          Everything you need to run attendance
        </h2>
        <div className="mt-10 grid border-l border-t border-white/10 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(([title, text]) => (
            <div key={title} className="border-b border-r border-white/10 p-6">
              <h3 className="font-medium">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-foreground-muted">
                {text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section
        id="how"
        className="border-t border-white/5 bg-background-surface"
      >
        <div className="mx-auto max-w-6xl px-6 py-24">
          <h2 className="text-2xl font-semibold tracking-tight">
            How it works
          </h2>
          <ol className="mt-10 grid gap-10 sm:grid-cols-3">
            {steps.map(([t, d], i) => (
              <li key={t}>
                <span className="text-sm tabular-nums text-foreground-subtle">
                  0{i + 1}
                </span>
                <h3 className="mt-2 font-medium">{t}</h3>
                <p className="mt-2 text-sm text-foreground-muted">{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Access */}
      <section id="access" className="mx-auto max-w-6xl px-6 py-24">
        <div className="flex flex-col items-start justify-between gap-6 border border-white/10 bg-background-surface p-8 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">
              Already have an account?
            </h2>
            <p className="mt-1 text-sm text-foreground-muted">
              Sign in with the credentials provided by your administrator.
            </p>
          </div>
          <div className="flex shrink-0 gap-3">
            <Link
              to="/release"
              className="rounded-sm border border-white/10 px-5 py-2.5 text-sm text-foreground hover:bg-background-elevated"
            >
              Download
            </Link>
            <Link
              to="/login"
              className="rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5">
        <div className="mx-auto flex max-w-6xl flex-col justify-between gap-4 px-6 py-8 text-sm text-foreground-subtle sm:flex-row">
          <span>© {new Date().getFullYear()} FaceCall</span>
          <div className="flex gap-6">
            <Link to="/release" className="hover:text-foreground-muted">
              Download
            </Link>
            <Link to="/privacy" className="hover:text-foreground-muted">
              Privacy
            </Link>
            <Link to="/terms" className="hover:text-foreground-muted">
              Terms
            </Link>
            <Link to="/help" className="hover:text-foreground-muted">
              Help
            </Link>
            <Link to="/contact" className="hover:text-foreground-muted">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
