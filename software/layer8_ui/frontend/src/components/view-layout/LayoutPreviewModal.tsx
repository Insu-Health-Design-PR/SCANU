import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { CustomLayoutBuilder } from '@/components/view-layout/CustomLayoutBuilder';
import type { CustomLayoutModules, FocusView, LayoutPreset, LayoutStyle } from '@/types/layout';

interface LayoutPreviewModalProps {
  open: boolean;
  layout: LayoutPreset;
  onBack: () => void;
  onClose: () => void;
  onApply: () => void;
  customModules: CustomLayoutModules;
  layoutStyle: LayoutStyle;
  focusView: FocusView;
  onToggleModule: (key: keyof CustomLayoutModules) => void;
  onSelectStyle: (style: LayoutStyle) => void;
  onSelectFocusView: (focusView: FocusView) => void;
}

function Frame({ title, subtitle, className = '' }: { title: string; subtitle?: string; className?: string }) {
  return (
    <div className={`rounded-3xl border border-white/15 bg-[linear-gradient(180deg,rgba(10,18,32,0.86),rgba(6,10,18,0.82))] p-4 ${className}`}>
      <div className="text-base font-medium text-slate-100">{title}</div>
      {subtitle ? <div className="mt-2 text-sm text-slate-400">{subtitle}</div> : null}
    </div>
  );
}

function OptionalInfo({ text }: { text: string }) {
  return <Frame title="Optional info below:" subtitle={text} className="min-h-20" />;
}

function CustomPreview({
  modules,
  layoutStyle,
  focusView,
}: {
  modules: CustomLayoutModules;
  layoutStyle: LayoutStyle;
  focusView: FocusView;
}) {
  const orderedModules = [
    modules.rgb ? { id: 'rgb', label: 'RGB Camera' } : null,
    modules.thermal ? { id: 'thermal', label: 'Thermal Camera' } : null,
    modules.pointCloud ? { id: 'pointCloud', label: 'Point Cloud / Spatial View' } : null,
    modules.presence ? { id: 'presence', label: 'Presence Sensor' } : null,
  ].filter(Boolean) as Array<{ id: FocusView; label: string }>;

  const focused = orderedModules.find((module) => module.id === focusView) ?? orderedModules[0];
  const others = orderedModules.filter((module) => module.id !== focused?.id);

  const utilityModules = [
    modules.systemStatus ? 'System Status' : null,
    modules.execution ? 'Execution Controls' : null,
  ].filter(Boolean) as string[];

  return (
    <div className="space-y-4">
      {orderedModules.length === 0 ? (
        <Frame title="No primary modules selected" subtitle="Enable at least one camera, point cloud, or presence module." />
      ) : layoutStyle === 'fullscreen' ? (
        <>
          <Frame title={focused.label} subtitle="fullscreen main panel" className="aspect-[16/6]" />
          {others.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {others.map((module) => (
                <Frame key={module.id} title={module.label} className="aspect-video" />
              ))}
            </div>
          ) : null}
        </>
      ) : layoutStyle === 'focus' ? (
        <>
          <Frame title={focused.label} subtitle="focused main panel" className="aspect-[16/6]" />
          {others.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {others.map((module) => (
                <Frame key={module.id} title={module.label} className="aspect-video" />
              ))}
            </div>
          ) : null}
        </>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {orderedModules.map((module) => (
            <Frame key={module.id} title={module.label} className="aspect-video" />
          ))}
        </div>
      )}

      {utilityModules.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {utilityModules.map((name) => (
            <Frame key={name} title={name} />
          ))}
        </div>
      ) : null}

      {modules.consoleLog ? <Frame title="Console Log" subtitle="trigger log / system events" /> : null}
    </div>
  );
}

