import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";
import ToastProvider from "./components/ToastProvider.jsx";
import { BrowserRouter } from "react-router-dom";
import { PageTitleProvider } from "./context/PageTitleContext.jsx";
import { SiteInfoProvider } from "./context/SiteInfoContext.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { GoogleOAuthProvider } from "@react-oauth/google";
import ThemeProvider from "./context/ThemeContext.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <ToastProvider />
      <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
        <AuthProvider>
          <SiteInfoProvider>
            <PageTitleProvider>
              <ThemeProvider>
                <App />
              </ThemeProvider>
            </PageTitleProvider>
          </SiteInfoProvider>
        </AuthProvider>
      </GoogleOAuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
