import type { AlertPayload, ConsoleMode, HealthResponse, ScorePoint, SensorStatus, StatusPayload, VisualPayload } from "../types";
import { AlertTable } from "../components/AlertTable";
import { GlobalStatusPanel } from "../components/GlobalStatusPanel";
import { ScoreTrendChart } from "../components/ScoreTrendChart";
import { SensorCards, type SensorAction } from "../components/SensorCards";
import { StateTimeline } from "../components/StateTimeline";
import { VisualOpsPanel } from "../components/VisualOpsPanel";

export function DashboardPage({
  status,
  health,
  sensors,
  alerts,
  scoreHistory,
  visual,
  mode,
  onSensorAction,
}: {
  status: StatusPayload;
  health: HealthResponse;
  sensors: SensorStatus[];
  alerts: AlertPayload[];
  scoreHistory: ScorePoint[];
  visual: VisualPayload;
  mode: ConsoleMode;
  onSensorAction: (sensor: SensorStatus, action: SensorAction) => void;
}) {
  return (
    <div className="layout-grid">
      <GlobalStatusPanel status={status} health={health} />
      <VisualOpsPanel visual={visual} />
      <ScoreTrendChart points={scoreHistory} />
      <StateTimeline points={scoreHistory} />
      <SensorCards sensors={sensors} mode={mode} onAction={onSensorAction} />
      <AlertTable alerts={alerts} compact />
    </div>
  );
}
