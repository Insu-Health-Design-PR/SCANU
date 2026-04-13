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
        <StatusChip label={rgb.source === 'live' ? 'Live Feed' : 'Fallback'} tone={rgb.source === 'live' ? 'cyan' : 'amber'} />
        {rgb.stale ? <StatusChip label="Stale" tone="red" /> : null}
      </div>
      <div className="overflow-hidden rounded-[1.2rem] border border-white/10 bg-slate-950">
        {imageSrc ? (
          <img src={imageSrc} alt="RGB stream" className="aspect-[16/9] w-full object-cover" />
        ) : (
          <div className="aspect-[16/9] bg-[linear-gradient(180deg,rgba(30,41,59,0.25),rgba(15,23,42,0.4)),url('https://images.unsplash.com/photo-1513694203232-719a280e022f?q=80&w=1400&auto=format&fit=crop')] bg-cover bg-center" />
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
