import { cn } from '@/lib/cn';

const toneMap = {
  cyan: 'border-cyan-300/25 bg-cyan-300/12 text-cyan-100',
  green: 'border-emerald-300/25 bg-emerald-300/12 text-emerald-100',
  amber: 'border-amber-300/25 bg-amber-300/12 text-amber-100',
  red: 'border-rose-300/25 bg-rose-300/12 text-rose-100',
  slate: 'border-white/10 bg-white/5 text-slate-200',
};

export function StatusChip({ label, tone = 'slate' }: { label: string; tone?: keyof typeof toneMap }) {
  return (
    <span className={cn('inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium tracking-wide', toneMap[tone])}>
      {label}
    </span>
  );
}
