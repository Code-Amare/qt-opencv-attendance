import { Toaster } from "react-hot-toast";

export default function ToastProvider() {
  return (
    <Toaster
      position="top-center"
      toastOptions={{
        duration: 3000,

        style: {
          background: "var(--surface)",
          color: "var(--foreground)",
          border: "1px solid var(--border)",
          boxShadow: "0 10px 25px rgba(0,0,0,0.15)",
        },

        success: {
          iconTheme: {
            primary: "var(--success)",
            secondary: "var(--surface)",
          },

          style: {
            border: "1px solid var(--success)",
          },
        },

        error: {
          iconTheme: {
            primary: "var(--danger)",
            secondary: "var(--surface)",
          },

          style: {
            border: "1px solid var(--danger)",
          },
        },

        loading: {
          iconTheme: {
            primary: "var(--primary)",
            secondary: "var(--surface)",
          },

          style: {
            border: "1px solid var(--primary)",
          },
        },
      }}
    />
  );
}
