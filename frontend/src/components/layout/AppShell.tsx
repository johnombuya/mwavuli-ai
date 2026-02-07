'use client';

import { Sidebar } from './Sidebar';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <main className="pt-14 pl-0 lg:pt-0 lg:pl-56">
        {children}
      </main>
    </div>
  );
}
