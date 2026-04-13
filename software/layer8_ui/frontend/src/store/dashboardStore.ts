import { create } from 'zustand';
import { dashboardSnapshot } from '@/data/mock/dashboardSnapshot';
import type { LayoutPreset, FocusView, LayoutStyle, CustomLayoutModules } from '@/types/layout';
import type { DashboardSnapshot } from '@/types/domain';

const STORAGE_KEY = 'scanu-layer8-ui-prefs';

const defaultModules: CustomLayoutModules = {
  rgb: true,
  thermal: true,
  pointCloud: true,
  presence: true,
  systemStatus: true,
  execution: true,
  consoleLog: true,
};

interface PersistedPrefs {
  appliedLayout: LayoutPreset;
  previewLayout: LayoutPreset;
  focusView: FocusView;
  layoutStyle: LayoutStyle;
  customModules: CustomLayoutModules;
}

interface DashboardStore {
  appliedLayout: LayoutPreset;
  previewLayout: LayoutPreset;
  focusView: FocusView;
  layoutStyle: LayoutStyle;
  snapshot: DashboardSnapshot;
  customModules: CustomLayoutModules;
  setSnapshot: (snapshot: DashboardSnapshot) => void;
  updateSnapshot: (updater: (current: DashboardSnapshot) => DashboardSnapshot) => void;
  setPreviewLayout: (layout: LayoutPreset) => void;
  applyPreviewLayout: () => void;
  setFocusView: (focus: FocusView) => void;
  toggleCustomModule: (key: keyof CustomLayoutModules) => void;
  setLayoutStyle: (style: LayoutStyle) => void;
}

const defaultPrefs: PersistedPrefs = {
  appliedLayout: 'Triple View',
  previewLayout: 'Triple View',
  focusView: 'rgb',
  layoutStyle: 'grid',
  customModules: defaultModules,
};

function loadPrefs(): PersistedPrefs {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultPrefs;
    const parsed = JSON.parse(raw) as Partial<PersistedPrefs>;
    return {
      appliedLayout: parsed.appliedLayout ?? defaultPrefs.appliedLayout,
      previewLayout: parsed.previewLayout ?? defaultPrefs.previewLayout,
      focusView: parsed.focusView ?? defaultPrefs.focusView,
      layoutStyle: parsed.layoutStyle ?? defaultPrefs.layoutStyle,
      customModules: {
        ...defaultPrefs.customModules,
        ...(parsed.customModules ?? {}),
      },
    };
  } catch {
    return defaultPrefs;
  }
}

function savePrefs(state: Pick<DashboardStore, 'appliedLayout' | 'previewLayout' | 'focusView' | 'layoutStyle' | 'customModules'>) {
  const payload: PersistedPrefs = {
    appliedLayout: state.appliedLayout,
    previewLayout: state.previewLayout,
    focusView: state.focusView,
    layoutStyle: state.layoutStyle,
    customModules: state.customModules,
  };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Best effort only.
  }
}

const prefs = loadPrefs();

export const useDashboardStore = create<DashboardStore>((set, get) => ({
  appliedLayout: prefs.appliedLayout,
  previewLayout: prefs.previewLayout,
  focusView: prefs.focusView,
  layoutStyle: prefs.layoutStyle,
  snapshot: dashboardSnapshot,
  customModules: prefs.customModules,
  setSnapshot: (snapshot) => set({ snapshot }),
  updateSnapshot: (updater) =>
    set((state) => ({
      snapshot: updater(state.snapshot),
    })),
  setPreviewLayout: (previewLayout) => {
    set({ previewLayout });
    savePrefs(get());
  },
  applyPreviewLayout: () => {
    set((state) => ({ appliedLayout: state.previewLayout }));
    savePrefs(get());
  },
  setFocusView: (focusView) => {
    set({ focusView });
    savePrefs(get());
  },
  toggleCustomModule: (key) => {
    set((state) => ({
      customModules: {
        ...state.customModules,
        [key]: !state.customModules[key],
      },
    }));
    savePrefs(get());
  },
  setLayoutStyle: (layoutStyle) => {
    set({ layoutStyle });
    savePrefs(get());
  },
}));
