import { Navigate, Outlet, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const TenantRoute = ({ adminOnly = false }) => {
  const { slug } = useParams();
  const { user, tenant, loading } = useAuth();

  if (loading) return <h1>Loading...</h1>;

  if (!user.isAuthenticated || !tenant) {
    return <Navigate to="/login" replace />;
  }

  if (tenant.slug !== slug) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && !user.isTenantAdmin) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

export default TenantRoute;
