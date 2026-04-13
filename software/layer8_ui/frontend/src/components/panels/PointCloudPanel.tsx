import { Radar } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { StatusChip } from '@/components/shared/StatusChip';
import { useDashboardStore } from '@/store/dashboardStore';

export function PointCloudPanel() {
  const pointCloud = useDashboardStore((state) => state.snapshot.pointCloud);
  const hasPoints = pointCloud.renderPoints.length > 0;

  return (
    <PanelCard title="Point Cloud" icon={<Radar className="h-4 w-4" />}>
      <div className="mb-3 flex flex-wrap gap-2">
        <StatusChip label={hasPoints ? 'Live Feed' : 'No Feed'} tone={hasPoints ? 'cyan' : 'amber'} />
        {pointCloud.stale ? <StatusChip label="Stale" tone="red" /> : null}
      </div>
      <div className="relative overflow-hidden rounded-[1.2rem] border border-cyan-400/10 bg-[linear-gradient(180deg,#08111f,#05070e)]">
        <div className="aspect-[16/7]">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(29,211,242,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(29,211,242,0.06)_1px,transparent_1px)] bg-[size:40px_40px]" />
          <div className="absolute inset-x-0 bottom-0 h-1/2 bg-[linear-gradient(to_top,rgba(29,211,242,0.12),transparent)]" />
          {hasPoints ? (
            pointCloud.renderPoints.map((point) => (
              <span
                key={point.id}
                className="absolute rounded-full bg-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.75)]"
                style={{ left: point.left, top: point.top, width: point.size, height: point.size, opacity: point.opacity }}
              />
            ))
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-400">No point cloud data from backend</div>
          )}
        </div>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-400 md:grid-cols-4">
        <span>Tracked points {pointCloud.trackedPoints}</span>
        <span>Confidence {Math.round(pointCloud.confidence * 100)}%</span>
        <span>Update {(pointCloud.lastUpdateMs / 1000).toFixed(1)}s</span>
        <span>Rate {pointCloud.updateRateHz.toFixed(1)} Hz</span>
      </div>
    </PanelCard>
  );
}
