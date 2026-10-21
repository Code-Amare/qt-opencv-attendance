import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useUpdatePageTitle } from "../../context/PageTitleContext";

const formatDate = (value) => {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
};

function Row({ label, children }) {
  return (
    <div className="grid gap-1 border-b border-white/5 py-3 last:border-0 sm:grid-cols-3 sm:gap-4">
      <dt className="text-sm text-foreground-muted">{label}</dt>
      <dd className="text-sm sm:col-span-2">{children || "—"}</dd>
    </div>
  );
}

function Badge({ on, onText, offText }) {
  return (
    <span className={on ? "text-success" : "text-foreground-subtle"}>
      {on ? onText : offText}
    </span>
  );
}

export default function Profile() {
  const { user, loading } = useAuth();
  useUpdatePageTitle("Profile");

  if (loading) return <p className="p-6 text-foreground-muted">Loading…</p>;

  const fullName = user.fullName?.trim() || user.email;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
        {user.isStaff && (
          <Link
            to="/admin/profile/edit"
            className="rounded-sm bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Edit profile
          </Link>
        )}
      </div>

      <div className="mx-auto w-full max-w-2xl border border-white/10 bg-background-surface p-6">
        {/* Picture + name */}
        <div className="flex items-center gap-4 border-b border-white/10 pb-6">
          <div className="h-20 w-20 shrink-0 overflow-hidden rounded-full border border-white/10 bg-background-elevated">
            {user.profilePicture ? (
              <img
                src={user.profilePicture}
                alt={fullName}
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="flex h-full w-full items-center justify-center text-xs text-foreground-subtle">
                No photo
              </span>
            )}
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-lg font-medium">{fullName}</h2>
            <p className="truncate text-sm text-foreground-muted">
              {user.email}
            </p>
            <p className="mt-1 text-xs uppercase tracking-wider text-foreground-subtle">
              {user.isStaff ? "Administrator" : "Member"}
            </p>
          </div>
        </div>

        <dl className="mt-2">
          <Row label="First name">{user.firstName}</Row>
          <Row label="Last name">{user.lastName}</Row>
          <Row label="Email">{user.email}</Row>
          <Row label="Phone number">{user.phoneNumber}</Row>
          <Row label="Date of birth">{formatDate(user.dateOfBirth)}</Row>
          <Row label="Gender">
            <span className="capitalize">{user.gender}</span>
          </Row>
          <Row label="Member since">{formatDate(user.dateJoined)}</Row>
          <Row label="Email status">
            <Badge on={user.emailVerified} onText="Verified" offText="Not verified" />
          </Row>
          <Row label="Two-factor">
            <Badge on={user.twoFactorEnabled} onText="Enabled" offText="Disabled" />
          </Row>
        </dl>

        {!user.isStaff && (
          <p className="mt-4 text-xs text-foreground-subtle">
            Only administrators can edit profile details. Contact an
            administrator if something needs to change.
          </p>
        )}
      </div>
    </div>
  );
}