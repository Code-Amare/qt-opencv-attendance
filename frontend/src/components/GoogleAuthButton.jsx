import { useGoogleLogin } from "@react-oauth/google";
import { FcGoogle } from "react-icons/fc";
import api from "../lib/axios";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "react-hot-toast";

const GoogleAuthButton = ({ nextPage = "/admin" }) => {
  const navigate = useNavigate();
  const { user, getUser } = useAuth();

  const google_auth = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      const toastId = toast.loading("Signing you in...");

      try {
        const response = await api.post("/users/auth/google/", {
          token: tokenResponse.access_token,
        });

        const user = response.data?.user;

        if (!user) {
          throw new Error("No user returned from the server.");
        }

        getUser();

        toast.success("Welcome back!", {
          id: toastId,
        });

        isAdmin = user.isStaff;
        if (isAdmin) {
          navigate("admin/dashboard", { replace: true });
        } else {
          navigate("dashboard", { replace: true });
        }
      } catch (error) {
        console.error("Google auth failed:", error);

        toast.error(
          error.response?.data?.error ||
            error.response?.data?.detail ||
            error.message ||
            "Google auth failed.",
          {
            id: toastId,
          },
        );
      }
    },

    onError: () => {
      toast.error("Google sign in was cancelled.");
    },
  });

  return (
    <button
      type="button"
      onClick={() => google_auth()}
      className="
                cursor-pointer
                w-full
                flex
                items-center
                justify-center
                gap-3
                rounded-lg
                border
                border-gray-300
                bg-white
                px-5
                py-3
                text-sm
                font-medium
                text-gray-700
                shadow-sm
                transition
                hover:bg-gray-50
                active:scale-[0.98]
            "
    >
      <FcGoogle size={22} />
      Continue with Google
    </button>
  );
};

export default GoogleAuthButton;
