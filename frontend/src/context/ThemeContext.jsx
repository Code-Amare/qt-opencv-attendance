import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

// `swatch` = [background, accent], only used for the picker preview dots.
export const THEMES = [
  { id: "light", label: "Light", dark: false, swatch: ["#F6F6F9", "#5B21B6"] },
  { id: "dark", label: "Dark", dark: true, swatch: ["#121215", "#5B21B6"] },
  {
    id: "midnight",
    label: "Midnight",
    dark: true,
    swatch: ["#0B1020", "#2563EB"],
  },
  { id: "forest", label: "Forest", dark: true, swatch: ["#0E1512", "#059669"] },
  { id: "rose", label: "Rose", dark: false, swatch: ["#FBF3F4", "#BE123C"] },
];

const STORAGE_KEY = "theme";
const isValid = (id) => THEMES.some((t) => t.id === id);

function getInitialTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (isValid(stored)) return stored;
  } catch {
    /* storage unavailable */
  }
  // First visit: follow the OS. Change "dark" to force one default.
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

const ThemeContext = createContext(null);

const ThemeProvider = ({ children }) => {
  const [theme, setThemeState] = useState(getInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    const meta = THEMES.find((t) => t.id === theme);

    root.dataset.theme = theme;
    root.classList.toggle("dark", !!meta?.dark);

    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* storage unavailable */
    }
  }, [theme]);

  const setTheme = useCallback((id) => {
    if (isValid(id)) setThemeState(id);
  }, []);

  // Kept for old code: flips between a light and a dark theme.
  const themeToggle = useCallback(() => {
    setThemeState((current) =>
      THEMES.find((t) => t.id === current)?.dark ? "light" : "dark",
    );
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, themeToggle, themes: THEMES }),
    [theme, setTheme, themeToggle],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
};

export function useTheme() {
  return useContext(ThemeContext);
}

export default ThemeProvider;
