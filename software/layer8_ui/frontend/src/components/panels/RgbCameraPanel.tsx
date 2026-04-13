import { Camera, Maximize2 } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';

export function RgbCameraPanel() {
  return (
    <PanelCard title="RGB Camera" icon={<Camera className="h-4 w-4" />} action={<Maximize2 className="h-4 w-4 text-slate-500" />}>
      <div className="overflow-hidden rounded-[1.2rem] border border-white/10 bg-slate-950">
        <div className="aspect-[16/9] bg-[linear-gradient(180deg,rgba(30,41,59,0.25),rgba(15,23,42,0.4)),url('https://images.unsplash.com/photo-1513694203232-719a280e022f?q=80&w=1400&auto=format&fit=crop')] bg-cover bg-center" />
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span>1080p</span>
        <span>|</span>
        <span>30 FPS</span>
        <span>|</span>
        <span>Streaming</span>
        <span>|</span>
        <span>Latency 24 ms</span>
      </div>
    </PanelCard>
  );
}
