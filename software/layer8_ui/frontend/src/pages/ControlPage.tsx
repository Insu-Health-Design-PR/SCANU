import { useState } from "react";

import type { ConsoleMode, ControlResult, SensorStatus } from "../types";
import { ControlConfirmModal, type ConfirmRequest } from "../components/ControlConfirmModal";
import { ControlLogPanel } from "../components/ControlLogPanel";
import { SensorCards, type SensorAction } from "../components/SensorCards";

export function ControlPage({
  mode,
  sensors,
  results,
  onAction,
}: {
  mode: ConsoleMode;
  sensors: SensorStatus[];
  results: ControlResult[];
  onAction: (sensor: SensorStatus, action: SensorAction, payload?: { config_path?: string; config_text?: string }) => Promise<void>;
}) {
  const [configPath, setConfigPath] = useState("");
  const [configText, setConfigText] = useState("");
  const [pendingConfirm, setPendingConfirm] = useState<ConfirmRequest | null>(null);
  const [pendingSensor, setPendingSensor] = useState<SensorStatus | null>(null);

  const handleSensorAction = async (sensor: SensorStatus, action: SensorAction) => {
    if (action === "kill_holders" || action === "usb_reset") {
      setPendingSensor(sensor);
      setPendingConfirm({ radarId: sensor.radar_id, action });
      return;
    }

    if (action === "reconfig") {
      await onAction(sensor, action, {
        config_path: configPath || undefined,
        config_text: configText || undefined,
      });
      return;
    }

    await onAction(sensor, action);
  };

  const onConfirm = async () => {
    if (!pendingConfirm || !pendingSensor) return;
    await onAction(pendingSensor, pendingConfirm.action);
    setPendingConfirm(null);
    setPendingSensor(null);
  };

  return (
    <div className="layout-grid">
      <section className="panel">
        <h3>Control Inputs</h3>
        <p className="muted">Mode: <b>{mode}</b>. Destructive actions require Maintenance mode and explicit confirmation.</p>
        <div className="control-form-grid">
          <label>
            Config Path
            <input value={configPath} onChange={(e) => setConfigPath(e.target.value)} placeholder="software/layer1_sensor_hub/...cfg" />
          </label>
          <label>
            Config Text (optional)
            <textarea value={configText} onChange={(e) => setConfigText(e.target.value)} placeholder="sensorStop\nflushCfg\n..." />
          </label>
        </div>
      </section>

      <SensorCards sensors={sensors} mode={mode} onAction={handleSensorAction} />
      <ControlLogPanel results={results} />

      <ControlConfirmModal
        request={pendingConfirm}
        onCancel={() => {
          setPendingConfirm(null);
          setPendingSensor(null);
        }}
        onConfirm={async () => {
          await onConfirm();
        }}
      />
    </div>
  );
}
