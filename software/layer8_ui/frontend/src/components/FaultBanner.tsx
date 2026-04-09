import type { SensorFaultPayload } from "../types";

export function FaultBanner({ payload }: { payload: SensorFaultPayload | null }) {
  if (!payload) return null;

  return (
    <section className="fault-banner" role="alert">
      <div>
        <strong>Sensor Fault</strong>
        <span> fault_code: {payload.fault_code ?? "unknown"} </span>
        <span> radars: {payload.radars.join(", ") || "-"} </span>
      </div>
      {payload.action_request ? (
        <div className="fault-hint">
          <b>Suggested action:</b> {payload.action_request.action} ({payload.action_request.reason})
          {payload.action_request.manual_required ? " [manual]" : ""}
        </div>
      ) : null}
    </section>
  );
}
