import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ProtectedRoute = ({ roles = [] }) => {
  const { user, loading } = useAuth();

  if (loading) return <h1>Loading...</h1>;

  if (!user || !user.isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (roles.length > 0 && !roles.includes(user.role)) {
    return (
      <Navigate to={`/unauthorized?allowed_for=${roles.join(",")}`} replace />
    );
  }

  return <Outlet />;
};

export default ProtectedRoute;
