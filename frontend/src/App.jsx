import { Route, Routes } from "react-router-dom";
import Home from "./pages/public/Home";
import Login from "./pages/public/Login";
import Contact from "./pages/public/Contact.jsx";
import ForgotPassword from "./pages/public/ForgotPassword.jsx";
import ResetPassword from "./pages/public/ResetPassword.jsx";
import AdminDashboard from "./pages/admin/AdminDashboard.jsx";
import ProtectedRoute from "./components/ProtectedPagesWrapper.jsx";
import DashboardLayout from "./components/DashboardLayout.jsx";
import Users from "./pages/admin/Users.jsx";
import UserEdit from "./pages/admin/UserEdit.jsx";
import UserNew from "./pages/admin/UserNew.jsx";
import Sessions from "./pages/admin/Sessions.jsx";
import SessionDetail from "./pages/admin/SessionDetail.jsx";
import LoginViaLink from "./pages/public/LoginViaLink.jsx";
import UserDetail from "./pages/admin/UserDetail.jsx";
import Releases from "./pages/admin/Releases.jsx";
import ReleaseEdit from "./pages/admin/ReleaseEdit.jsx";
import Release from "./pages/public/Release.jsx";
import Profile from "./pages/admin/Profile.jsx";
import ProfileEdit from "./pages/admin/ProfileEdit.jsx";

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password/:code" element={<ResetPassword />} />
      <Route path="/release" element={<Release />} />
      <Route path="/login/:code" element={<LoginViaLink />} />

      <Route element={<ProtectedRoute roles={["admin"]} />}>
        <Route element={<DashboardLayout />}>
          <Route path="/admin/dashboard" element={<AdminDashboard />} />

          <Route path="/admin/users" element={<Users />} />
          <Route path="/admin/users/new" element={<UserNew />} />
          <Route path="/admin/users/:id" element={<UserDetail />} />
          <Route path="/admin/users/:id/edit" element={<UserEdit />} />

          <Route path="/admin/sessions" element={<Sessions />} />
          <Route path="/admin/sessions/:id" element={<SessionDetail />} />

          <Route path="/admin/releases" element={<Releases />} />
          <Route path="/admin/releases/new" element={<ReleaseEdit />} />
          <Route path="/admin/releases/:id" element={<ReleaseEdit />} />
          <Route path="/admin/profile" element={<Profile />} />
          <Route path="/admin/profile/edit" element={<ProfileEdit />} />

          {/* pages still to build
          <Route path="/admin/releases" element={<Releases />} />
          <Route path="/admin/releases/new" element={<ReleaseForm />} />
          <Route path="/admin/releases/:id" element={<ReleaseForm />} />
          <Route path="/admin/settings" element={<SiteSettings />} />
          <Route path="/admin/profile" element={<Profile />} />
          <Route path="/admin/profile/edit" element={<ProfileEdit />} />
          */}
        </Route>
      </Route>
    </Routes>
  );
};

export default App;
