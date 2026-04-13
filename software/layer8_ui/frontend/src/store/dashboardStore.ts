import { create } from 'zustand';
import { dashboardSnapshot } from '@/data/mock/dashboardSnapshot';
import type { LayoutPreset, FocusView, LayoutStyle, CustomLayoutModules } from '@/types/layout';

const defaultModules: CustomLayoutModules = {
  rgb: true,
  thermal: true,
  pointCloud: true,
  presence: true,
  systemStatus: true,
  execution: true,
  consoleLog: true,
};

interface DashboardStore {
  appliedLayout: LayoutPreset;
  previewLayout: LayoutPreset;
  focusView: FocusView;
  layoutStyle: LayoutStyle;
  snapshot: typeof dashboardSnapshot;
  customModules: CustomLayoutModules;
  setPreviewLayout: (layout: LayoutPreset) => void;
  applyPreviewLayout: () => void;
  setFocusView: (focus: FocusView) => void;
  toggleCustomModule: (key: keyof CustomLayoutModules) => void;
  setLayoutStyle: (style: LayoutStyle) => void;
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  appliedLayout: 'Triple View',
  previewLayout: 'Triple View',
  focusView: 'rgb',
  layoutStyle: 'grid',
  snapshot: dashboardSnapshot,
  customModules: defaultModules,
  setPreviewLayout: (layout) => set({ previewLayout: layout }),
  applyPreviewLayout: () => set((state) => ({ appliedLayout: state.previewLayout })),
  setFocusView: (focusView) => set({ focusView }),
  toggleCustomModule: (key) =>
    set((state) => ({
      customModules: {
        ...state.customModules,
        [key]: !state.customModules[key],
      },
    })),
  setLayoutStyle: (layoutStyle) => set({ layoutStyle }),
}));
