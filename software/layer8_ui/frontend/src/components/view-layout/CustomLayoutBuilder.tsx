import type { CustomLayoutModules, LayoutStyle } from '@/types/layout';

interface CustomLayoutBuilderProps {
  modules: CustomLayoutModules;
  layoutStyle: LayoutStyle;
  onToggleModule: (key: keyof CustomLayoutModules) => void;
  onSelectStyle: (style: LayoutStyle) => void;
}

export function CustomLayoutBuilder({ modules, layoutStyle, onToggleModule, onSelectStyle }: CustomLayoutBuilderProps) {
  const moduleKeys = Object.keys(modules) as Array<keyof CustomLayoutModules>;

  return (
    <div className="space-y-4 rounded-3xl border border-white/10 bg-white/[0.03] p-4">
      <div>
        <div className="text-sm font-medium text-white">Custom modules</div>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {moduleKeys.map((key) => (
            <label key={key} className="flex items-center justify-between rounded-2xl border border-white/10 bg-surface-700/50 px-3 py-2 text-sm text-slate-200">
              <span>{key}</span>
              <input type="checkbox" checked={modules[key]} onChange={() => onToggleModule(key)} />
            </label>
          ))}
        </div>
      </div>

      <div>
        <div className="text-sm font-medium text-white">Layout style</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {(['grid', 'focus', 'fullscreen'] as LayoutStyle[]).map((style) => (
            <button
              key={style}
              onClick={() => onSelectStyle(style)}
              className={style === layoutStyle ? 'rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1.5 text-sm text-cyan-200' : 'rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-300'}
            >
              {style}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
