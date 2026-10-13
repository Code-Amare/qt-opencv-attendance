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
  role: null,
};

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
    role: userData.role,
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(initialUser);

  const [loading, setLoading] = useState(true);

  const getUser = async () => {
    setLoading(true);

    try {
      const response = await api.get("/accounts/me/");

      const userData = response.data.user;

      setUser(formatUser(userData));
    } catch (error) {
      setUser(initialUser);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getUser();
  }, []);

  const login = (userData) => {
    setUser(formatUser(userData));

    setLoading(false);
  };

  const updateProfile = async (payload) => {
    try {
      // payload = { first_name, last_name, phone_number, date_of_birth, gender }
      const response = await api.patch("/accounts/profile/update/", payload);
      const updatedUser = response.data.user; // as per your response

      // Update the user state with the new data
      setUser(formatUser(updatedUser));
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
      await api.post("/accounts/logout/");
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      setUser(initialUser);

      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        getUser,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
