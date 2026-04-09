import { useMemo, useState } from "react";

export interface ConfirmRequest {
  radarId: string;
  action: "kill_holders" | "usb_reset";
}

export function ControlConfirmModal({
  request,
  onCancel,
  onConfirm,
}: {
  request: ConfirmRequest | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const [typed, setTyped] = useState("");

  const expected = useMemo(() => {
    if (!request) return "";
    return `CONFIRM ${request.radarId}`;
  }, [request]);

  if (!request) return null;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <h3>Confirm Destructive Action</h3>
        <p>
          You are about to run <b>{request.action}</b> on <b>{request.radarId}</b>.
        </p>
        <p>Type exactly: <code>{expected}</code></p>
        <input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={expected} />
        <div className="modal-actions">
          <button className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button className="btn danger" onClick={onConfirm} disabled={typed !== expected}>
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
