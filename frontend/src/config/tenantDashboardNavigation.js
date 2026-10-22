import {
  FiHome,
  FiUsers,
  FiList,
  FiUserPlus,
  FiCalendar,
  FiPlus,
  FiUser,
  FiEdit,
  FiSettings,
} from "react-icons/fi";

export const getTenantPaths = (slug) => {
  const base = `/${slug}/admin`;
  return {
    base,
    home: `${base}/dashboard`,
    users: `${base}/users`,
    usersNew: `${base}/users/new`,
    user: (id) => `${base}/users/${id}`,
    userEdit: (id) => `${base}/users/${id}/edit`,
    sessions: `${base}/sessions`,
    sessionsNew: `${base}/sessions/new`,
    session: (id) => `${base}/sessions/${id}`,
    profile: `${base}/profile`,
    profileEdit: `${base}/profile/edit`,
    settings: `${base}/settings`,
  };
};

export const tenantDashboardNavigation = (slug) => {
  const paths = getTenantPaths(slug);

  return [
    { name: "Dashboard", path: paths.home, icon: FiHome },

    {
      name: "Users",
      icon: FiUsers,
      children: [
        { name: "All Users", path: paths.users, icon: FiList },
        { name: "Add User", path: paths.usersNew, icon: FiUserPlus },
      ],
    },

    {
      name: "Sessions",
      icon: FiCalendar,
      children: [
        { name: "All Sessions", path: paths.sessions, icon: FiList },
        { name: "New Session", path: paths.sessionsNew, icon: FiPlus },
      ],
    },

    {
      name: "My Account",
      icon: FiUser,
      children: [
        { name: "View Profile", path: paths.profile, icon: FiUser },
        { name: "Edit Profile", path: paths.profileEdit, icon: FiEdit },
      ],
    },

    { name: "Organization", path: paths.settings, icon: FiSettings },
  ];
};

export function getTenantPageTitle(pathname, slug) {
  const flat = tenantDashboardNavigation(slug).flatMap((item) =>
    item.children ? item.children : [item],
  );
  let best = null;
  for (const item of flat) {
    const match =
      pathname === item.path || pathname.startsWith(item.path + "/");
    if (match && (!best || item.path.length > best.path.length)) best = item;
  }
  return best?.name ?? "Dashboard";
}