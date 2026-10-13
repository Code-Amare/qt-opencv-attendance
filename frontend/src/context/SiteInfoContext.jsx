import { createContext, useContext, useEffect, useState } from "react";

import api from "../lib/axios";

const SiteInfoContext = createContext(null);

const initialSiteInfo = {
  siteName: "None",
  siteLogoUrl: null,
};

export function SiteInfoProvider({ children }) {
  const [siteInfo, setSiteInfo] = useState(initialSiteInfo);

  useEffect(() => {
    if (siteInfo.siteLogoUrl) {
      const favicon = document.querySelector("link[rel='icon']");

      if (favicon) {
        favicon.href = siteInfo.siteLogoUrl;
      } else {
        const link = document.createElement("link");
        link.rel = "icon";
        link.href = siteInfo.siteLogoUrl;
        document.head.appendChild(link);
      }
    }
  }, [siteInfo.siteLogoUrl]);

  const getSiteInfo = async () => {
    try {
      const response = await api.get("/site/");

      const siteData = response.data.site;

      setSiteInfo({
        siteName: siteData.site_name,
        siteLogoUrl: siteData.site_logo,
      });
    } catch (error) {
      setSiteInfo({
        siteName: null,
        siteLogoUrl: null,
      });
    }
  };

  useEffect(() => {
    getSiteInfo();
  }, []);

  return (
    <SiteInfoContext.Provider
      value={{
        siteInfo,
        getSiteInfo,
      }}
    >
      {children}
    </SiteInfoContext.Provider>
  );
}

export function useSiteInfo() {
  return useContext(SiteInfoContext);
}
