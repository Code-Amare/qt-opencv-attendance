import { Route, Routes } from "react-router-dom";
import Home from "./pages/public/Home";
import Login from "./pages/public/Login";
import Register from "./pages/public/Register";
import Contact from "./pages/public/Contact.jsx";
import ForgotPassword from "./pages/public/ForgotPassword.jsx";
import ResetPassword from "./pages/public/ResetPassword.jsx";
import LoginViaLink from "./pages/public/LoginViaLink.jsx";
import Release from "./pages/public/Release.jsx";
import ProtectedRoute from "./components/ProtectedPagesWrapper.jsx";
import TenantRoute from "./components/TenantRoute.jsx";
import DashboardLayout from "./components/DashboardLayout.jsx";
import SuperAdminDashboard from "./pages/admin/AdminDashboard.jsx";
import Tenants from "./pages/admin/Tenants.jsx";
import TenantDetail from "./pages/admin/TenantDetail.jsx";
import Releases from "./pages/admin/Releases.jsx";
import ReleaseEdit from "./pages/admin/ReleaseEdit.jsx";
import Profile from "./pages/common/Profile.jsx";
import ProfileEdit from "./pages/common/ProfileEdit.jsx";
import TenantAdminDashboard from "./pages/tenant/TenantDashboard.jsx";
import Sessions from "./pages/tenant/Sessions.jsx";
import SessionDetail from "./pages/tenant/SessionDetail.jsx";
import Users from "./pages/tenant/Users.jsx";
import UserNew from "./pages/tenant/UserNew.jsx";
import UserDetail from "./pages/tenant/UserDetail.jsx";
import UserEdit from "./pages/tenant/UserEdit.jsx";
import MemberDashboard from "./pages/user/MemberDashboard.jsx";
import SessionNew from "./pages/tenant/SessionNew.jsx";

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password/:code" element={<ResetPassword />} />
      <Route path="/release" element={<Release />} />
      <Route path="/login/:code" element={<LoginViaLink />} />

      <Route element={<TenantRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/:slug/dashboard" element={<MemberDashboard />} />
          <Route path="/:slug/profile" element={<Profile />} />
          <Route path="/:slug/profile/edit" element={<ProfileEdit />} />
        </Route>
      </Route>

      <Route element={<TenantRoute adminOnly />}>
        <Route element={<DashboardLayout />}>
          <Route
            path="/:slug/admin/dashboard"
            element={<TenantAdminDashboard />}
          />
          <Route path="/:slug/admin/profile" element={<Profile />} />
          <Route path="/:slug/admin/profile/edit" element={<ProfileEdit />} />

          <Route path="/:slug/admin/users" element={<Users />} />
          <Route path="/:slug/admin/users/new" element={<UserNew />} />
          <Route path="/:slug/admin/users/:id" element={<UserDetail />} />
          <Route path="/:slug/admin/users/:id/edit" element={<UserEdit />} />

          <Route path="/:slug/admin/sessions" element={<Sessions />} />
          <Route path="/:slug/admin/sessions/:id" element={<SessionDetail />} />

          <Route path="/:slug/admin/sessions" element={<Sessions />} />
          <Route path="/:slug/admin/sessions/new" element={<SessionNew />} />
          <Route path="/:slug/admin/sessions/:id" element={<SessionDetail />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={["admin"]} />}>
        <Route element={<DashboardLayout />}>
          <Route path="/admin/dashboard" element={<SuperAdminDashboard />} />

          <Route path="/admin/tenants" element={<Tenants />} />
          <Route path="/admin/tenants/:id" element={<TenantDetail />} />

          <Route path="/admin/releases" element={<Releases />} />
          <Route path="/admin/releases/new" element={<ReleaseEdit />} />
          <Route path="/admin/releases/:id" element={<ReleaseEdit />} />

          <Route path="/admin/profile" element={<Profile />} />
          <Route path="/admin/profile/edit" element={<ProfileEdit />} />
        </Route>
      </Route>
    </Routes>
  );
};

export default App;
