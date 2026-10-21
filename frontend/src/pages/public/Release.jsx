import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FaWindows, FaApple, FaLinux } from "react-icons/fa";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { usePageTitle } from "../../context/PageTitleContext";

// Adjust to match your Django urls.py (maps to LatestReleaseView)
const LATEST_RELEASE_URL = "/site/releases/latest/";

const OS_LIST = [
  {
    key: "windows",
    label: "Windows",
    Icon: FaWindows,
    aliases: ["windows", "win"],
  },
  {
    key: "mac",
    label: "macOS",
    Icon: FaApple,
    aliases: ["mac", "macos", "darwin", "osx"],
  },
  { key: "linux", label: "Linux", Icon: FaLinux, aliases: ["linux"] },
];

const normalizePlatform = (value = "") => {
  const v = String(value).toLowerCase();
  const match = OS_LIST.find((os) => os.aliases.includes(v));
  return match ? match.key : v;
};

const formatDate = (value) => {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
};

// Assumes file_size is stored in bytes
const formatSize = (bytes) => {
  const n = Number(bytes);
  if (!n || n < 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let size = n;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i += 1;
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

export default function Release() {
  const { updatePageTitle } = usePageTitle();

  const [release, setRelease] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    updatePageTitle("Download FaceCall");
  }, []);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const res = await api.get(LATEST_RELEASE_URL, {
          skipAuthRefresh: true,
        });
        if (!cancelled) setRelease(res.data);
      } catch (err) {
        if (cancelled) return;
        // 404 just means nothing is published yet: every OS shows muted
        if (err?.response?.status !== 404) {
          setError(getErrorMessage(err, "Unable to load the latest release."));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // { windows: [asset, ...], mac: [...], linux: [...] }
  const assetsByOs = useMemo(() => {
    const groups = {};
    (release?.assets || []).forEach((asset) => {
      const key = normalizePlatform(asset.platform);
      (groups[key] ||= []).push(asset);
    });
    return groups;
  }, [release]);

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-10 border-b border-white/5 bg-background">
        <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <Link to="/" className="text-base font-semibold tracking-tight">
            FaceCall
          </Link>
          <Link
            to="/login"
            className="rounded-sm bg-primary px-4 py-1.5 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Sign in
          </Link>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-20">
        {/* Heading */}
        <p className="text-xs font-medium uppercase tracking-widest text-foreground-subtle">
          Desktop app
        </p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Download FaceCall
        </h1>
        <p className="mt-5 max-w-md text-foreground-muted">
          Install the FaceCall desktop app to run face recognition attendance on
          your own computer.
        </p>

        {/* Version info */}
        {release && (
          <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-foreground-muted">
            <span className="font-medium text-foreground">
              Version {release.version}
            </span>
            {formatDate(release.published_at) && (
              <span>Released {formatDate(release.published_at)}</span>
            )}
          </div>
        )}

        {error && (
          <div className="mt-8 max-w-xl">
            <Alert
              variant="error"
              title="Something went wrong"
              onClose={() => setError("")}
            >
              {error}
            </Alert>
          </div>
        )}

        {/* OS cards */}
        <div className="mt-10 grid border-l border-t border-white/10 sm:grid-cols-3">
          {OS_LIST.map(({ key, label, Icon }) => {
            const assets = assetsByOs[key] || [];
            const available = !loading && assets.length > 0;

            return (
              <div
                key={key}
                aria-disabled={!available}
                className={`flex flex-col items-start border-b border-r border-white/10 p-6 transition ${
                  available ? "" : "opacity-40"
                }`}
              >
                <Icon
                  aria-hidden="true"
                  className={`h-12 w-12 ${
                    available ? "text-foreground" : "text-foreground-subtle"
                  }`}
                />
                <h2 className="mt-5 font-medium">{label}</h2>

                {loading ? (
                  <p className="mt-2 text-sm text-foreground-muted">
                    Checking…
                  </p>
                ) : available ? (
                  <div className="mt-4 flex w-full flex-col gap-3">
                    {assets.map((asset) => (
                      <div key={`${asset.platform}-${asset.architecture}`}>
                        <a
                          href={asset.download_url}
                          className="flex items-center justify-between rounded-sm bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
                        >
                          <span>Download</span>
                          <span className="text-xs uppercase opacity-80">
                            {asset.architecture}
                          </span>
                        </a>
                        {formatSize(asset.file_size) && (
                          <p className="mt-1 text-xs text-foreground-subtle">
                            {formatSize(asset.file_size)}
                          </p>
                        )}
                        {asset.checksum_sha256 && (
                          <details className="mt-1 text-xs text-foreground-subtle">
                            <summary className="cursor-pointer hover:text-foreground-muted">
                              SHA-256
                            </summary>
                            <code className="mt-1 block break-all">
                              {asset.checksum_sha256}
                            </code>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-foreground-muted">
                    Not available yet
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* Release notes */}
        {release?.release_notes && (
          <section className="mt-16 max-w-2xl">
            <h2 className="text-xl font-semibold tracking-tight">What's new</h2>
            <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-foreground-muted">
              {release.release_notes}
            </p>
          </section>
        )}
      </main>

      {/* Footer */}
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
}
