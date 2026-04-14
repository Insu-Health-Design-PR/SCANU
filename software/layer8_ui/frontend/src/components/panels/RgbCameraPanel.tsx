import { Camera, Maximize2 } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { StatusChip } from '@/components/shared/StatusChip';
import { useDashboardStore } from '@/store/dashboardStore';

export function RgbCameraPanel() {
  const rgb = useDashboardStore((state) => state.snapshot.rgb);
  const imageSrc = rgb.frameBase64 ? `data:image/jpeg;base64,${rgb.frameBase64}` : null;

  return (
    <PanelCard title="RGB Camera" icon={<Camera className="h-4 w-4" />} action={<Maximize2 className="h-4 w-4 text-slate-500" />}>
      <div className="mb-3 flex flex-wrap gap-2">
        <StatusChip label={imageSrc ? 'Live Feed' : 'No Feed'} tone={imageSrc ? 'cyan' : 'amber'} />
        {rgb.stale ? <StatusChip label="Stale" tone="red" /> : null}
      </div>
      <div className="overflow-hidden rounded-[1.2rem] border border-white/10 bg-slate-950">
        {imageSrc ? (
          <img src={imageSrc} alt="RGB stream" className="aspect-[16/9] w-full object-cover" />
        ) : (
          <div className="flex aspect-[16/9] items-center justify-center bg-slate-950 text-sm text-slate-400">No RGB frame from backend</div>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span>{rgb.resolution}</span>
        <span>|</span>
        <span>{rgb.fps} FPS</span>
        <span>|</span>
        <span>{rgb.status}</span>
        <span>|</span>
        <span>Latency {rgb.latencyMs} ms</span>
      </div>
    </PanelCard>
  );
}
