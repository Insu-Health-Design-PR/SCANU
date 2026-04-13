import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

interface PanelCardProps {
  title: string;
  eyebrow?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function PanelCard({ title, eyebrow = 'LIVE MODULE', icon, action, children, className }: PanelCardProps) {
  return (
    <section className={cn('rounded-panel border border-white/10 bg-surface-800/80 p-5 shadow-panel backdrop-blur-xl', className)}>
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          {icon ? (
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
              {icon}
            </div>
          ) : null}
          <div>
            <div className="text-[10px] uppercase tracking-[0.28em] text-slate-500">{eyebrow}</div>
            <h2 className="text-xl font-medium tracking-tight text-slate-100">{title}</h2>
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
