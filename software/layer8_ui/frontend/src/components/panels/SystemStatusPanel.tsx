import { Cpu } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { MetricPill } from '@/components/shared/MetricPill';
import { StatusChip } from '@/components/shared/StatusChip';
import { useDashboardStore } from '@/store/dashboardStore';

export function SystemStatusPanel() {
  const { health, state } = useDashboardStore((store) => store.snapshot);

  return (
    <PanelCard title="System Status" icon={<Cpu className="h-4 w-4" />}>
      <div className="mb-4 flex flex-wrap gap-2">
        <StatusChip label="Connected" tone={health.connected ? 'green' : 'red'} />
        <StatusChip label="Configured" tone={health.configured ? 'green' : 'red'} />
        <StatusChip label="Streaming" tone={health.streaming ? 'cyan' : 'red'} />
        <StatusChip label={state} tone={state === 'SCANNING' ? 'amber' : state === 'FAULT' ? 'red' : 'slate'} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <MetricPill label="Active sensors" value={`${health.activeSensors}/${health.sensorCount}`} />
        <MetricPill label="Fused score" value={`${Math.round(health.fusedScore * 100)}%`} />
        <MetricPill label="Confidence" value={`${Math.round(health.confidence * 100)}%`} />
        <MetricPill label="Health" value={health.healthy ? 'Operational' : 'Fault'} />
      </div>
    </PanelCard>
  );
}
