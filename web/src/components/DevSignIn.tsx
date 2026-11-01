import { useState } from 'react';
import { createApi } from '../api';
import { ErrorNotice } from './ui';
import { useAction } from '../hooks';

/** Included only when a local build explicitly enables VITE_DEV_LOGIN. Server permissions still apply. */
export function DevSignIn() {
  const [email, setEmail] = useState('president@example.com');
  const action = useAction();
  return (
    <form
      onSubmit={async (event) => {
        event.preventDefault();
        if (action.pending) return;
        const result = await action.run(() => createApi().signInDev(email));
        if (result.ok) window.location.assign('/events');
      }}
    >
      <p className="inline-note">Local development only. Use a cabinet test account.</p>
      <label className="field">
        <span>Development email</span>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          maxLength={254}
        />
      </label>
      <ErrorNotice message={action.error} />
      <button className="button primary" disabled={action.pending}>
        {action.pending ? 'Signing in…' : 'Sign in locally'}
      </button>
    </form>
  );
}
