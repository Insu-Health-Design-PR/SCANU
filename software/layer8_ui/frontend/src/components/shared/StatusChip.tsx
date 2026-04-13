import { cn } from '@/lib/cn';

const toneMap = {
  cyan: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-200',
  green: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200',
  amber: 'border-amber-400/20 bg-amber-400/10 text-amber-200',
  red: 'border-rose-400/20 bg-rose-400/10 text-rose-200',
  slate: 'border-white/10 bg-white/5 text-slate-200',
};

export function StatusChip({ label, tone = 'slate' }: { label: string; tone?: keyof typeof toneMap }) {
  return (
    <span className={cn('inline-flex items-center rounded-full border px-3 py-1 text-xs', toneMap[tone])}>
      {label}
    </span>
  );
}
