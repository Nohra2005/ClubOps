import { useEffect, useRef, useState } from 'react';
import { ApiError } from './api/client';

export function useResource<T>(load: () => Promise<T>, keys: unknown[]) {
  const loader = useRef(load); loader.current = load;
  const [value, setValue] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true; setLoading(true); setValue(undefined); setError(undefined);
    loader.current().then(result => { if (active) { setValue(result); setLoading(false); } }).catch((cause: unknown) => {
      if (!active) return;
      setError(cause instanceof Error ? cause.message : 'Something went wrong. Please try again.'); setLoading(false);
      if (cause instanceof ApiError && cause.status === 0) window.dispatchEvent(new Event('clubops-offline'));
    });
    return () => { active = false; };
    // Callers declare the identity of a resource; inline loader functions do not refetch it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...keys, revision]);
  return { value, error, loading, reload: () => setRevision(n => n + 1) };
}

/** The ref locks synchronously, before React renders a disabled button. */
export function useAction() {
  const lock = useRef(false);
  const mounted = useRef(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string>();
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function run<T>(action: () => Promise<T>): Promise<{ ok: true; value: T } | { ok: false }> {
    if (lock.current) return { ok: false };
    lock.current = true; setPending(true); setError(undefined);
    try { const value = await action(); return { ok: true, value }; }
    catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : 'Something went wrong. Please try again.'); if (cause instanceof ApiError && cause.status === 0) window.dispatchEvent(new Event('clubops-offline')); return { ok: false }; }
    finally { lock.current = false; if (mounted.current) setPending(false); }
  }
  return { run, pending, error, clearError: () => setError(undefined) };
}
