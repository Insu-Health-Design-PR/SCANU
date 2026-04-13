import { useState } from 'react';
import { LayoutGrid } from 'lucide-react';
import { LayoutPopover } from '@/components/view-layout/LayoutPopover';
import { LayoutPreviewModal } from '@/components/view-layout/LayoutPreviewModal';
import { useDashboardStore } from '@/store/dashboardStore';

export function ViewLayoutButton() {
  const [openPopover, setOpenPopover] = useState(false);
  const [openPreview, setOpenPreview] = useState(false);
  const {
    previewLayout,
    setPreviewLayout,
    applyPreviewLayout,
    customModules,
    toggleCustomModule,
    layoutStyle,
    setLayoutStyle,
  } = useDashboardStore();

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setOpenPopover((value) => !value)}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200"
        >
          <LayoutGrid className="h-4 w-4" />
          View Layout
        </button>

        {openPopover ? (
          <div className="absolute right-0 top-[calc(100%+12px)] z-40">
            <LayoutPopover
              selected={previewLayout}
              onSelect={setPreviewLayout}
              onOpenPreview={() => {
                setOpenPreview(true);
                setOpenPopover(false);
              }}
            />
          </div>
        ) : null}
      </div>

      <LayoutPreviewModal
        open={openPreview}
        layout={previewLayout}
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
