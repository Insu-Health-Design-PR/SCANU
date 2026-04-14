import type { ReactNode } from 'react';

export function DashboardShell({ children }: { children: ReactNode }) {
  return <div className="mx-auto min-h-screen w-full max-w-[1520px] px-4 py-6 md:px-6 xl:px-8">{children}</div>;
}
