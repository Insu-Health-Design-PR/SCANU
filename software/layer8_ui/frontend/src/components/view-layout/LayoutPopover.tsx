import { layoutPresets } from '@/lib/constants';
import type { LayoutPreset } from '@/types/layout';

interface LayoutPopoverProps {
  selected: LayoutPreset;
  onSelect: (layout: LayoutPreset) => void;
  onOpenPreview: () => void;
}

export function LayoutPopover({ selected, onSelect, onOpenPreview }: LayoutPopoverProps) {
  return (
    <div className="w-[320px] rounded-[1.75rem] border border-white/10 bg-surface-800/95 p-4 shadow-panel backdrop-blur-xl">
      <div className="mb-4 text-lg font-medium text-white">View Layout</div>
      <div className="space-y-2">
        {layoutPresets.map((layout) => (
          <button
            key={layout}
            onClick={() => onSelect(layout)}
            className={layout === selected ? 'flex w-full items-center justify-between rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-left text-sm text-cyan-200' : 'flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-left text-sm text-slate-200'}
          >
            <span>{layout}</span>
            <span>{layout === selected ? '✓' : ''}</span>
          </button>
        ))}
      </div>
      <button onClick={onOpenPreview} className="mt-4 w-full rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-medium text-cyan-200">
        Open Preview
      </button>
    </div>
  );
}
