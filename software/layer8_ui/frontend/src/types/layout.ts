export type LayoutPreset =
  | '1 Camera'
  | '2 Cameras'
  | 'RGB + Point Cloud'
  | 'Thermal + Point Cloud'
  | 'Point Cloud Only'
  | 'Triple View'
  | 'Custom Combination';

export type FocusView = 'rgb' | 'thermal';
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
