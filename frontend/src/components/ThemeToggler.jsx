import { useEffect, useState } from "react";
import { useTheme } from "../context/ThemeContext";

const ThemeToggler = ({ className }) => {
  const { theme, themeToggle } = useTheme();

  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className={className}>
      <label className="relative inline-flex h-8 w-14 cursor-pointer items-center scale-80">
        <input
          type="checkbox"
          checked={theme == "dark"}
          onChange={themeToggle}
          className="peer sr-only"
        />

        {/* Track */}
        <div
          className="
          h-full w-full rounded-full
          bg-zinc-300
          transition-colors duration-300
          peer-checked:bg-zinc-700
        "
        />

        {/* Thumb */}
        <div
          className={`
          absolute left-1
          h-6 w-6
          rounded-full
          
          bg-[linear-gradient(40deg,#ff0080,#ff8c00_70%)]
          
          ${mounted ? "transition-all duration-300" : ""}

          peer-checked:left-7
          peer-checked:bg-zinc-800

          peer-checked:shadow-[inset_-3px_-2px_5px_-2px_#8983f7,inset_-10px_-4px_0_0_#a3dafb]
        `}
        />
      </label>
    </div>
  );
};

export default ThemeToggler;
