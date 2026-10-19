import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  FiChevronDown,
  FiChevronLeft,
  FiChevronRight,
  FiEdit,
  FiLogOut,
  FiMenu,
  FiUser,
  FiX,
} from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import { useSiteInfo } from "../context/SiteInfoContext";
import ThemeToggler from "./ThemeToggler";
import dashboardNavigation, {
  PATHS,
  getPageTitle,
} from "../config/dashboardNavigation";

const STORAGE_KEY = "dashboard-sidebar-collapsed";

/* ------------------------------------------------------------ helpers */
function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    () => typeof window !== "undefined" && window.matchMedia(query).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = (e) => setMatches(e.matches);
    setMatches(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

// Reads both camelCase and snake_case user fields.
function getUserDisplay(user) {
  const firstName = user?.firstName ?? user?.first_name ?? "";
  const lastName = user?.lastName ?? user?.last_name ?? "";
  const fullName =
    user?.fullName ??
    user?.full_name ??
    (`${firstName} ${lastName}`.trim() || user?.username || "User");

  return {
    fullName,
    email: user?.email ?? "",
    picture: user?.profilePicture ?? user?.profile_picture ?? "",
    initial: (firstName || fullName || "U").charAt(0).toUpperCase(),
  };
}

const isPathActive = (pathname, path) =>
  pathname === path || pathname.startsWith(path + "/");

const hasActiveChild = (item, pathname) =>
  !!item.children?.some((child) => isPathActive(pathname, child.path));

function readCollapsed() {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

/* ------------------------------------------------------------- avatar */
function UserAvatar({ user, className = "h-8 w-8" }) {
  const { fullName, picture, initial } = getUserDisplay(user);

  return (
    <div
      className={`${className} rounded-full overflow-hidden bg-primary-subtle flex items-center justify-center flex-shrink-0`}
    >
      {picture ? (
        <img
          src={picture}
          alt={fullName}
          className="h-full w-full object-cover"
        />
      ) : (
        <span className="text-sm font-semibold text-primary">{initial}</span>
      )}
    </div>
  );
}

/* ---------------------------------------------------------- user card */
function DashboardUserCard({ user, collapsed, onNavigate }) {
  if (!user) return null;
  const { fullName, email } = getUserDisplay(user);

  if (collapsed) {
    return (
      <NavLink
        to={PATHS.profile}
        onClick={onNavigate}
        title={fullName}
        className="flex flex-shrink-0 justify-center border-t border-border p-2"
      >
        <UserAvatar user={user} className="h-8 w-8" />
      </NavLink>
    );
  }

  return (
    <NavLink
      to={PATHS.profile}
      onClick={onNavigate}
      className="block flex-shrink-0 border-t border-border p-4 transition-colors hover:bg-surface-hover"
    >
      <div className="flex items-center gap-3">
        <UserAvatar user={user} className="h-12 w-12" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {fullName}
          </p>
          <p className="truncate text-xs text-muted-foreground">{email}</p>
        </div>
      </div>
    </NavLink>
  );
}

/* ---------------------------------------------------------- user menu */
function UserMenu() {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!user) return null;

  const menuItems = [
    {
      label: "View Profile",
      icon: FiUser,
      action: () => navigate(PATHS.profile),
    },
    {
      label: "Edit Profile",
      icon: FiEdit,
      action: () => navigate(PATHS.profileEdit),
    },
    { label: "Logout", icon: FiLogOut, action: () => logout?.() },
  ];

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-surface-hover transition-colors cursor-pointer"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <UserAvatar user={user} className="h-8 w-8" />
        <FiChevronDown className="h-4 w-4 text-muted-foreground hidden sm:block" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-48 origin-top-right rounded-lg bg-surface shadow-lg ring-1 ring-border-strong z-50">
          <div className="py-1">
            {menuItems.map((item) => (
              <button
                key={item.label}
                onClick={() => {
                  item.action();
                  setIsOpen(false);
                }}
                className="flex w-full items-center gap-3 px-4 py-2 text-sm text-foreground hover:bg-surface-hover transition-colors cursor-pointer"
              >
                <item.icon className="h-4 w-4 text-muted-foreground" />
                {item.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------ top bar */
function DashboardNav({ setSidebarOpen }) {
  const { pathname } = useLocation();

  return (
    <header className="flex h-16 flex-shrink-0 items-center justify-between gap-3 border-b border-border bg-surface px-4">
      <div className="flex min-w-0 items-center gap-2">
        <button
          className="lg:hidden rounded-md p-2 text-muted-foreground hover:bg-surface-hover cursor-pointer"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open sidebar"
        >
          <FiMenu className="h-5 w-5" />
        </button>

        <div className="truncate text-lg font-semibold text-foreground cursor-default">
          {getPageTitle(pathname)}
        </div>
      </div>

      <UserMenu />
    </header>
  );
}

/* ------------------------------------------------------------ sidebar */
function DashboardSidebar({ open, setOpen }) {
  const { user } = useAuth();
  const { siteInfo } = useSiteInfo();
  const { pathname } = useLocation();
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  // Collapsing only exists on desktop. The mobile drawer is always full width.
  const [isCollapsed, setIsCollapsed] = useState(readCollapsed);
  const collapsed = isCollapsed && isDesktop;

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(isCollapsed));
    } catch {
      /* storage unavailable: ignore */
    }
  }, [isCollapsed]);

  const [expandedMenus, setExpandedMenus] = useState(() =>
    Object.fromEntries(
      dashboardNavigation
        .filter((item) => hasActiveChild(item, pathname))
        .map((item) => [item.name, true]),
    ),
  );

  const [popoverItem, setPopoverItem] = useState(null);
  const popoverRef = useRef(null);
  const buttonRefs = useRef({});

  // On every route change: close the popover, open the group that is active.
  useEffect(() => {
    setPopoverItem(null);
    setExpandedMenus((prev) => {
      const next = { ...prev };
      dashboardNavigation.forEach((item) => {
        if (hasActiveChild(item, pathname)) next[item.name] = true;
      });
      return next;
    });
  }, [pathname]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        popoverItem &&
        popoverRef.current &&
        !popoverRef.current.contains(event.target) &&
        !buttonRefs.current[popoverItem]?.contains(event.target)
      ) {
        setPopoverItem(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [popoverItem]);

  const toggleCollapsed = () => setIsCollapsed((prev) => !prev);

  const toggleMenu = (name) => {
    if (collapsed) {
      setPopoverItem((current) => (current === name ? null : name));
    } else {
      setExpandedMenus((prev) => ({ ...prev, [name]: !prev[name] }));
    }
  };

  const closeSidebar = () => {
    if (open) setOpen(false);
  };

  const visibleItems = dashboardNavigation.filter(
    (item) => !item.roles || item.roles.includes(user?.role),
  );

  const linkClass = (isActive, extra = "") => `
    flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium
    transition-colors cursor-pointer ${extra}
    ${
      isActive
        ? "bg-primary text-primary-foreground"
        : "text-foreground hover:bg-surface-hover"
    }
  `;

  const brandName = siteInfo?.siteName || "FaceCall";

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-background/50 backdrop-blur-sm lg:hidden cursor-pointer"
          onClick={closeSidebar}
        />
      )}

      <aside
        className={`
          h-full bg-surface border-r border-border
          transition-all duration-300 ease-in-out
          flex flex-col shrink-0
          fixed inset-y-0 left-0 z-40
          ${collapsed ? "w-16" : "w-64"}
          ${open ? "translate-x-0" : "-translate-x-full"}
          lg:relative lg:translate-x-0
        `}
      >
        {/* Header */}
        <div className="flex h-16 flex-shrink-0 items-center border-b border-border px-4">
          {!collapsed ? (
            <div className="flex min-w-0 flex-1 items-center overflow-hidden">
              <NavLink
                to={PATHS.home}
                className="flex min-w-0 items-center gap-2"
                onClick={closeSidebar}
              >
                {siteInfo?.siteLogoUrl && (
                  <img
                    src={siteInfo.siteLogoUrl}
                    alt={`${brandName} logo`}
                    className="h-8 w-auto max-w-[100px] flex-shrink-0 object-contain"
                  />
                )}
                <span
                  className="truncate whitespace-nowrap text-sm font-semibold"
                  title={brandName}
                >
                  {brandName}
                </span>
              </NavLink>
            </div>
          ) : (
            <div
              className="min-w-0 flex-1 cursor-pointer self-stretch"
              onClick={toggleCollapsed}
              aria-label="Expand sidebar"
            />
          )}

          <div className="flex flex-shrink-0 items-center gap-2">
            {/* Collapse toggle: desktop only */}
            <button
              className="hidden lg:flex items-center justify-center rounded-md p-1 text-muted-foreground hover:bg-surface-hover cursor-pointer"
              onClick={toggleCollapsed}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? (
                <FiChevronRight className="h-5 w-5" />
              ) : (
                <FiChevronLeft className="h-5 w-5" />
              )}
            </button>

            {/* Close drawer: mobile only */}
            <button
              className="lg:hidden rounded-md p-1 text-muted-foreground hover:bg-surface-hover cursor-pointer"
              onClick={closeSidebar}
              aria-label="Close sidebar"
            >
              <FiX className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto p-3">
          {visibleItems.map((item) => {
            if (item.children) {
              const visibleChildren = item.children.filter(
                (child) => !child.roles || child.roles.includes(user?.role),
              );
              if (visibleChildren.length === 0) return null;

              const isExpanded = !!expandedMenus[item.name];
              const groupActive = hasActiveChild(item, pathname);
              const isPopoverOpen = popoverItem === item.name;
              const rect = isPopoverOpen
                ? buttonRefs.current[item.name]?.getBoundingClientRect()
                : null;

              return (
                <div key={item.name} className="relative space-y-1">
                  <button
                    ref={(el) => (buttonRefs.current[item.name] = el)}
                    onClick={() => toggleMenu(item.name)}
                    className={`
                      flex w-full items-center gap-3 rounded-lg px-3 py-2
                      text-sm font-medium transition-colors cursor-pointer
                      hover:bg-surface-hover
                      ${
                        groupActive
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground"
                      }
                      ${collapsed ? "justify-center px-0" : ""}
                    `}
                    title={collapsed ? item.name : undefined}
                  >
                    <item.icon className="h-5 w-5 flex-shrink-0" />
                    {!collapsed && (
                      <>
                        <span className="flex-1 truncate whitespace-nowrap text-left">
                          {item.name}
                        </span>
                        <FiChevronDown
                          className={`h-4 w-4 transition-transform duration-200 ${
                            isExpanded ? "rotate-180" : ""
                          }`}
                        />
                      </>
                    )}
                  </button>

                  {/* Collapsed: floating submenu */}
                  {collapsed && isPopoverOpen && (
                    <div
                      ref={popoverRef}
                      className="fixed z-50 min-w-[180px] rounded-lg border border-border bg-surface py-1 shadow-lg"
                      style={{
                        left: (rect?.right || 0) + 8,
                        top: rect?.top || 0,
                      }}
                    >
                      {visibleChildren.map((child) => (
                        <NavLink
                          key={child.name}
                          to={child.path}
                          end
                          onClick={() => {
                            setPopoverItem(null);
                            closeSidebar();
                          }}
                          className={({ isActive }) =>
                            linkClass(isActive, "rounded-none px-4")
                          }
                        >
                          {child.icon && (
                            <child.icon className="h-4 w-4 flex-shrink-0" />
                          )}
                          <span className="truncate whitespace-nowrap">
                            {child.name}
                          </span>
                        </NavLink>
                      ))}
                    </div>
                  )}

                  {/* Expanded: inline submenu */}
                  {!collapsed && isExpanded && (
                    <div className="ml-4 mt-1 space-y-1 border-l border-border pl-3">
                      {visibleChildren.map((child) => (
                        <NavLink
                          key={child.name}
                          to={child.path}
                          end
                          onClick={closeSidebar}
                          className={({ isActive }) => linkClass(isActive)}
                        >
                          {child.icon && (
                            <child.icon className="h-5 w-5 flex-shrink-0" />
                          )}
                          <span className="truncate whitespace-nowrap">
                            {child.name}
                          </span>
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              );
            }

            return (
              <NavLink
                key={item.name}
                to={item.path}
                end={item.path === PATHS.home}
                onClick={closeSidebar}
                className={({ isActive }) =>
                  linkClass(isActive, collapsed ? "justify-center px-0" : "")
                }
                title={collapsed ? item.name : undefined}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {!collapsed && (
                  <span className="truncate whitespace-nowrap">
                    {item.name}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Theme */}
        <div className="flex-shrink-0 border-t border-border px-4 py-3">
          <div
            className={`flex items-center ${
              collapsed ? "justify-center" : "justify-between"
            }`}
          >
            {!collapsed && (
              <span className="whitespace-nowrap text-sm text-muted-foreground">
                Theme
              </span>
            )}
            <ThemeToggler />
          </div>
        </div>

        <DashboardUserCard
          user={user}
          collapsed={collapsed}
          onNavigate={closeSidebar}
        />
      </aside>
    </>
  );
}

/* ------------------------------------------------------------- layout */
export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="h-screen flex overflow-hidden bg-background">
      <DashboardSidebar open={sidebarOpen} setOpen={setSidebarOpen} />

      <div className="flex-1 flex flex-col min-w-0">
        <DashboardNav setSidebarOpen={setSidebarOpen} />

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
