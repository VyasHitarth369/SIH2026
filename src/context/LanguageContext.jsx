import { createContext, useContext, useState, useMemo } from 'react';
import { translations } from '../i18n/translations';

const LanguageContext = createContext(null);

function getInitialLang() {
  if (typeof window === 'undefined') return 'en';
  const saved = window.localStorage.getItem('samadhansetu_lang');
  return saved === 'hi' || saved === 'en' ? saved : 'en';
}

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(getInitialLang);

  const setLang = (next) => {
    setLangState(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('samadhansetu_lang', next);
    }
  };

  const value = useMemo(() => ({
    lang,
    setLang,
    t: translations[lang] || translations.en,
  }), [lang]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
