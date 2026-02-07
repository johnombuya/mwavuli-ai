'use client';

import { useLanguage } from '@/contexts/LanguageContext';
import type { UiLang } from '@/lib/translations';

const LABELS: Record<UiLang, string> = {
  en: 'EN',
  sw: 'SW',
  sheng: 'Sheng',
};

interface LanguageSwitcherProps {
  variant?: 'default' | 'sidebar';
}

export function LanguageSwitcher({ variant = 'default' }: LanguageSwitcherProps) {
  const { lang, setLang } = useLanguage();
  const isSidebar = variant === 'sidebar';
  return (
    <div
      className={`flex gap-1 rounded-lg p-0.5 ${
        isSidebar ? 'border border-slate-600 bg-slate-700/50' : 'border border-slate-300 bg-surface-muted'
      }`}
    >
      {(['en', 'sw', 'sheng'] as const).map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => setLang(l)}
          className={`rounded-md px-2 py-1 text-sm font-medium ${
            isSidebar
              ? lang === l
                ? 'bg-slate-600 text-white'
                : 'text-slate-300 hover:bg-slate-600 hover:text-white'
              : lang === l
                ? 'bg-white shadow text-slate-900'
                : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          {LABELS[l]}
        </button>
      ))}
    </div>
  );
}
