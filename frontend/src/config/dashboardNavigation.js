import {
  FiHome,
  FiUsers,
  FiList,
  FiUserPlus,
  FiCalendar,
  FiDownload,
  FiPlus,
  FiUser,
  FiEdit,
  FiSettings,
} from "react-icons/fi";

export const PATHS = {
  home: "/admin/dashboard",
  profile: "/admin/profile",
  profileEdit: "/admin/profile/edit",
};

// Add `roles: ["admin"]` to any item or child to limit it by user.role.
// Items without `roles` are visible to everyone.
const dashboardNavigation = [
  { name: "Dashboard", path: PATHS.home, icon: FiHome },

  {
    name: "Users",
    icon: FiUsers,
    children: [
      { name: "All Users", path: "/admin/users", icon: FiList },
      { name: "Add User", path: "/admin/users/new", icon: FiUserPlus },
    ],
  },

  { name: "Sessions", path: "/admin/sessions", icon: FiCalendar },

  {
    name: "Releases",
    icon: FiDownload,
    children: [
      { name: "All Releases", path: "/admin/releases", icon: FiList },
      { name: "New Release", path: "/admin/releases/new", icon: FiPlus },
    ],
  },

  {
    name: "My Account",
    icon: FiUser,
    children: [
      { name: "View Profile", path: PATHS.profile, icon: FiUser },
      { name: "Edit Profile", path: PATHS.profileEdit, icon: FiEdit },
    ],
  },

  { name: "Site Settings", path: "/admin/settings", icon: FiSettings },
];

export default dashboardNavigation;

// Title for the top bar: the longest nav path that matches the current URL.
export function getPageTitle(pathname) {
  const flat = dashboardNavigation.flatMap((item) =>
    item.children ? item.children : [item],
  );
  let best = null;
  for (const item of flat) {
    const match = pathname === item.path || pathname.startsWith(item.path + "/");
    if (match && (!best || item.path.length > best.path.length)) best = item;
  }
  return best?.name ?? "Dashboard";
}