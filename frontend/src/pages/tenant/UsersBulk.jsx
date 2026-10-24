import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";
import { getTenantPaths } from "../../config/tenantDashboardNavigation";

const COLUMNS = [
  "first_name",
  "last_name",
  "email",
  "phone_number",
  "section",
  "date_of_birth",
];

const MAX_ROWS = 500;
const MAX_FILE_BYTES = 2 * 1024 * 1024;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const LIMITS = {
  first_name: 150,
  last_name: 150,
  phone_number: 20,
  section: 50,
};

const TEMPLATE = [
  COLUMNS.join(","),
  "Abebe,Kebede,abebe@example.com,0911000000,3,5/14/2008",
  "Sara,Tesfaye,sara@example.com,,3,11/2/2007",
].join("\r\n");

const TEMPLATE_HREF = `data:text/csv;charset=utf-8,${encodeURIComponent(
  `\uFEFF${TEMPLATE}\r\n`,
)}`;

const pad = (n) => String(n).padStart(2, "0");

function parseCsv(text) {
  const input = text.replace(/^\uFEFF/, "");
  const firstLine = input.split(/\r?\n/, 1)[0] ?? "";
  const delimiter =
    firstLine.includes(";") && !firstLine.includes(",") ? ";" : ",";

  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < input.length; i += 1) {
    const c = input[i];

    if (inQuotes) {
      if (c === '"') {
        if (input[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === delimiter) {
      row.push(field);
      field = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && input[i + 1] === "\n") i += 1;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += c;
    }
  }

  if (field !== "" || row.length) {
    row.push(field);
    rows.push(row);
  }

  return rows.filter((r) => r.some((v) => v.trim() !== ""));
}

function parseDate(value, order) {
  let year;
  let month;
  let day;

  const iso = value.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (iso) {
    year = Number(iso[1]);
    month = Number(iso[2]);
    day = Number(iso[3]);
  } else {
    const slashed = value.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})$/);
    if (!slashed) return null;

    const first = Number(slashed[1]);
    const second = Number(slashed[2]);
    year = Number(slashed[3]);
    if (slashed[3].length === 2) {
      year += year > new Date().getFullYear() % 100 ? 1900 : 2000;
    }
    month = order === "mdy" ? first : second;
    day = order === "mdy" ? second : first;
  }

  if (year < 1900) return null;

  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }

  return `${year}-${pad(month)}-${pad(day)}`;
}

function buildRows(text, dateOrder) {
  const table = parseCsv(text);
  if (table.length < 2) {
    return { error: "The file has no data rows." };
  }

  const header = table[0].map((h) =>
    h.trim().toLowerCase().replace(/\s+/g, "_"),
  );
  if (!header.includes("email")) {
    return { error: "The file needs an email column. Use the template." };
  }
  if (table.length - 1 > MAX_ROWS) {
    return { error: `A file can have at most ${MAX_ROWS} rows.` };
  }

  const seen = new Map();

  const rows = table.slice(1).map((cells, index) => {
    const line = index + 1;
    const data = {};
    COLUMNS.forEach((column) => {
      const at = header.indexOf(column);
      data[column] = at === -1 ? "" : (cells[at] ?? "").trim();
    });
    data.email = data.email.toLowerCase();

    let problem = "";

    if (!data.email) {
      problem = "Email is missing";
    } else if (!EMAIL_RE.test(data.email)) {
      problem = "Email is not valid";
    } else if (seen.has(data.email)) {
      problem = `Same email as row ${seen.get(data.email)}`;
    } else {
      seen.set(data.email, line);
    }

    if (!problem && data.date_of_birth) {
      const normalized = parseDate(data.date_of_birth, dateOrder);
      if (normalized) {
        data.date_of_birth = normalized;
      } else {
        problem = "Date of birth is not a valid date";
      }
    }

    if (!problem) {
      const tooLong = Object.entries(LIMITS).find(
        ([key, max]) => data[key].length > max,
      );
      if (tooLong) problem = `${tooLong[0].replace("_", " ")} is too long`;
    }

    return { line, data, problem };
  });

  return { rows };
}

