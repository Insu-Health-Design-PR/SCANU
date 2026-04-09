import type { ConsoleMode } from "../types";

const MODES: ConsoleMode[] = ["monitor", "control", "maintenance"];

export function ModeSelector({ mode, onChange }: { mode: ConsoleMode; onChange: (m: ConsoleMode) => void }) {
  return (
    <div className="mode-selector" role="radiogroup" aria-label="Operator mode">
      {MODES.map((candidate) => (
        <button
          key={candidate}
          className={`mode-btn ${mode === candidate ? "active" : ""}`}
          onClick={() => onChange(candidate)}
          role="radio"
          aria-checked={mode === candidate}
        >
          {candidate}
        </button>
      ))}
    </div>
  );
}
