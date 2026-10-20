import { createContext, useContext, useEffect, useState } from "react";

const DashboardTitleContext = createContext(null);

export function DashboardTitleProvider({ children }) {
  const [title, setTitle] = useState(null); // null = use route-based title

  return (
    <DashboardTitleContext.Provider value={{ title, setTitle }}>
      {children}
    </DashboardTitleContext.Provider>
  );
}

export function useDashboardTitle() {
  const context = useContext(DashboardTitleContext);
  if (!context) {
    throw new Error(
      "useDashboardTitle must be used inside DashboardTitleProvider",
    );
  }
  return context;
}

// Call from a page to set a custom title; resets on unmount.
export function updateTitle(title) {
  const { setTitle } = useDashboardTitle();

  useEffect(() => {
    setTitle(title);
    return () => setTitle(null);
  }, [title, setTitle]);
}
