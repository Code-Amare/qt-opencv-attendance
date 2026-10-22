import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Alert from "../../components/Alert";
import api from "../../lib/axios";
import { getErrorMessage } from "../../lib/errors";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";
import { updateTitle } from "../../context/DashboardTitleContext";
import { getTenantPaths } from "../../config/tenantDashboardNavigation";

const fieldClass =
  "w-full rounded-sm border border-white/10 bg-background-elevated px-3 py-2.5 text-sm " +
  "placeholder:text-foreground-subtle focus:border-primary-hover focus:outline-none";

const labelClass = "mb-1.5 block text-sm text-foreground-muted";

const ghostBtn =
  "cursor-pointer rounded-sm border border-white/10 px-3 py-1.5 text-xs text-foreground " +
  "hover:bg-background-elevated disabled:cursor-not-allowed disabled:opacity-50";

const pad = (n) => String(n).padStart(2, "0");

const ageFrom = (dob) => {
  if (!dob) return null;
  const birth = new Date(dob);
  if (Number.isNaN(birth.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const months = now.getMonth() - birth.getMonth();
  if (months < 0 || (months === 0 && now.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age;
};

const fullName = (u) =>
  `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim() || u.username || "—";

export default function SessionNew() {
  const navigate = useNavigate();
  const { tenant } = useAuth();
  const paths = getTenantPaths(tenant.slug);

  const [form, setForm] = useState({
    name: "",
    started_at: "",
    ended_at: "",
    late_minutes: 10,
  });

  const [members, setMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [selected, setSelected] = useState(() => new Set());

  const [search, setSearch] = useState("");
  const [section, setSection] = useState("");
  const [minAge, setMinAge] = useState("");
  const [maxAge, setMaxAge] = useState("");
  const [faceOnly, setFaceOnly] = useState("");

  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  updateTitle("New session");
  useUpdatePageTitle("New session");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get("/tenant/users/");
        const list = res.data.users ?? res.data.results ?? res.data;
        setMembers(
          list.filter((u) => !u.is_tenant_admin && u.is_active !== false),
        );
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load users."));
      } finally {
        setLoadingMembers(false);
      }
    };

    load();
  }, []);

  const sections = useMemo(
    () =>
      [...new Set(members.map((u) => u.section).filter(Boolean))].sort((a, b) =>
        String(a).localeCompare(String(b), undefined, { numeric: true }),
      ),
    [members],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const min = minAge === "" ? null : Number(minAge);
    const max = maxAge === "" ? null : Number(maxAge);

    return members.filter((u) => {
      if (section && u.section !== section) return false;
      if (faceOnly === "enrolled" && !u.has_face) return false;
      if (faceOnly === "missing" && u.has_face) return false;

      if (min !== null || max !== null) {
        const age = ageFrom(u.date_of_birth);
        if (age === null) return false;
        if (min !== null && age < min) return false;
        if (max !== null && age > max) return false;
      }

      if (!q) return true;
      return (
        fullName(u).toLowerCase().includes(q) ||
        (u.email ?? "").toLowerCase().includes(q)
      );
    });
  }, [members, search, section, minAge, maxAge, faceOnly]);

  const allFilteredSelected =
    filtered.length > 0 && filtered.every((u) => selected.has(u.id));

  const withoutFace = useMemo(
    () => members.filter((u) => selected.has(u.id) && !u.has_face).length,
    [members, selected],
  );

  const toggle = (id) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const selectFiltered = () =>
    setSelected((prev) => {
      const next = new Set(prev);
      filtered.forEach((u) => next.add(u.id));
      return next;
    });

  const deselectFiltered = () =>
    setSelected((prev) => {
      const next = new Set(prev);
      filtered.forEach((u) => next.delete(u.id));
      return next;
    });

  const clearFilters = () => {
    setSearch("");
    setSection("");
    setMinAge("");
    setMaxAge("");
    setFaceOnly("");
  };

  const filtersActive = Boolean(
    search || section || minAge || maxAge || faceOnly,
  );

  const onChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
    if (error) setError("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.name.trim() || !form.started_at) {
      return setError("Name and start time are required.");
    }
    if (form.ended_at && new Date(form.ended_at) <= new Date(form.started_at)) {
      return setError("The end time must be after the start time.");
    }
    if (selected.size === 0) {
      return setError("Select at least one person for this session.");
    }

    const minutes = Math.max(0, Number(form.late_minutes) || 0);
    const payload = {
      name: form.name.trim(),
      started_at: new Date(form.started_at).toISOString(),
      ended_at: form.ended_at ? new Date(form.ended_at).toISOString() : null,
      late_time: `${Math.floor(minutes / 60)}:${pad(minutes % 60)}:00`,
      target_ids: [...selected],
    };

    setSaving(true);
    try {
      await api.post("/attendance/sessions/", payload);
      navigate(paths.sessions, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, "Failed to create the session."));
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <Link
        to={paths.sessions}
        className="inline-block text-sm text-foreground-muted hover:text-foreground"
      >
        ← Back to sessions
      </Link>

      {error && (
        <Alert variant="error" title="Error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <form onSubmit={onSubmit} noValidate className="space-y-6">
        <section className="border border-white/10 bg-background-surface">
          <div className="flex h-12 items-center border-b border-white/10 px-4 text-sm font-medium">
            Details
          </div>
          <div className="space-y-4 p-6">
            <div>
              <label htmlFor="name" className={labelClass}>
                Name
              </label>
              <input
                id="name"
                name="name"
                value={form.name}
                onChange={onChange}
                placeholder="Morning lecture"
                className={fieldClass}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="started_at" className={labelClass}>
                  Starts
                </label>
                <input
                  id="started_at"
                  type="datetime-local"
                  name="started_at"
                  value={form.started_at}
                  onChange={onChange}
                  className={fieldClass}
                />
              </div>
              <div>
                <label htmlFor="ended_at" className={labelClass}>
                  Ends (optional)
                </label>
                <input
                  id="ended_at"
                  type="datetime-local"
                  name="ended_at"
                  value={form.ended_at}
                  onChange={onChange}
                  className={fieldClass}
                />
              </div>
              <div>
                <label htmlFor="late_minutes" className={labelClass}>
                  Late window (min)
                </label>
                <input
                  id="late_minutes"
                  type="number"
                  min="0"
                  name="late_minutes"
                  value={form.late_minutes}
                  onChange={onChange}
                  className={fieldClass}
                />
              </div>
            </div>
          </div>
        </section>

        <section className="border border-white/10 bg-background-surface">
          <div className="flex h-12 items-center justify-between border-b border-white/10 px-4">
            <span className="text-sm font-medium">Who is this session for?</span>
            <span className="text-xs tabular-nums text-foreground-subtle">
              {selected.size} selected
            </span>
          </div>

          <div className="space-y-4 border-b border-white/10 p-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or email"
                className={`${fieldClass} lg:col-span-2`}
              />
              <select
                value={section}
                onChange={(e) => setSection(e.target.value)}
                className={fieldClass}
              >
                <option value="">All sections</option>
                {sections.map((s) => (
                  <option key={s} value={s}>
                    Section {s}
                  </option>
                ))}
              </select>
              <select
                value={faceOnly}
                onChange={(e) => setFaceOnly(e.target.value)}
                className={fieldClass}
              >
                <option value="">All face statuses</option>
                <option value="enrolled">Face enrolled</option>
                <option value="missing">No face yet</option>
              </select>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <input
                type="number"
                min="0"
                value={minAge}
                onChange={(e) => setMinAge(e.target.value)}
                placeholder="Min age"
                className={fieldClass}
              />
              <input
                type="number"
                min="0"
                value={maxAge}
                onChange={(e) => setMaxAge(e.target.value)}
                placeholder="Max age"
                className={fieldClass}
              />
              <div className="flex items-center gap-2 sm:col-span-2 lg:justify-end">
                {filtersActive && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="cursor-pointer text-xs text-foreground-muted hover:text-foreground"
                  >
                    Clear filters
                  </button>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={selectFiltered}
                disabled={filtered.length === 0 || allFilteredSelected}
                className={ghostBtn}
              >
                Select all {filtered.length} shown
              </button>
              <button
                type="button"
                onClick={deselectFiltered}
                disabled={!filtered.some((u) => selected.has(u.id))}
                className={ghostBtn}
              >
                Deselect shown
              </button>
              <button
                type="button"
                onClick={() => setSelected(new Set())}
                disabled={selected.size === 0}
                className={ghostBtn}
              >
                Clear selection
              </button>
            </div>

            {withoutFace > 0 && (
              <p className="text-xs text-warning">
                {withoutFace} selected{" "}
                {withoutFace === 1 ? "person has" : "people have"} no enrolled
                face and can't be recognised yet.
              </p>
            )}
          </div>

          {loadingMembers ? (
            <p className="p-4 text-sm text-foreground-muted">Loading…</p>
          ) : members.length === 0 ? (
            <p className="p-4 text-sm text-foreground-muted">
              No users yet.{" "}
              <Link to={paths.usersNew} className="underline">
                Add one
              </Link>{" "}
              first.
            </p>
          ) : filtered.length === 0 ? (
            <p className="p-4 text-sm text-foreground-muted">
              No one matches these filters.
            </p>
          ) : (
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-background-surface">
                  <tr className="border-b border-white/5 text-left text-xs uppercase tracking-wider text-foreground-subtle">
                    <th className="w-12 px-4 py-2.5 font-medium">
                      <input
                        type="checkbox"
                        checked={allFilteredSelected}
                        onChange={() =>
                          allFilteredSelected
                            ? deselectFiltered()
                            : selectFiltered()
                        }
                        aria-label="Select all shown"
                        className="h-4 w-4 cursor-pointer"
                      />
                    </th>
                    <th className="px-4 py-2.5 font-medium">Name</th>
                    <th className="px-4 py-2.5 text-right font-medium">
                      Section
                    </th>
                    <th className="px-4 py-2.5 text-right font-medium">Age</th>
                    <th className="px-4 py-2.5 text-right font-medium">Face</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((u) => {
                    const age = ageFrom(u.date_of_birth);
                    const checked = selected.has(u.id);
                    return (
                      <tr
                        key={u.id}
                        onClick={() => toggle(u.id)}
                        className={`cursor-pointer border-b border-white/5 last:border-0 hover:bg-background-elevated ${
                          checked ? "bg-background-elevated" : ""
                        }`}
                      >
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggle(u.id)}
                            onClick={(e) => e.stopPropagation()}
                            aria-label={`Select ${fullName(u)}`}
                            className="h-4 w-4 cursor-pointer"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div>{fullName(u)}</div>
                          <div className="text-xs text-foreground-subtle">
                            {u.email}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-foreground-muted">
                          {u.section || "—"}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-foreground-muted">
                          {age ?? "—"}
                        </td>
                        <td
                          className={`px-4 py-3 text-right ${
                            u.has_face ? "text-success" : "text-warning"
                          }`}
                        >
                          {u.has_face ? "Enrolled" : "Not enrolled"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <div className="flex items-center justify-end gap-3">
          <Link
            to={paths.sessions}
            className="rounded-sm px-4 py-2 text-sm text-foreground-muted hover:text-foreground"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="cursor-pointer rounded-sm bg-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving
              ? "Creating…"
              : `Create session${selected.size ? ` for ${selected.size}` : ""}`}
          </button>
        </div>
      </form>
    </div>
  );
}