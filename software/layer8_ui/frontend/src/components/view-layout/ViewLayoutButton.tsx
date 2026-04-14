import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, LayoutGrid } from 'lucide-react';
import { LayoutPopover } from '@/components/view-layout/LayoutPopover';
import { LayoutPreviewModal } from '@/components/view-layout/LayoutPreviewModal';
import { useDashboardStore } from '@/store/dashboardStore';

export function ViewLayoutButton() {
  const [openPopover, setOpenPopover] = useState(false);
  const [openPreview, setOpenPreview] = useState(false);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);

  const {
    previewLayout,
    setPreviewLayout,
    applyPreviewLayout,
    customModules,
    toggleCustomModule,
    layoutStyle,
    setLayoutStyle,
    focusView,
    setFocusView,
  } = useDashboardStore();

  useEffect(() => {
    if (!openPopover) return;

    const updateRect = () => {
      if (!buttonRef.current) return;
      setAnchorRect(buttonRef.current.getBoundingClientRect());
    };

    updateRect();
    window.addEventListener('resize', updateRect);
    window.addEventListener('scroll', updateRect, true);

    const onPointerDown = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (buttonRef.current?.contains(target)) return;
      if (popoverRef.current?.contains(target)) return;
      setOpenPopover(false);
    };

    window.addEventListener('mousedown', onPointerDown);

    return () => {
      window.removeEventListener('resize', updateRect);
      window.removeEventListener('scroll', updateRect, true);
      window.removeEventListener('mousedown', onPointerDown);
    };
  }, [openPopover]);

  const popoverStyle = useMemo(() => {
    const width = 330;
    if (!anchorRect) return { top: 0, left: 0 };
    const left = Math.max(12, Math.min(window.innerWidth - width - 12, anchorRect.right - width));
    const top = anchorRect.bottom + 10;
    return { top, left };
  }, [anchorRect]);

  return (
    <>
      <div className="relative">
        <button
          ref={buttonRef}
          data-testid="view-layout-button"
          type="button"
          aria-expanded={openPopover}
          onClick={() => setOpenPopover((value) => !value)}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:border-cyan-400/25 hover:bg-cyan-400/10"
        >
          <LayoutGrid className="h-4 w-4" />
          View Layout
          <ChevronDown className={`h-4 w-4 transition ${openPopover ? 'rotate-180 text-cyan-300' : 'text-slate-400'}`} />
        </button>
      </div>

      {typeof document !== 'undefined'
        ? createPortal(
            <AnimatePresence>
              {openPopover ? (
                <motion.div
                  ref={popoverRef}
                  initial={{ opacity: 0, y: -8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.98 }}
                  transition={{ duration: 0.16, ease: 'easeOut' }}
                  style={{ position: 'fixed', ...popoverStyle }}
                  className="z-[100]"
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
            </AnimatePresence>,
            document.body,
          )
        : null}

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
        focusView={focusView}
        onToggleModule={toggleCustomModule}
        onSelectStyle={setLayoutStyle}
        onSelectFocusView={setFocusView}
      />
    </>
  );
}
