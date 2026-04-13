import { layoutPresets } from '@/lib/constants';
import type { LayoutPreset } from '@/types/layout';

interface LayoutPopoverProps {
  selected: LayoutPreset;
  onSelect: (layout: LayoutPreset) => void;
  onOpenPreview: () => void;
}

export function LayoutPopover({ selected, onSelect, onOpenPreview }: LayoutPopoverProps) {
  return (
    <div className="w-[330px] overflow-hidden rounded-[1.2rem] border border-white/12 bg-[linear-gradient(180deg,rgba(12,19,32,0.98),rgba(8,13,23,0.95))] shadow-panel backdrop-blur-xl">
      <div className="border-b border-white/10 px-4 py-3 text-lg font-medium text-white">View Layout</div>

      <div className="space-y-0 px-2 py-2">
        {layoutPresets.map((layout) => (
          <button
            data-testid={`layout-option-${layout.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
            key={layout}
            type="button"
            onClick={() => onSelect(layout)}
            className="flex w-full items-center gap-3 rounded-lg border border-transparent px-3 py-2 text-left text-sm text-slate-200 transition hover:border-white/10 hover:bg-white/[0.05]"
          >
            <span
              className={`h-3.5 w-3.5 rounded-full border ${layout === selected ? 'border-cyan-300 bg-cyan-300/90' : 'border-slate-500'}`}
            />
            <span className={layout === selected ? 'text-cyan-100' : 'text-slate-200'}>{layout}</span>
          </button>
        ))}
      </div>

      <div className="border-t border-white/10 p-3">
        <button
          data-testid="open-layout-preview"
          type="button"
          onClick={onOpenPreview}
          className="w-full rounded-xl border border-cyan-400/25 bg-cyan-400/12 px-4 py-2.5 text-sm font-medium text-cyan-100 transition hover:bg-cyan-400/20"
        >
          Open Preview
        </button>
      </div>
    </div>
  );
}
