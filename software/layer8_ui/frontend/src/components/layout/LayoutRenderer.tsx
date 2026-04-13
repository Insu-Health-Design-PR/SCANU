import { PresenceSensorPanel } from '@/components/panels/PresenceSensorPanel';
import { PointCloudPanel } from '@/components/panels/PointCloudPanel';
import { RgbCameraPanel } from '@/components/panels/RgbCameraPanel';
import { ThermalCameraPanel } from '@/components/panels/ThermalCameraPanel';
import { SideRail } from '@/components/layout/SideRail';
import { useDashboardStore } from '@/store/dashboardStore';

function MainTripleView() {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.9fr_0.9fr]">
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <RgbCameraPanel />
          <ThermalCameraPanel />
        </div>
        <PointCloudPanel />
        <PresenceSensorPanel />
      </div>
      <SideRail />
    </div>
  );
}

function OneCameraView() {
  const focusView = useDashboardStore((state) => state.focusView);
  return (
    <div className="grid gap-4 xl:grid-cols-[1.9fr_0.9fr]">
      <div className="space-y-4">
        {focusView === 'rgb' ? <RgbCameraPanel /> : <ThermalCameraPanel />}
        <PointCloudPanel />
        <PresenceSensorPanel />
      </div>
      <SideRail />
    </div>
  );
}

function TwoCameraView() {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.9fr_0.9fr]">
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <RgbCameraPanel />
          <ThermalCameraPanel />
        </div>
        <PresenceSensorPanel />
      </div>
      <SideRail />
    </div>
  );
}

function DualView({ mode }: { mode: 'rgb+pc' | 'thermal+pc' }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.9fr_0.9fr]">
      <div className="space-y-4">
        {mode === 'rgb+pc' ? <RgbCameraPanel /> : <ThermalCameraPanel />}
        <PointCloudPanel />
        <PresenceSensorPanel />
      </div>
      <SideRail />
    </div>
  );
}

function PointCloudOnlyView() {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.9fr_0.9fr]">
      <div className="space-y-4">
        <PointCloudPanel />
        <PresenceSensorPanel />
      </div>
      <SideRail />
    </div>
  );
}

export function LayoutRenderer() {
  const layout = useDashboardStore((state) => state.appliedLayout);

  switch (layout) {
    case '1 Camera':
      return <OneCameraView />;
    case '2 Cameras':
      return <TwoCameraView />;
    case 'RGB + Point Cloud':
      return <DualView mode="rgb+pc" />;
    case 'Thermal + Point Cloud':
      return <DualView mode="thermal+pc" />;
    case 'Point Cloud Only':
      return <PointCloudOnlyView />;
    case 'Custom Combination':
      return <MainTripleView />;
    case 'Triple View':
    default:
      return <MainTripleView />;
  }
}
