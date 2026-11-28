import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

export type Theme = 'frost' | 'afterdark';
const key = 'clubops.theme';
const ThemeContext = createContext<{ theme: Theme; toggle: () => void } | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === 'afterdark' ? 'afterdark' : 'frost',
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', theme === 'afterdark' ? '#0b2233' : '#dceaf3');
    try {
      localStorage.setItem(key, theme);
    } catch {
      // Keep the in-tab choice usable when browser persistence is unavailable.
    }
  }, [theme]);
  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === key || event.key === null)
        setTheme(event.newValue === 'afterdark' ? 'afterdark' : 'frost');
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);
  return (
    <ThemeContext.Provider
      value={{
        theme,
        toggle: () => setTheme((current) => (current === 'frost' ? 'afterdark' : 'frost')),
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('ThemeProvider is missing');
  return context;
}
