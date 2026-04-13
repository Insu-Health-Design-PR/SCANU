import { Radar } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { pointCloudPoints } from '@/data/mock/pointCloud';

export function PointCloudPanel() {
  return (
    <PanelCard title="Point Cloud" icon={<Radar className="h-4 w-4" />}>
      <div className="relative overflow-hidden rounded-[1.2rem] border border-cyan-400/10 bg-[linear-gradient(180deg,#08111f,#05070e)]">
        <div className="aspect-[16/7]">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(29,211,242,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(29,211,242,0.06)_1px,transparent_1px)] bg-[size:40px_40px]" />
          <div className="absolute inset-x-0 bottom-0 h-1/2 bg-[linear-gradient(to_top,rgba(29,211,242,0.12),transparent)]" />
          {pointCloudPoints.map((point) => (
            <span
              key={point.id}
              className="absolute rounded-full bg-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.75)]"
              style={{ left: point.left, top: point.top, width: point.size, height: point.size, opacity: point.opacity }}
            />
          ))}
        </div>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-400 md:grid-cols-4">
        <span>Tracked points 159</span>
        <span>Confidence 89%</span>
        <span>Update 0.8s</span>
        <span>Rate 14 Hz</span>
      </div>
    </PanelCard>
  );
}
