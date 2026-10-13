import { createContext, useContext, useEffect, useState } from "react";

import { useSiteInfo } from "./SiteInfoContext";

const PageTitleContext = createContext(null);

export function PageTitleProvider({ children }) {
  const { siteInfo } = useSiteInfo();

  const [pageTitle, setPageTitle] = useState(null);

  const updatePageTitle = (title) => {
    setPageTitle(title);
  };

  useEffect(() => {
    document.title = pageTitle || siteInfo.siteName || "Website";
  }, [pageTitle, siteInfo]);

  return (
    <PageTitleContext.Provider
      value={{
        pageTitle,
        updatePageTitle,
      }}
    >
      {children}
    </PageTitleContext.Provider>
  );
}

export function usePageTitle() {
  return useContext(PageTitleContext);
}
