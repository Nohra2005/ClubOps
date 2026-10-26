import { useEffect, useRef, useState } from 'react';
import { createApi } from '../api';
import { loadGoogleIdentity } from '../google-identity';
import { ErrorNotice } from './ui';

export function GoogleSignIn({ clientId }: { clientId: string }) {
  const container = useRef<HTMLDivElement>(null);
  const sending = useRef(false);
  const [pending, setPending] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setError('');
    setReady(false);
    loadGoogleIdentity()
      .then((google) => {
        if (!active || !container.current) return;
        google.initialize({
          client_id: clientId,
          auto_select: false,
          callback: async ({ credential }) => {
            if (!active || sending.current) return;
            sending.current = true;
            setPending(true);
            setError('');
            try {
              await createApi().signInGoogle(credential);
              if (active) window.location.assign('/events');
            } catch (cause) {
              if (active)
                setError(
                  cause instanceof Error
                    ? cause.message
                    : 'Sign-in could not finish. Please try again.',
                );
            } finally {
              sending.current = false;
              if (active) setPending(false);
            }
          },
        });
        container.current.replaceChildren();
        google.renderButton(container.current, {
          theme: 'outline',
          size: 'large',
          width: Math.min(360, container.current.clientWidth || 280),
          text: 'continue_with',
        });
        setReady(true);
      })
      .catch((cause: unknown) => {
        if (active)
          setError(cause instanceof Error ? cause.message : 'Google sign-in is unavailable.');
      });
    return () => {
      active = false;
    };
  }, [clientId, attempt]);
  return (
    <>
      <div
        ref={container}
        aria-label="Google sign-in"
        aria-busy={pending}
        style={{ pointerEvents: pending ? 'none' : undefined }}
      />
      {!ready && !error && <p role="status">Loading Google sign-in…</p>}
      {pending && <p role="status">Opening your cabinet workspace…</p>}
      <ErrorNotice message={error} />
      {error && !ready && (
        <button className="button" onClick={() => setAttempt((value) => value + 1)}>
          Try Google again
        </button>
      )}
    </>
  );
}
