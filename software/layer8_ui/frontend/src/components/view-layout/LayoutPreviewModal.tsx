import { X } from 'lucide-react';
import type { LayoutPreset, CustomLayoutModules, LayoutStyle } from '@/types/layout';
import { CustomLayoutBuilder } from '@/components/view-layout/CustomLayoutBuilder';

interface LayoutPreviewModalProps {
  open: boolean;
  layout: LayoutPreset;
  onClose: () => void;
  onApply: () => void;
  customModules: CustomLayoutModules;
  layoutStyle: LayoutStyle;
  onToggleModule: (key: keyof CustomLayoutModules) => void;
  onSelectStyle: (style: LayoutStyle) => void;
}

export function LayoutPreviewModal({
  open,
  layout,
  onClose,
  onApply,
  customModules,
  layoutStyle,
  onToggleModule,
  onSelectStyle,
}: LayoutPreviewModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div className="w-full max-w-6xl rounded-[2rem] border border-white/10 bg-surface-800/95 p-6 shadow-panel">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.28em] text-slate-500">Preview Mode</div>
            <h3 className="text-2xl font-medium text-white">{layout}</h3>
          </div>
          <button onClick={onClose} className="rounded-full border border-white/10 bg-white/5 p-2 text-slate-200">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
          <div className="rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,#0B1220,#060911)] p-5">
            <div className="mb-4 text-sm text-slate-300">Preview canvas</div>
            <div className="grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="aspect-video rounded-3xl border border-white/10 bg-white/[0.04] p-4 text-slate-400">RGB preview</div>
                <div className="aspect-video rounded-3xl border border-white/10 bg-white/[0.04] p-4 text-slate-400">Thermal preview</div>
              </div>
              <div className="aspect-[16/6] rounded-3xl border border-white/10 bg-white/[0.04] p-4 text-slate-400">Point cloud preview</div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4 text-slate-400">Presence sensor</div>
                <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4 text-slate-400">System / execution / logs</div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {layout === 'Custom Combination' ? (
              <CustomLayoutBuilder
                modules={customModules}
                layoutStyle={layoutStyle}
                onToggleModule={onToggleModule}
                onSelectStyle={onSelectStyle}
              />
            ) : (
              <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300">
                This preview modal exists so the user can inspect a layout before applying it to the live dashboard.
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button onClick={onClose} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">Close</button>
              <button onClick={onApply} className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm font-medium text-cyan-200">Apply Layout</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
