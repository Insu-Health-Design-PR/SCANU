import { useState } from 'react';
import { Check } from 'lucide-react';
import { PresenceSensorPanel } from '@/components/panels/PresenceSensorPanel';
import { PointCloudPanel } from '@/components/panels/PointCloudPanel';
import { RgbCameraPanel } from '@/components/panels/RgbCameraPanel';
import { ThermalCameraPanel } from '@/components/panels/ThermalCameraPanel';
import { ConsoleLogPanel } from '@/components/panels/ConsoleLogPanel';
import { ExecutionControlsPanel } from '@/components/panels/ExecutionControlsPanel';
import { SystemStatusPanel } from '@/components/panels/SystemStatusPanel';
import { LayoutPreviewModal } from '@/components/view-layout/LayoutPreviewModal';
import { layoutPresets } from '@/lib/constants';
import { useDashboardStore } from '@/store/dashboardStore';

type MainModuleId = 'rgb' | 'thermal' | 'pointCloud' | 'presence';

const MAIN_MODULE_ORDER: MainModuleId[] = ['rgb', 'thermal', 'pointCloud', 'presence'];

function renderMainModule(id: MainModuleId) {
  if (id === 'rgb') return <RgbCameraPanel key={id} />;
  if (id === 'thermal') return <ThermalCameraPanel key={id} />;
  if (id === 'pointCloud') return <PointCloudPanel key={id} />;
  return <PresenceSensorPanel key={id} />;
}

function PresenceAndOpsRow() {
  return (
    <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
      <PresenceSensorPanel />
      <div className="space-y-5">
        <SystemStatusPanel />
        <ExecutionControlsPanel />
      </div>
    </div>
  );
}

function LayoutSidebarPanel() {
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
      <section className="rounded-panel border border-white/10 bg-[linear-gradient(180deg,rgba(12,19,32,0.94),rgba(8,13,23,0.9))] p-4 shadow-panel backdrop-blur-xl">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-2xl font-medium tracking-tight text-white">View Layout</h3>
          <span className="rounded-md border border-white/10 bg-white/5 px-1.5 py-0.5 text-xs text-slate-300">53</span>
        </div>

        <div className="space-y-1.5">
          {layoutPresets.map((layout) => {
            const selected = layout === previewLayout;
            return (
              <button
                key={layout}
                type="button"
                onClick={() => setPreviewLayout(layout)}
                className="flex w-full items-center gap-3 rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-white/[0.05]"
              >
                <span
                  className={`flex h-4 w-4 items-center justify-center rounded border ${
                    selected ? 'border-cyan-300 bg-cyan-300/20 text-cyan-200' : 'border-slate-500 text-transparent'
                  }`}
                >
                  <Check className="h-3 w-3" />
                </span>
                <span>{layout}</span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={() => setOpenPreview(true)}
          className="mt-4 w-full rounded-full border border-cyan-400/30 bg-cyan-400/15 px-4 py-2.5 text-sm font-medium text-cyan-100 transition hover:bg-cyan-400/22"
        >
          Open Preview
        </button>
      </section>

      <LayoutPreviewModal
        open={openPreview}
        layout={previewLayout}
        onBack={() => setOpenPreview(false)}
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

function CustomCombinationView() {
  const { customModules, layoutStyle, focusView } = useDashboardStore((state) => ({
    customModules: state.customModules,
    layoutStyle: state.layoutStyle,
    focusView: state.focusView,
  }));

  const enabledMain = MAIN_MODULE_ORDER.filter((id) => customModules[id]);
  const focusCandidate = focusView === 'thermal' ? 'thermal' : 'rgb';
  const focusModule = enabledMain.includes(focusCandidate) ? focusCandidate : enabledMain[0];
  const otherModules = enabledMain.filter((id) => id !== focusModule);
  const hasOps = customModules.systemStatus || customModules.execution;

  if (enabledMain.length === 0) {
    return (
      <div className="rounded-panel border border-white/10 bg-surface-800/70 p-6 text-sm text-slate-300">
        Enable at least one main module in Custom Combination to preview the layout.
      </div>
    );
  }

  if (layoutStyle === 'fullscreen') {
    return (
      <div className="space-y-5">
        {focusModule ? renderMainModule(focusModule) : null}
        {hasOps ? (
          <div className="grid gap-5 lg:grid-cols-2">
            {customModules.systemStatus ? <SystemStatusPanel /> : null}
            {customModules.execution ? <ExecutionControlsPanel /> : null}
          </div>
        ) : null}
        {customModules.consoleLog ? <ConsoleLogPanel /> : null}
      </div>
    );
  }

  if (layoutStyle === 'focus') {
    return (
      <div className="space-y-5">
        {focusModule ? renderMainModule(focusModule) : null}
        {otherModules.length ? (
          <div className="grid gap-4 md:grid-cols-2">{otherModules.map((id) => renderMainModule(id))}</div>
        ) : null}
        {hasOps ? (
          <div className="grid gap-5 lg:grid-cols-2">
            {customModules.systemStatus ? <SystemStatusPanel /> : null}
            {customModules.execution ? <ExecutionControlsPanel /> : null}
          </div>
        ) : null}
        {customModules.consoleLog ? <ConsoleLogPanel /> : null}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2">{enabledMain.map((id) => renderMainModule(id))}</div>
      {hasOps ? (
        <div className="grid gap-5 lg:grid-cols-2">
          {customModules.systemStatus ? <SystemStatusPanel /> : null}
          {customModules.execution ? <ExecutionControlsPanel /> : null}
        </div>
      ) : null}
      {customModules.consoleLog ? <ConsoleLogPanel /> : null}
    </div>
  );
}

function MainTripleView() {
  return (
    <div className="grid gap-5 xl:grid-cols-[1.75fr_0.72fr]">
      <div className="space-y-5">
        <div className="grid gap-5 lg:grid-cols-2">
          <RgbCameraPanel />
          <ThermalCameraPanel />
        </div>

        <div className="grid gap-5 lg:grid-cols-[1.65fr_0.85fr]">
          <PointCloudPanel />
          <SystemStatusPanel />
        </div>

        <PresenceSensorPanel />
      </div>

      <div className="space-y-5">
        <LayoutSidebarPanel />
        <ExecutionControlsPanel />
        <ConsoleLogPanel />
      </div>
    </div>
  );
}

function OneCameraView() {
  const focusView = useDashboardStore((state) => state.focusView);
  return (
    <div className="space-y-5">
      {focusView === 'rgb' ? <RgbCameraPanel /> : <ThermalCameraPanel />}
      <PresenceAndOpsRow />
      <ConsoleLogPanel />
    </div>
  );
}

function TwoCameraView() {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-2">
        <RgbCameraPanel />
        <ThermalCameraPanel />
      </div>
      <PresenceAndOpsRow />
      <ConsoleLogPanel />
    </div>
  );
}

function DualView({ mode }: { mode: 'rgb+pc' | 'thermal+pc' }) {
  return (
    <div className="space-y-5">
      {mode === 'rgb+pc' ? <RgbCameraPanel /> : <ThermalCameraPanel />}
      <PointCloudPanel />
      <PresenceAndOpsRow />
      <ConsoleLogPanel />
    </div>
  );
}

function PointCloudOnlyView() {
  return (
    <div className="space-y-5">
      <PointCloudPanel />
      <PresenceAndOpsRow />
      <ConsoleLogPanel />
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
      return <CustomCombinationView />;
    case 'Triple View':
    default:
      return <MainTripleView />;
  }
}
