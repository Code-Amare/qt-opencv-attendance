import { useEffect, useRef, useState } from "react";
import { FiCheck, FiChevronUp } from "react-icons/fi";
import { useTheme } from "../context/ThemeContext";

function Swatch({ colors }) {
  return (
    <span
      className="h-5 w-5 flex-shrink-0 rounded-full ring-1 ring-border-strong"
      style={{
        background: `linear-gradient(135deg, ${colors[0]} 50%, ${colors[1]} 50%)`,
      }}
    />
  );
}

// placement: "up" (sidebar) or "down" (navbar). align: "left" or "right".
const ThemeToggler = ({ className = "", placement = "up", align = "left" }) => {
  const { theme, setTheme, themes } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKeyDown = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const current = themes.find((t) => t.id === theme) ?? themes[0];

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        title={`Theme: ${current.label}`}
        className="flex items-center gap-2 rounded-lg p-1.5 transition-colors hover:bg-surface-hover cursor-pointer"
      >
        <Swatch colors={current.swatch} />
        <FiChevronUp
          className={`h-4 w-4 text-muted-foreground transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div
          role="menu"
          className={`absolute z-50 w-44 rounded-lg border border-border bg-surface py-1 shadow-lg ${
            placement === "up" ? "bottom-full mb-2" : "top-full mt-2"
          } ${align === "right" ? "right-0" : "left-0"}`}
        >
          {themes.map((t) => (
            <button
              key={t.id}
              type="button"
              role="menuitemradio"
              aria-checked={t.id === theme}
              onClick={() => {
                setTheme(t.id);
                setOpen(false);
              }}
              className={`flex w-full items-center gap-3 px-3 py-2 text-sm transition-colors hover:bg-surface-hover cursor-pointer ${
                t.id === theme ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              <Swatch colors={t.swatch} />
              <span className="flex-1 text-left">{t.label}</span>
              {t.id === theme && <FiCheck className="h-4 w-4 text-primary" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ThemeToggler;
