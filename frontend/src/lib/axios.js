import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/";

// Only for dev

const hostname = window.location.hostname;

const isWifiNetwork = hostname.startsWith("192");

// const API_BASE_URL = isWifiNetwork
//   ? import.meta.env.VITE_API_URL_WIFI
//   : import.meta.env.VITE_API_URL || "/";

// dev end here

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);

    if (parts.length === 2) {
        return parts.pop().split(";").shift();
    }

    return null;
}

const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
});

// Normal axios instance (no interceptors)
const refreshApi = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
});

api.interceptors.request.use(
    (config) => {
        if (
            config.method &&
            !["get", "head", "options"].includes(
                config.method.toLowerCase()
            )
        ) {
            const csrfToken = getCookie("csrftoken");

            if (csrfToken) {
                config.headers["X-CSRFToken"] =
                    decodeURIComponent(csrfToken);
            }
        }

        return config;
    },
    (error) => Promise.reject(error)
);

api.interceptors.response.use(
    (response) => response,

    async (error) => {
        const originalRequest = error.config;

        if (!originalRequest) {
            return Promise.reject(error);
        }

        // Skip automatic token refresh for this request if requested
        if (originalRequest.skipAuthRefresh) {
            return Promise.reject(error);
        }

        const refreshRequired = error.response?.status === 401;

        // Only attempt refresh once
        if (
            refreshRequired &&
            !originalRequest._retry
        ) {
            originalRequest._retry = true;

            try {
                await refreshApi.post("/users/token/refresh/");

                // Retry the original request once
                return api(originalRequest);

            } catch (refreshError) {
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

export default api;