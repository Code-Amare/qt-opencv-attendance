import {
  FiHome,
  FiBriefcase,
  FiList,
  FiPlus,
  FiDownload,
  FiUser,
  FiEdit,
  FiSettings,
} from "react-icons/fi";

export const PATHS = {
  home: "/admin/dashboard",
  profile: "/admin/profile",
  profileEdit: "/admin/profile/edit",
};

const adminDashboardNavigation = [
  { name: "Dashboard", path: PATHS.home, icon: FiHome },

  { name: "Tenants", path: "/admin/tenants", icon: FiBriefcase },

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

export default adminDashboardNavigation;

export function getPageTitle(pathname) {
  const flat = adminDashboardNavigation.flatMap((item) =>
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