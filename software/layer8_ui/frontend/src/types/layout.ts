export type LayoutPreset =
  | '1 Camera'
  | '2 Cameras'
  | 'RGB + Point Cloud'
  | 'Thermal + Point Cloud'
  | 'Point Cloud Only'
  | 'Triple View'
  | 'Custom Combination';

export type FocusView = 'rgb' | 'thermal' | 'pointCloud' | 'presence';
export type LayoutStyle = 'grid' | 'focus' | 'fullscreen';

export interface CustomLayoutModules {
  rgb: boolean;
  thermal: boolean;
  pointCloud: boolean;
  presence: boolean;
  systemStatus: boolean;
  execution: boolean;
  consoleLog: boolean;
}

export interface UiPreferences {
  appliedLayout: LayoutPreset;
  previewLayout: LayoutPreset;
  focusView: FocusView;
  layoutStyle: LayoutStyle;
  customModules: CustomLayoutModules;
}
