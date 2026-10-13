import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";
import ToastProvider from "./components/ToastProvider.jsx";
import { BrowserRouter } from "react-router-dom";
import { PageTitleProvider } from "./context/PageTitleContext.jsx";
import { SiteInfoProvider } from "./context/SiteInfoContext.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <PageTitleProvider>
        <ToastProvider />
        <SiteInfoProvider>
          <App />
        </SiteInfoProvider>
      </PageTitleProvider>
    </BrowserRouter>
  </StrictMode>,
);
