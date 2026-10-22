import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource-variable/dm-sans';
import '@fontsource-variable/manrope';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <main className="welcome"><span className="wordmark">clubops<span>●</span></span><h1>Your cabinet, connected.</h1><p>Events, decisions, and the know-how that stays with your club.</p></main>
  </StrictMode>,
);
