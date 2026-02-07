'use client';

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { type UiLang, translations } from '@/lib/translations';

type LangContextValue = {
  lang: UiLang;
  setLang: (l: UiLang) => void;
  t: typeof translations.en;
};

const LangContext = createContext<LangContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<UiLang>('en');
  const setLang = useCallback((l: UiLang) => setLangState(l), []);
  const t = translations[lang];
  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLanguage(): LangContextValue {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
