import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, LayoutGrid } from 'lucide-react';
import { LayoutPopover } from '@/components/view-layout/LayoutPopover';
import { LayoutPreviewModal } from '@/components/view-layout/LayoutPreviewModal';
import { useDashboardStore } from '@/store/dashboardStore';

export function ViewLayoutButton() {
  const [openPopover, setOpenPopover] = useState(false);
  const [openPreview, setOpenPreview] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const {
    previewLayout,
    setPreviewLayout,
    applyPreviewLayout,
    customModules,
    toggleCustomModule,
    layoutStyle,
    setLayoutStyle,
  } = useDashboardStore();

  useEffect(() => {
    if (!openPopover) return;
    const onPointerDown = (event: MouseEvent) => {
      const node = wrapperRef.current;
      if (!node || !(event.target instanceof Node)) return;
      if (!node.contains(event.target)) setOpenPopover(false);
    };
    window.addEventListener('mousedown', onPointerDown);
    return () => window.removeEventListener('mousedown', onPointerDown);
  }, [openPopover]);

  return (
    <>
      <div ref={wrapperRef} className="relative">
        <button
          type="button"
          aria-expanded={openPopover}
          onClick={() => setOpenPopover((value) => !value)}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:border-cyan-400/25 hover:bg-cyan-400/10"
        >
          <LayoutGrid className="h-4 w-4" />
          View Layout
          <ChevronDown className={`h-4 w-4 transition ${openPopover ? 'rotate-180 text-cyan-300' : 'text-slate-400'}`} />
        </button>

        <AnimatePresence>
          {openPopover ? (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.16, ease: 'easeOut' }}
              className="absolute right-0 top-[calc(100%+12px)] z-40"
            >
              <LayoutPopover
                selected={previewLayout}
                onSelect={setPreviewLayout}
                onOpenPreview={() => {
                  setOpenPreview(true);
                  setOpenPopover(false);
                }}
              />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      <LayoutPreviewModal
        open={openPreview}
        layout={previewLayout}
        onBack={() => {
          setOpenPreview(false);
          setOpenPopover(true);
        }}
        onClose={() => setOpenPreview(false)}
        onApply={() => {
          applyPreviewLayout();
          setOpenPreview(false);
        }}
        customModules={customModules}
        layoutStyle={layoutStyle}
        onToggleModule={toggleCustomModule}
        onSelectStyle={setLayoutStyle}
      />
    </>
  );
}
