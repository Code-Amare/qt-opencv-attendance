import { useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { usePageTitle } from "../../context/PageTitleContext";

const MemberDashboard = () => {
  const { user, tenant, logout } = useAuth();
  const { updatePageTitle } = usePageTitle();

  useEffect(() => {
    updatePageTitle("Dashboard");
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-white/5 px-6 py-4">
        <span className="text-base font-semibold tracking-tight">
          {tenant.name}
        </span>
        <div className="flex items-center gap-4 text-sm text-foreground-muted">
          <span>{user.fullName}</span>
          <button
            onClick={logout}
            className="cursor-pointer rounded-sm border border-white/10 px-3 py-1.5 text-foreground hover:bg-background-elevated"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">
          Welcome, {user.firstName}
        </h1>
        <p className="mt-1 text-sm text-foreground-muted">
          Your attendance in {tenant.name} will appear here.
        </p>
      </main>
    </div>
  );
};

export default MemberDashboard;
