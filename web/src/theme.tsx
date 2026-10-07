import { useState } from "react";

// Light is the default: it is the one built for reading a phone in a sunny yard. Dark is an
// opt-in, remembered on this device. index.html applies the saved choice before first paint.

type Theme = "light" | "dark";

const STORAGE_KEY = "scraplink.theme";
const BAR_COLOUR: Record<Theme, string> = { light: "#1c2428", dark: "#0b0f11" };

function current(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function apply(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", BAR_COLOUR[theme]);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Private mode: the choice lasts until the tab closes.
  }
}

/** A switch for the dark top bars (app shell and signed-out pages). */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(current);
  const dark = theme === "dark";
  return (
    <button
      type="button"
      className="theme-toggle"
      aria-pressed={dark}
      onClick={() => {
        const next = dark ? "light" : "dark";
        apply(next);
        setTheme(next);
      }}
    >
      <span className="theme-toggle-label">Dark mode</span>
    </button>
  );
}
