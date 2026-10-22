import { useState } from 'react';
import { Link } from 'react-router';
import { ArrowRight } from 'lucide-react';
import { apiMode } from '../api';

/** Public route: it must remain reachable when /me is unauthorized or the server is down. */
export default function Login() {
  const [message, setMessage] = useState('');
  function google() {
    const configured = import.meta.env.VITE_AUTH_LOGIN_URL;
    if (apiMode === 'http' && configured) {
      try {
        const url = new URL(configured, window.location.origin);
        if (url.origin !== window.location.origin && url.protocol !== 'https:')
          throw new Error('invalid');
        window.location.assign(url.href);
        return;
      } catch {
        setMessage('The sign-in connection is unavailable. Please ask your club administrator.');
        return;
      }
    }
    setMessage(
      'Google sign-in will open when your club server is connected. You can explore the sample workspace below.',
    );
  }
  return (
    <div className="login-page">
      <div className="login-art">
        <Link to="/events" className="brand">
          <div className="brand-symbol">
            c<span>•</span>
          </div>
          <span>clubops.</span>
        </Link>
        <div>
          <span className="eyebrow">A BETTER WAY TO RUN YOUR CLUB</span>
          <h1>
            Great events.
            <br />A lasting legacy.
          </h1>
          <p>Keep your plans, your people, and everything you've learned together.</p>
        </div>
        <small>Made for the cabinet. Built for the next one.</small>
      </div>
      <div className="login-form">
        <span className="eyebrow">WELCOME TO CLUBOPS</span>
        <h2>Your club starts here.</h2>
        <p>Sign in to your cabinet workspace.</p>
        <button className="button google-button" onClick={google}>
          <span className="google-g">G</span> Continue with Google
        </button>
        {message && (
          <p role="status" className="inline-note">
            {message}
          </p>
        )}
        {apiMode === 'demo' && (
          <>
            <div className="divider-label">or take a look around</div>
            <button className="button primary" onClick={() => window.location.assign('/events')}>
              Explore the demo <ArrowRight size={16} />
            </button>
            <small>Sample accounts and fictional records. No Google account is connected.</small>
          </>
        )}
      </div>
    </div>
  );
}
