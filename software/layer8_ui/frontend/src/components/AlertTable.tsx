import { useMemo, useState } from "react";

import { ALERT_COLORS, formatTimeIso } from "../lib/utils";
import type { AlertLevel, AlertPayload } from "../types";

export function AlertTable({ alerts, compact = false }: { alerts: AlertPayload[]; compact?: boolean }) {
  const [level, setLevel] = useState<AlertLevel | "ALL">("ALL");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    return alerts.filter((a) => {
      const levelMatch = level === "ALL" || a.level === level;
      const q = query.trim().toLowerCase();
      const searchMatch =
        q.length === 0 ||
        a.message.toLowerCase().includes(q) ||
        a.radar_id.toLowerCase().includes(q) ||
        a.state.toLowerCase().includes(q);
      return levelMatch && searchMatch;
    });
  }, [alerts, level, query]);

  return (
    <section className="panel">
      <h3>Alerts</h3>
      <div className="filters-row">
        <select value={level} onChange={(e) => setLevel(e.target.value as AlertLevel | "ALL")}>
          <option value="ALL">ALL</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ALERT">ALERT</option>
          <option value="FAULT">FAULT</option>
        </select>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search message or radar"
          className="search-input"
        />
      </div>
      <div className={`table-wrap ${compact ? "compact" : ""}`}>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Level</th>
              <th>State</th>
              <th>Radar</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.event_id}>
                <td>{formatTimeIso(item.timestamp_utc)}</td>
                <td>
                  <span className="badge" style={{ backgroundColor: ALERT_COLORS[item.level] }}>
                    {item.level}
                  </span>
                </td>
                <td>{item.state}</td>
                <td>{item.radar_id}</td>
                <td>{item.message}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No alerts matching filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
