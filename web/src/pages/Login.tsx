import { useState } from 'react';
import { Link } from 'react-router';
import { ArrowRight } from 'lucide-react';
import { apiMode } from '../api';
import { GoogleSignIn } from '../components/GoogleSignIn';
import { DevSignIn } from '../components/DevSignIn';

/** Public route: it must remain reachable when /me is unauthorized or the server is down. */
export default function Login() {
  const [message, setMessage] = useState('');
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim();
  function google() {
    setMessage(
      'Google sign-in will open when your club server is connected. You can explore the sample workspace below.',
    );
  }
  return (
    <main className="login-page">
      <div className="login-art">
        <Link to="/events" className="brand">
          <div className="brand-symbol">
            c<span>•</span>
          </div>
          <span>clubops.</span>
        </Link>
      </div>
      <div className="login-form">
        <h1>Sign in</h1>
        <p>Use the Google account on your club?s cabinet list.</p>
        {apiMode === 'http' ? (
          import.meta.env.VITE_DEV_LOGIN === '1' ? (
            <DevSignIn />
          ) : clientId ? (
            <GoogleSignIn clientId={clientId} />
          ) : (
            <p role="status" className="inline-note">
              Google sign-in needs to be configured by your club administrator.
            </p>
          )
        ) : (
          <button className="button google-button" onClick={google}>
            <span className="google-g">G</span> Continue with Google
          </button>
        )}
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
    </main>
  );
}
