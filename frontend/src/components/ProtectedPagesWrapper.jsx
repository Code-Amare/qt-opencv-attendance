import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default ProtectedRoute = ({ role = [] }) => {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  if (loading) {
    return <h1>Loading...</h1>;
  }

  if (!user || !user.isAuthenticated) {
    return navigate("/login");
  }

  if (roles.length > 0 && !roles.includes(user.role)) {
    return (
      <Navigate to={`/unauthorized?allowed_for=${roles.join(",")}`} replace />
    );
  }

  return <Outlet />;
};