export default function UsersBulk() {
  const { tenant } = useAuth();
  const paths = getTenantPaths(tenant.slug);
  const fileInput = useRef(null);

  const [fileName, setFileName] = useState("");
  const [raw, setRaw] = useState("");
  const [dateOrder, setDateOrder] = useState("mdy");
  const [serverProblems, setServerProblems] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null);

  updateTitle("Bulk add users");
  useUpdatePageTitle("Bulk add users");

  const parsed = useMemo(
    () => (raw ? buildRows(raw, dateOrder) : null),
    [raw, dateOrder],
  );

  const rows = useMemo(
    () =>
      (parsed?.rows ?? []).map((r) =>
        serverProblems[r.line] ? { ...r, problem: serverProblems[r.line] } : r,
      ),
    [parsed, serverProblems],
  );

  const valid = useMemo(() => rows.filter((r) => !r.problem), [rows]);
  const problems = rows.length - valid.length;
  const shownError = error || parsed?.error || "";

  const onPickFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError("");
    setServerProblems({});
    setRaw("");
    setFileName("");

    if (file.size > MAX_FILE_BYTES) {
      return setError("The file must be 2 MB or smaller.");
    }

    try {
      setRaw(await file.text());
      setFileName(file.name);
    } catch {
      setError("Could not read the file.");
    }
  };

  const onChangeOrder = (e) => {
    setDateOrder(e.target.value);
    setServerProblems({});
    setError("");
  };

  const onReset = () => {
    setRaw("");
    setFileName("");
    setError("");
    setServerProblems({});
    if (fileInput.current) fileInput.current.value = "";
  };

  const onSubmit = async () => {
    if (valid.length === 0) return;

    setError("");
    setSubmitting(true);
    try {
      const res = await api.post("/tenant/users/bulk/", {
        users: valid.map((r) => ({ line: r.line, ...r.data })),
      });
      setCreated(res.data.created ?? valid.length);
    } catch (err) {
      const body = err.response?.data;
      if (Array.isArray(body?.errors)) {
        setServerProblems(
          Object.fromEntries(body.errors.map((item) => [item.row, item.error])),
        );
      }
      setError(getErrorMessage(err, "Failed to add the users."));
    } finally {
      setSubmitting(false);
    }
  };

  if (created !== null) {
    return (
      <div className="mx-auto max-w-2xl space-y-6 p-6">
        <Alert variant="success" title="Users added">
          {created} {created === 1 ? "user was" : "users were"} added to{" "}
          {tenant.name}.
        </Alert>
        <div className="flex flex-wrap gap-3">
          <Link
            to={paths.users}
            className="rounded-sm bg-primary px-5 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            View users
          </Link>
          <button
            type="button"
            onClick={() => {
              setCreated(null);
              onReset();
            }}
            className="cursor-pointer rounded-sm border border-white/10 px-5 py-2 text-sm text-foreground hover:bg-background-elevated"
          >
            Add more
          </button>
        </div>
      </div>
    );
  }

  const cards = [
    ["Rows", rows.length, ""],
    ["Ready to add", valid.length, "text-success"],
    ["With problems", problems, problems ? "text-warning" : ""],
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <Link
        to={paths.users}
        className="inline-block text-sm text-foreground-muted hover:text-foreground"
      >
        ← Back to users
      </Link>

      {shownError && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {shownError}
        </Alert>
      )}

      <section className="border border-white/10 bg-background-surface">
        <div className="flex h-12 items-center border-b border-white/10 px-4 text-sm font-medium">
          Upload a file
        </div>
        <div className="space-y-5 p-6">
          <ol className="space-y-2 text-sm text-foreground-muted">
            <li>
              1.{" "}
              <a
                href={TEMPLATE_HREF}
                download="users-template.csv"
                className="text-foreground underline underline-offset-4 hover:text-primary-hover"
              >
                Download the template
              </a>{" "}
              and fill in one person per row.
            </li>
            <li>
              2. Only <span className="text-foreground">email</span> is
              required. Dates can be 5/14/2008 or 2008-05-14.
            </li>
            <li>
              3. Save it as CSV and upload it here. Up to {MAX_ROWS} users per
              file.
            </li>
          </ol>

          <div className="flex flex-wrap items-center gap-3">
            <input
              ref={fileInput}
              id="users_file"
              type="file"
              accept=".csv,text/csv"
              onChange={onPickFile}
              className="hidden"
            />
            <label
              htmlFor="users_file"
              className="cursor-pointer rounded-sm border border-white/10 px-4 py-2 text-sm text-foreground hover:bg-background-elevated"
            >
              {fileName ? "Choose another file" : "Choose CSV file"}
            </label>
            {fileName && (
              <>
                <span className="text-sm text-foreground-muted">
                  {fileName}
                </span>
                <button
                  type="button"
                  onClick={onReset}
                  className="cursor-pointer text-sm text-foreground-muted hover:text-foreground"
                >
                  Clear
                </button>
              </>
            )}
          </div>

          <div className="sm:max-w-xs">
            <label
              htmlFor="date_order"
              className="mb-1.5 block text-sm text-foreground-muted"
            >
              Dates in my file are
            </label>
            <select
              id="date_order"
              value={dateOrder}
              onChange={onChangeOrder}
              className="w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm focus:border-primary-hover focus:outline-none"
            >
              <option value="mdy">Month/Day/Year (5/14/2008)</option>
              <option value="dmy">Day/Month/Year (14/5/2008)</option>
            </select>
          </div>
        </div>
      </section>

      {rows.length > 0 && (
        <>
          <section className="grid border-l border-t border-white/10 sm:grid-cols-3">
            {cards.map(([label, value, tone]) => (
              <div
                key={label}
                className="border-b border-r border-white/10 bg-background-surface p-6"
              >
                <div className={`text-3xl font-semibold tabular-nums ${tone}`}>
                  {value}
                </div>
                <div className="mt-1 text-sm text-foreground-muted">
                  {label}
                </div>
              </div>
            ))}
          </section>

          <section className="border border-white/10 bg-background-surface">
            <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
              <span className="text-sm font-medium">Preview</span>
              <span className="text-xs text-foreground-subtle">
                Rows with problems are skipped
              </span>
            </div>
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-background-surface">
                  <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                    <th className="px-4 py-2.5 font-medium">Row</th>
                    <th className="px-4 py-2.5 font-medium">Name</th>
                    <th className="px-4 py-2.5 font-medium">Email</th>
                    <th className="px-4 py-2.5 text-right font-medium">
                      Section
                    </th>
                    <th className="px-4 py-2.5 text-right font-medium">
                      Date of birth
                    </th>
                    <th className="px-4 py-2.5 text-right font-medium">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={r.line}
                      className="border-b border-white/5 last:border-0"
                    >
                      <td className="px-4 py-3 tabular-nums text-foreground-subtle">
                        {r.line}
                      </td>
                      <td className="px-4 py-3">
                        {`${r.data.first_name} ${r.data.last_name}`.trim() ||
                          "—"}
                      </td>
                      <td className="px-4 py-3 text-foreground-muted">
                        {r.data.email || "—"}
                      </td>
                      <td className="px-4 py-3 text-right text-foreground-muted">
                        {r.data.section || "—"}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                        {r.data.date_of_birth || "—"}
                      </td>
                      <td
                        className={`px-4 py-3 text-right ${
                          r.problem ? "text-danger" : "text-success"
                        }`}
                      >
                        {r.problem || "Ready"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="flex items-center justify-end gap-3">
            <Link
              to={paths.users}
              className="rounded-sm px-4 py-2 text-sm text-foreground-muted hover:text-foreground"
            >
              Cancel
            </Link>
            <button
              type="button"
              onClick={onSubmit}
              disabled={submitting || valid.length === 0}
              className="cursor-pointer rounded-sm bg-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting
                ? "Adding…"
                : `Add ${valid.length} ${valid.length === 1 ? "user" : "users"}`}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
