import { Maximize2, Thermometer } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { StatusChip } from '@/components/shared/StatusChip';
import { useDashboardStore } from '@/store/dashboardStore';

export function ThermalCameraPanel() {
  const thermal = useDashboardStore((state) => state.snapshot.thermal);
  const imageSrc = thermal.frameBase64 ? `data:image/jpeg;base64,${thermal.frameBase64}` : null;

  return (
    <PanelCard title="Thermal Camera" icon={<Thermometer className="h-4 w-4" />} action={<Maximize2 className="h-4 w-4 text-slate-500" />}>
      <div className="mb-3 flex flex-wrap gap-2">
        <StatusChip label={imageSrc ? 'Live Feed' : 'No Feed'} tone={imageSrc ? 'cyan' : 'amber'} />
        {thermal.stale ? <StatusChip label="Stale" tone="red" /> : null}
      </div>
      <div className="overflow-hidden rounded-[1.2rem] border border-orange-400/10 bg-slate-950">
        {imageSrc ? (
          <img src={imageSrc} alt="Thermal stream" className="aspect-[16/9] w-full object-cover" />
        ) : (
          <div className="flex aspect-[16/9] items-center justify-center bg-slate-950 text-sm text-slate-400">No thermal frame from backend</div>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span>Thermal</span>
        <span>|</span>
        <span>{thermal.fps} FPS</span>
        <span>|</span>
        <span>{thermal.status}</span>
        <span>|</span>
        <span>Latency {thermal.latencyMs} ms</span>
      </div>
    </PanelCard>
  );
}
