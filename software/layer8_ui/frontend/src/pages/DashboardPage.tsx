import type { AlertPayload, ConsoleMode, HealthResponse, ScorePoint, SensorStatus, StatusPayload } from "../types";
import { AlertTable } from "../components/AlertTable";
import { GlobalStatusPanel } from "../components/GlobalStatusPanel";
import { ScoreTrendChart } from "../components/ScoreTrendChart";
import { SensorCards, type SensorAction } from "../components/SensorCards";
import { StateTimeline } from "../components/StateTimeline";

export function DashboardPage({
  status,
  health,
  sensors,
  alerts,
  scoreHistory,
  mode,
  onSensorAction,
}: {
  status: StatusPayload;
  health: HealthResponse;
  sensors: SensorStatus[];
  alerts: AlertPayload[];
  scoreHistory: ScorePoint[];
  mode: ConsoleMode;
  onSensorAction: (sensor: SensorStatus, action: SensorAction) => void;
}) {
  return (
    <div className="layout-grid">
      <GlobalStatusPanel status={status} health={health} />
      <ScoreTrendChart points={scoreHistory} />
      <StateTimeline points={scoreHistory} />
      <SensorCards sensors={sensors} mode={mode} onAction={onSensorAction} />
      <AlertTable alerts={alerts} compact />
    </div>
  );
}
