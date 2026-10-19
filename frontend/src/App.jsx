import { Route, Routes } from "react-router-dom";
import Home from "./pages/public/Home";
import Login from "./pages/public/Login";
import Contact from "./pages/public/Contact.jsx";
import ForgotPassword from "./pages/public/ForgotPassword.jsx";
import ResetPassword from "./pages/public/ResetPassword.jsx";
import AdminDashboard from "./pages/admin/AdminDashboard.jsx";
import ProtectedRoute from "./components/ProtectedPagesWrapper.jsx";
import Users from "./pages/admin/Users.jsx";
import UserEdit from "./pages/admin/UserEdit.jsx";
import UserNew from "./pages/admin/UserNew.jsx";
import Sessions from "./pages/admin/Sessions.jsx";
import SessionDetail from "./pages/admin/SessionDetail.jsx";
import LoginViaLink from "./pages/public/LoginViaLink.jsx";

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password/:code" element={<ResetPassword />} />
      <Route path="/login/:code" element={<LoginViaLink />} />

      <Route element={<ProtectedRoute roles={["admin"]} />}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<Users />} />
        <Route path="/admin/users/:id" element={<UserEdit />} />
        <Route path="/admin/users/new" element={<UserNew />} />
        <Route path="/admin/sessions" element={<Sessions />} />
        <Route path="/admin/sessions/:id" element={<SessionDetail />} />
      </Route>
    </Routes>
  );
};

export default App;
