import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { useSiteInfo } from "./SiteInfoContext";

const PageTitleContext = createContext(null);

export function PageTitleProvider({ children }) {
  const { siteInfo } = useSiteInfo();
  const [pageTitle, setPageTitle] = useState(null); // null = fall back to site name

  const updatePageTitle = useCallback((title) => {
    setPageTitle(title);
  }, []);

  useEffect(() => {
    document.title = pageTitle || siteInfo?.siteName || "Website";
  }, [pageTitle, siteInfo]);

  return (
    <PageTitleContext.Provider value={{ pageTitle, updatePageTitle }}>
      {children}
    </PageTitleContext.Provider>
  );
}

export function usePageTitle() {
  const context = useContext(PageTitleContext);
  if (!context) {
    throw new Error("usePageTitle must be used inside PageTitleProvider");
  }
  return context;
}

// Call from a page to set the browser tab title; resets on unmount.
export function useUpdatePageTitle(title) {
  const { updatePageTitle } = usePageTitle();

  useEffect(() => {
    updatePageTitle(title);
    return () => updatePageTitle(null);
  }, [title, updatePageTitle]);
}
