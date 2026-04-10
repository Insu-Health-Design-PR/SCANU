import type { ReactNode } from 'react';

export function DashboardShell({ children }: { children: ReactNode }) {
  return <div className="min-h-screen px-4 py-6 md:px-6 xl:px-8">{children}</div>;
}
