import { useState } from 'react';
import { Play } from 'lucide-react';
import { PanelCard } from '@/components/shared/PanelCard';
import { StatusChip } from '@/components/shared/StatusChip';
import { dashboardApi } from '@/services/dashboardApi';
import { useDashboardStore } from '@/store/dashboardStore';

export function ExecutionControlsPanel() {
  const mode = useDashboardStore((state) => state.snapshot.mode);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [resultText, setResultText] = useState<string>('Ready.');

  const runControl = async (action: 'start' | 'stop' | 'reconfigure' | 'reset') => {
    setPendingAction(action);
    try {
      const result =
        action === 'start'
          ? await dashboardApi.start()
          : action === 'stop'
            ? await dashboardApi.stop()
            : action === 'reconfigure'
              ? await dashboardApi.reconfigure()
              : await dashboardApi.reset();
      setResultText(`${result.action ?? action}: ${result.success ? 'OK' : 'FAILED'}${result.reason ? ` (${result.reason})` : ''}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'unknown error';
      setResultText(`${action}: FAILED (${message})`);
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <PanelCard title="Execution Controls" icon={<Play className="h-4 w-4" />}>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <button
          onClick={() => void runControl('start')}
          disabled={pendingAction !== null}
          className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-200 disabled:opacity-60"
        >
          {pendingAction === 'start' ? 'Starting...' : 'Start'}
        </button>
        <button
          onClick={() => void runControl('stop')}
          disabled={pendingAction !== null}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 disabled:opacity-60"
        >
          {pendingAction === 'stop' ? 'Stopping...' : 'Stop'}
        </button>
        <button
          onClick={() => void runControl('reconfigure')}
          disabled={pendingAction !== null}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 disabled:opacity-60"
        >
          {pendingAction === 'reconfigure' ? 'Reconfiguring...' : 'Reconfigure'}
        </button>
        <button
          onClick={() => void runControl('reset')}
          disabled={pendingAction !== null}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 disabled:opacity-60"
        >
          {pendingAction === 'reset' ? 'Resetting...' : 'Reset'}
        </button>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusChip label={mode === 'live' ? 'Live' : 'Simulated'} tone={mode === 'live' ? 'cyan' : 'slate'} />
        <StatusChip label="All Sensors" tone="slate" />
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-3 text-xs text-slate-400">
        {resultText}
      </div>
    </PanelCard>
  );
}
