import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { createApi, getDemoSession, setDemoSession } from './api';
import type { ApiClient } from './api/client';
import type { DemoSession } from './api/mock';
import type { Me } from './api/types';
import { useResource } from './hooks';

interface Context {
  api: ApiClient;
  me: Me;
  canEdit: boolean;
  isPresident: boolean;
  refresh: () => void;
  notify: (text: string) => void;
  switchDemo: (session: DemoSession) => void;
  offline: boolean;
  signedOut: boolean;
  signOut: () => void;
  signIn: () => void;
}
const AppContext = createContext<Context | null>(null);
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error('App context is missing');
  return context;
};

export function AppProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState(getDemoSession);
  const api = useMemo(() => createApi(session), [session]);
  const user = useResource(() => api.me(), [api], true);
  const [toast, setToast] = useState('');
  const [offline, setOffline] = useState(false);
  const [signedOut, setSignedOut] = useState(false);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(''), 4500);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    const down = () => setOffline(true);
    const up = () => setOffline(false);
    const storage = () =>
      setToast('Browser storage is unavailable. Changes stay in this tab only.');
    window.addEventListener('clubops-offline', down);
    window.addEventListener('offline', down);
    window.addEventListener('online', up);
    window.addEventListener('clubops-storage-unavailable', storage);
    return () => {
      window.removeEventListener('clubops-offline', down);
      window.removeEventListener('offline', down);
      window.removeEventListener('online', up);
      window.removeEventListener('clubops-storage-unavailable', storage);
    };
  }, []);
  if (window.location.pathname === '/login') return <>{children}</>;
  if (
    user.loading &&
    (!user.value ||
      (api.mode === 'demo' &&
        (user.value.club.id !== session.club || user.value.role !== session.role)))
  )
    return (
      <div className="boot">
        <div className="brand-symbol">
          c<span>•</span>
        </div>
        <p>Opening your club workspace…</p>
        <div className="skeleton" />
      </div>
    );
  if (user.error || !user.value)
    return (
      <div className="boot">
        <h1>Let's get you connected.</h1>
        <p>{user.error}</p>
        <button className="button primary" onClick={user.reload}>
          Try again
        </button>
        <a className="button" href="/login">
          Sign in
        </a>
      </div>
    );
  const me = user.value;
  return (
    <AppContext
      value={{
        api,
        me,
        canEdit: me.role !== 'adviser',
        isPresident: me.role === 'president',
        refresh: user.reload,
        notify: setToast,
        switchDemo: (next) => {
          setDemoSession(next);
          setSession(next);
          setOffline(false);
        },
        offline,
        signedOut,
        signOut: () => {
          if (api.mode === 'demo') setSignedOut(true);
          else setToast('Sign-out is not connected yet. Close this workspace to leave it.');
        },
        signIn: () => setSignedOut(false),
      }}
    >
      {children}
      {toast && (
        <div className="toast" role="status">
          {toast}
          <button aria-label="Dismiss notification" onClick={() => setToast('')}>
            ×
          </button>
        </div>
      )}
    </AppContext>
  );
}
