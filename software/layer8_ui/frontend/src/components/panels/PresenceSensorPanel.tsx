import { Activity } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { StatusChip } from '@/components/shared/StatusChip';
import { useDashboardStore } from '@/store/dashboardStore';

export function PresenceSensorPanel() {
  const presence = useDashboardStore((state) => state.snapshot.presence);
  const max = Math.max(...presence.timeline);

  return (
    <PanelCard title="Presence Sensor" icon={<Activity className="h-4 w-4" />}>
      <div className="mb-4 flex items-center justify-between gap-4">
        <StatusChip label={presence.detected ? 'PRESENT' : 'NO PRESENCE'} tone={presence.detected ? 'green' : 'slate'} />
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-[0.24em] text-slate-500">Confidence</div>
          <div className="text-2xl font-medium text-white">{Math.round(presence.confidence * 100)}%</div>
        </div>
      </div>
      <div className="flex h-24 items-end gap-1 overflow-hidden rounded-2xl border border-white/10 bg-slate-950 px-3 py-3">
        {presence.timeline.map((value, index) => (
          <div
            key={index}
            className="w-full rounded-full bg-gradient-to-t from-cyan-500/90 via-cyan-300/80 to-emerald-300/70"
            style={{ height: `${(value / max) * 100}%` }}
          />
        ))}
      </div>
      <div className="mt-3 text-xs text-slate-400">Last trigger: {presence.lastTriggerIso}</div>
    </PanelCard>
  );
}
