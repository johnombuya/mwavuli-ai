'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useLanguage } from '@/contexts/LanguageContext';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';

const navItems = [
  { href: '/', labelKey: 'dashboardTitle' },
  { href: '/verify', labelKey: 'navVerify' },
  { href: '/appeals', label: 'Appeals' },
  { href: '/admin/audit', label: 'Audit log' },
  { href: '/methodology', label: 'How it works' },
  { href: '/integrate', label: 'Integrate' },
] as const;

function NavContent({
  pathname,
  t,
  onLinkClick,
}: {
  pathname: string;
  t: Record<string, string>;
  onLinkClick?: () => void;
}) {
  return (
    <>
      <nav className="flex-1 space-y-0.5 p-3">
        {navItems.map((item) => {
          const href = item.href;
          const label = 'label' in item ? item.label : t[item.labelKey as keyof typeof t];
          const isActive = pathname === href || (href !== '/' && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              onClick={onLinkClick}
              className={`block rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive ? 'bg-sidebar-hover text-white' : 'text-slate-300 hover:bg-sidebar-hover hover:text-white'
              }`}
            >
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-slate-600 p-3">
        <LanguageSwitcher variant="sidebar" />
      </div>
    </>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { t } = useLanguage();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const closeDrawer = () => setDrawerOpen(false);

  return (
    <>
      {/* Mobile header with hamburger */}
      <div className="fixed left-0 right-0 top-0 z-20 flex h-14 items-center gap-3 border-b border-slate-200 bg-white px-4 lg:hidden">
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
          aria-label="Open menu"
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <Link href="/" className="font-semibold text-slate-900">
          Mwavuli
        </Link>
      </div>

      {/* Mobile drawer overlay */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={closeDrawer}
          aria-hidden
        />
      )}

      {/* Sidebar: drawer on mobile, fixed on desktop */}
      <aside
        className={`fixed left-0 top-0 z-30 flex h-full w-56 flex-col bg-sidebar text-white transition-transform duration-200 ease-out ${
          drawerOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b border-slate-600 px-4">
          <Link href="/" onClick={closeDrawer} className="font-semibold text-slate-100">
            Mwavuli
          </Link>
          <button
            type="button"
            onClick={closeDrawer}
            className="rounded-lg p-2 text-slate-300 hover:bg-slate-700 lg:hidden"
            aria-label="Close menu"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <NavContent pathname={pathname} t={t} onLinkClick={closeDrawer} />
      </aside>
    </>
  );
}
