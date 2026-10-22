import {
  FiHome,
  FiUsers,
  FiList,
  FiUserPlus,
  FiCalendar,
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
    sessions: `${base}/sessions`,
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

    { name: "Sessions", path: paths.sessions, icon: FiCalendar },

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
