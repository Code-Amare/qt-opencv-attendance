import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ProtectedRoute = ({ roles = [] }) => {
  const { user, loading } = useAuth();
  let userRole = "";
  if (user.isStaff) {
    userRole = "admin";
  } else {
    userRole = "user";
  }

  if (loading) return <h1>Loading...</h1>;

  if (!user || !user.isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!roles.includes(userRole)) {
    return (
      <Navigate to={`/unauthorized?allowed_for=${roles.join(",")}`} replace />
    );
  }

  return <Outlet />;
};

export default ProtectedRoute;
