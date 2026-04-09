import type { AlertPayload } from "../types";
import { AlertTable } from "../components/AlertTable";

export function EventsPage({ alerts }: { alerts: AlertPayload[] }) {
  const exportJson = () => {
    const blob = new Blob([JSON.stringify(alerts, null, 2)], { type: "application/json" });
    const href = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = href;
    a.download = `layer8-alerts-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(href);
  };

  return (
    <div className="layout-grid">
      <section className="panel">
        <h3>Event History</h3>
        <div className="toolbar-inline">
          <button className="btn" onClick={exportJson}>
            Export JSON
          </button>
        </div>
      </section>
      <AlertTable alerts={alerts} />
    </div>
  );
}
