import { createContext, useContext, useEffect, useState } from "react";

import api from "../lib/axios";

const AuthContext = createContext(null);

const initialUser = {
  id: null,
  isAuthenticated: false,

  firstName: null,
  lastName: null,
  fullName: null,

  dateOfBirth: null,
  gender: null,

  email: null,
  phoneNumber: null,

  profilePicture: null,
  profilePictureUpdatedAt: null,

  dateJoined: null,

  emailVerified: null,
  twoFactorEnabled: null,
  isStaff: null,

  tenant: null,
  isTenantAdmin: false,
};

function formatTenant(tenantData) {
  if (!tenantData) return null;

  return {
    id: tenantData.id,
    name: tenantData.name,
    slug: tenantData.slug,
    isActive: tenantData.is_active,
    createdAt: tenantData.created_at,
  };
}

function formatUser(userData) {
  return {
    id: userData.id,
    isAuthenticated: true,

    firstName: userData.first_name,
    lastName: userData.last_name,
    fullName: `${userData.first_name} ${userData.last_name}`,

    dateOfBirth: userData.date_of_birth,
    gender: userData.gender,

    email: userData.email,
    phoneNumber: userData.phone_number,

    profilePicture: userData.profile_picture,
    profilePictureUpdatedAt: userData.profile_picture_updated_at,

    dateJoined: userData.date_joined,

    emailVerified: userData.email_verified,
    twoFactorEnabled: userData.two_factor_enabled,
    isStaff: userData.is_staff,

    tenant: formatTenant(userData.tenant),
    isTenantAdmin: Boolean(userData.is_tenant_admin),
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(initialUser);
  const [tenant, setTenant] = useState(null);

  const [loading, setLoading] = useState(true);

  const applyUser = (userData) => {
    const formatted = formatUser(userData);
    setUser(formatted);
    setTenant(formatted.tenant);
  };

  const clearUser = () => {
    setUser(initialUser);
    setTenant(null);
  };

  const getUser = async () => {
    setLoading(true);

    try {
      const response = await api.get("/users/me/");

      applyUser(response.data.user);
    } catch (error) {
      clearUser();
      console.log(error.response?.data?.detail);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getUser();
  }, []);

  const login = (userData) => {
    applyUser(userData);

    setLoading(false);
  };

  const updateTenant = (tenantData) => {
    const updated = formatTenant(tenantData);

    setTenant(updated);
    setUser((prev) => ({ ...prev, tenant: updated }));
  };

  const updateProfile = async (payload) => {
    try {
      const response = await api.patch("/users/profile/update/", payload);

      applyUser(response.data.user);
      return { success: true };
    } catch (error) {
      console.error(error.response);
      const is_no_change = error.response?.data?.is_no_change;
      const singleError = is_no_change
        ? "No changes were made."
        : "Faild to update profile.";

      const errorData = error.response?.data?.errors;
      return { success: false, errors: errorData, singleError: singleError };
    }
  };

  const logout = async () => {
    try {
      await api.post("/users/logout/");
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      clearUser();

      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        tenant,
        loading,
        login,
        logout,
        getUser,
        updateProfile,
        updateTenant,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