function PresetPreview({
  layout,
  customModules,
  layoutStyle,
  focusView,
}: {
  layout: LayoutPreset;
  customModules: CustomLayoutModules;
  layoutStyle: LayoutStyle;
  focusView: FocusView;
}) {
  if (layout === '1 Camera') {
    return (
      <div className="space-y-4">
        <Frame title="Focused Camera" subtitle="large preview" className="aspect-[16/7]" />
        <OptionalInfo text="Presence Sensor | System Status | minimal controls" />
      </div>
    );
  }

  if (layout === '2 Cameras') {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <Frame title="RGB Camera" subtitle="large preview" className="aspect-video" />
          <Frame title="Thermal Camera" subtitle="large preview" className="aspect-video" />
        </div>
        <OptionalInfo text="Presence Sensor | System Status | minimal controls" />
      </div>
    );
  }

  if (layout === 'RGB + Point Cloud') {
    return (
      <div className="space-y-4">
        <Frame title="RGB Camera" subtitle="live stream" className="aspect-video" />
        <Frame title="Point Cloud / Spatial View" subtitle="3D / radar visualization" className="aspect-[16/6]" />
      </div>
    );
  }

  if (layout === 'Thermal + Point Cloud') {
    return (
      <div className="space-y-4">
        <Frame title="Thermal Camera" subtitle="live thermal stream" className="aspect-video" />
        <Frame title="Point Cloud / Spatial View" subtitle="3D / radar visualization" className="aspect-[16/6]" />
      </div>
    );
  }

  if (layout === 'Point Cloud Only') {
    return (
      <div className="space-y-4">
        <Frame title="Point Cloud / Spatial View" subtitle="full screen radar scene" className="aspect-[16/6]" />
        <OptionalInfo text="Presence Sensor | Status | small controls" />
      </div>
    );
  }

  if (layout === 'Custom Combination') {
    return <CustomPreview modules={customModules} layoutStyle={layoutStyle} focusView={focusView} />;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <Frame title="RGB Camera" className="aspect-video" />
        <Frame title="Thermal Camera" className="aspect-video" />
      </div>
      <Frame title="Point Cloud / Spatial View" className="aspect-[16/6]" />
      <Frame title="Presence Sensor | Status | Execution" />
    </div>
  );
}

export function LayoutPreviewModal({
  open,
  layout,
  onBack,
  onClose,
  onApply,
  customModules,
  layoutStyle,
  focusView,
  onToggleModule,
  onSelectStyle,
  onSelectFocusView,
}: LayoutPreviewModalProps) {
  const [flashPreview, setFlashPreview] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  const handlePreviewLayout = () => {
    setFlashPreview(true);
    setTimeout(() => setFlashPreview(false), 420);
    const node = document.getElementById('layout-preview-canvas');
    if (node) {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.16 }}
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/88 p-4 backdrop-blur-sm"
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            onClick={(event) => event.stopPropagation()}
            className="w-full max-w-7xl rounded-[2rem] border border-cyan-400/15 bg-[linear-gradient(180deg,rgba(12,19,32,0.98),rgba(8,13,23,0.96))] p-5 shadow-panel"
          >
            <div className="mb-4 flex items-center justify-between gap-4 rounded-2xl border border-white/10 px-4 py-3">
              <h3 className="text-2xl font-medium text-white">Layout Preview: {layout}</h3>
              <div className="flex items-center gap-3">
                <button
                  data-testid="apply-layout"
                  onClick={onApply}
                  className="rounded-xl border border-cyan-400/25 bg-cyan-400/12 px-4 py-2 text-sm font-medium text-cyan-100 transition hover:bg-cyan-400/20"
                >
                  Apply Layout
                </button>
                <button
                  onClick={onBack}
                  className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10"
                >
                  Back
                </button>
                <button
                  data-testid="close-layout-preview"
                  onClick={onClose}
                  className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10"
                >
                  Close
                </button>
                <button
                  onClick={onClose}
                  className="rounded-full border border-white/10 bg-white/5 p-2 text-slate-300 transition hover:bg-white/10"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className={`grid gap-4 ${layout === 'Custom Combination' ? 'xl:grid-cols-[2fr_1fr]' : 'xl:grid-cols-1'}`}>
              <div
                id="layout-preview-canvas"
                className={`rounded-[1.5rem] border bg-[linear-gradient(180deg,#0a1221,#060a12)] p-5 transition ${
                  flashPreview ? 'border-cyan-300/55 shadow-[0_0_0_1px_rgba(103,232,249,0.45),0_0_34px_rgba(34,211,238,0.18)]' : 'border-white/10'
                }`}
              >
                <PresetPreview layout={layout} customModules={customModules} layoutStyle={layoutStyle} focusView={focusView} />
              </div>

              {layout === 'Custom Combination' ? (
                <div className="space-y-4 rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4">
                  <CustomLayoutBuilder
                    modules={customModules}
                    layoutStyle={layoutStyle}
                    focusView={focusView}
                    onToggleModule={onToggleModule}
                    onSelectStyle={onSelectStyle}
                    onSelectFocusView={onSelectFocusView}
                    onPreviewLayout={handlePreviewLayout}
                  />
                </div>
              ) : null}
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
