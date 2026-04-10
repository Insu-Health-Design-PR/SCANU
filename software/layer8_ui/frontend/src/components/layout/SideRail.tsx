import { ConsoleLogPanel } from '@/components/panels/ConsoleLogPanel';
import { ExecutionControlsPanel } from '@/components/panels/ExecutionControlsPanel';
import { SystemStatusPanel } from '@/components/panels/SystemStatusPanel';

export function SideRail() {
  return (
    <aside className="flex flex-col gap-4">
      <SystemStatusPanel />
      <ExecutionControlsPanel />
      <ConsoleLogPanel />
    </aside>
  );
}
