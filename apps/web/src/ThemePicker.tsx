import { useEffect, useState } from "react";
import { Icon } from "./Icon";

type Preference = "system" | "light" | "dark";
const key = "sentinel-theme";
function storedPreference(): Preference {
  try {
    const value = localStorage.getItem(key);
    if (value === "light" || value === "dark") return value;
  } catch {
    /* Theme controls remain usable when storage is unavailable. */
  }
  return "system";
}

export function ThemePicker() {
  const [preference, setPreference] = useState<Preference>(storedPreference);
  const [dark, setDark] = useState(
    document.documentElement.dataset.theme === "dark",
  );
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const isDark =
        preference === "dark" || (preference === "system" && media.matches);
      document.documentElement.dataset.theme = isDark ? "dark" : "light";
      setDark(isDark);
    };
    const sync = (event: StorageEvent) => {
      if (event.key === key || event.key === null)
        setPreference(storedPreference());
    };
    apply();
    media.addEventListener("change", apply);
    window.addEventListener("storage", sync);
    return () => {
      media.removeEventListener("change", apply);
      window.removeEventListener("storage", sync);
    };
  }, [preference]);
  return (
    <label className="theme-picker">
      <Icon name={dark ? "moon" : "sun"} />
      <span className="sr-only">Color theme</span>
      <select
        aria-label="Color theme"
        value={preference}
        onChange={(event) => {
          const value = event.target.value as Preference;
          setPreference(value);
          try {
            if (value === "system") localStorage.removeItem(key);
            else localStorage.setItem(key, value);
          } catch {
            /* The selection still applies for the current page. */
          }
        }}
      >
        <option value="system">Device theme</option>
        <option value="light">Light mode</option>
        <option value="dark">Dark mode</option>
      </select>
    </label>
  );
}
