import { useEffect } from "react";

interface ShortcutHandlers {
  refresh: () => void;
  goDashboard: () => void;
  goControl: () => void;
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers): void {
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const target = ev.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;

      if (ev.key === "r") {
        ev.preventDefault();
        handlers.refresh();
      }
      if (ev.key === "g") {
        ev.preventDefault();
        handlers.goDashboard();
      }
      if (ev.key === "c") {
        ev.preventDefault();
        handlers.goControl();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handlers]);
}
