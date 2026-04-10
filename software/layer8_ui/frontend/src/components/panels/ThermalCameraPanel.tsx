import { Maximize2, Thermometer } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';

export function ThermalCameraPanel() {
  return (
    <PanelCard title="Thermal Camera" icon={<Thermometer className="h-4 w-4" />} action={<Maximize2 className="h-4 w-4 text-slate-500" />}>
      <div className="overflow-hidden rounded-[1.2rem] border border-orange-400/10 bg-slate-950">
        <div className="aspect-[16/9] bg-[radial-gradient(circle_at_20%_15%,rgba(255,205,86,0.92),transparent_20%),radial-gradient(circle_at_74%_18%,rgba(255,94,58,0.9),transparent_25%),radial-gradient(circle_at_52%_70%,rgba(149,76,233,0.85),transparent_30%),linear-gradient(135deg,#f59e0b_0%,#f97316_16%,#ec4899_42%,#7c3aed_72%,#111827_100%)] opacity-95" />
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span>Iron palette</span>
        <span>|</span>
        <span>30 FPS</span>
        <span>|</span>
        <span>Streaming</span>
        <span>|</span>
        <span>Latency 18 ms</span>
      </div>
    </PanelCard>
  );
}
