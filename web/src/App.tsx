import { useEffect, useState, type FormEvent } from 'react';
import {
  BrowserRouter,
  Link,
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router';
import {
  ArrowRight,
  ArrowUpRight,
  Bell,
  BookOpen,
  CalendarDays,
  CheckCheck,
  ChevronDown,
  LogOut,
  Mail,
  MessageCircle,
  Search,
  Settings2,
} from 'lucide-react';
import { AppProvider, useApp } from './AppContext';
import { clubs } from './api/fixtures';
import { roleLabels, roles } from './api/types';
import Events from './pages/Events';
import NewEvent from './pages/NewEvent';
import EventDetail from './pages/EventDetail';
import Chat from './pages/Chat';
import Review from './pages/Review';
import Calendar from './pages/Calendar';
import Knowledge, { KnowledgeFact } from './pages/Knowledge';
import Handover from './pages/Handover';
import Settings from './pages/Settings';
import Setup from './pages/Setup';
import Inbox from './pages/Inbox';
import Login from './pages/Login';
import { storage } from './api';
import { PageHeading } from './components/ui';
import { RoleLearningProvider } from './handover/RoleLearning';
import { RoleTour } from './handover/RoleTour';

const navigation = [
  { to: '/chat', label: 'Chat', icon: MessageCircle },
  { to: '/events', label: 'Events', icon: CalendarDays },
  { to: '/review', label: 'Review', icon: CheckCheck },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/inbox', label: 'Inbox', icon: Mail },
  { to: '/knowledge', label: 'Knowledge', icon: BookOpen },
  { to: '/settings', label: 'Settings', icon: Settings2 },
];

function Shell() {
  const { api, me } = useApp();
  return (
    <RoleLearningProvider key={JSON.stringify([api.mode, me.club.id, me.user.member_id, me.role])}>
      <ShellContent />
    </RoleLearningProvider>
  );
}

function ShellContent() {
  const { me, api, switchDemo, signOut, signingOut, signedOut, offline, isPresident } = useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const title =
    navigation.find((n) => location.pathname.startsWith(n.to))?.label ??
    (location.pathname === '/handover' ? 'Start your role' : 'Workspace');
  useEffect(() => {
    document.title = `${title} · ClubOps`;
  }, [title]);
  if (signedOut) return <Navigate to="/login" replace />;
  if (
    !me.club.setup_complete &&
    isPresident &&
    location.pathname === '/events' &&
    storage.getItem(`clubops.setup.paused.${me.club.id}`) !== 'yes'
  )
    return <Navigate to="/setup" replace />;
  const search = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim()) {
      navigate(`/knowledge?q=${encodeURIComponent(query.trim())}`);
      setSearchOpen(false);
    }
  };
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link to="/events" className="brand">
          <div className="brand-symbol">
            c<span>•</span>
          </div>
          <span>
            clubops<span className="brand-dot">.</span>
          </span>
        </Link>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation
            .filter((n) => n.to !== '/settings' || isPresident)
            .map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
              >
                <Icon size={19} strokeWidth={1.7} />
                <span>{label}</span>
                {to === '/review' && me.counts.review > 0 && (
                  <span className="nav-count review-count">{me.counts.review}</span>
                )}
                {to === '/events' && me.counts.overdue_events > 0 && (
                  <span className="nav-count">{me.counts.overdue_events}</span>
                )}
              </NavLink>
            ))}
        </nav>
        <div className="sidebar-footer">
          <span className="tiny-label">BUILT FOR THE NEXT CABINET</span>
          <p>
            Good plans.
            <br />
            Knowledge that stays.
          </p>
          <div>
            <span className="live-dot" /> Fall cabinet · 2026/27
          </div>
        </div>
      </aside>
      <div className="app-body">
        <header className="topbar">
          <div className="club-selector">
            <span className="club-monogram">{me.club.initials}</span>
            <div>
              <span className="tiny-label">CLUB WORKSPACE</span>
              {api.mode === 'demo' ? (
                <label>
                  <span className="sr-only">Club</span>
                  <select
                    aria-label="Club"
                    value={me.club.id}
                    onChange={(e) => {
                      switchDemo({ club: e.target.value, role: me.role });
                      navigate('/events');
                    }}
                  >
                    {clubs.map((club) => (
                      <option key={club.id} value={club.id}>
                        {club.name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <strong>{me.club.name}</strong>
              )}
            </div>
          </div>
          <form className={`top-search${searchOpen ? ' expanded' : ''}`} onSubmit={search}>
            <button
              type="button"
              aria-label="Open Knowledge search"
              onClick={() => setSearchOpen(!searchOpen)}
            >
              <Search size={18} />
            </button>
            <input
              aria-label="Search Knowledge"
              placeholder="Search your club's knowledge"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <kbd>↵</kbd>
          </form>
          <div className="topbar-actions">
            <details className="popover">
              <summary aria-label={`${me.counts.reminders} reminders due`} className="icon-button">
                <Bell size={20} />
                {me.counts.reminders > 0 && <span className="notification-dot" />}
              </summary>
              <div className="popover-panel">
                <strong>{me.counts.reminders} reminders due</strong>
                <p>Keep the next deadline in sight.</p>
                <Link to="/calendar">
                  Open Calendar <ArrowUpRight size={14} />
                </Link>
              </div>
            </details>
            <span className="topbar-divider" />
            <details className="popover user-menu">
              <summary>
                <span className="sr-only">Your account: </span>
                <span className="avatar" aria-hidden="true">
                  {me.user.name
                    .split(' ')
                    .map((n) => n[0])
                    .slice(0, 2)
                    .join('')}
                </span>
                <span className="user-name">
                  {me.user.name}
                  <small>{roleLabels[me.role]}</small>
                </span>
                <ChevronDown size={14} />
              </summary>
              <div className="popover-panel">
                <strong>{me.user.name}</strong>
                <p>
                  {roleLabels[me.role]} · {me.club.name}
                </p>
                <Link to="/handover">Start your role / handover</Link>
                <Link to="/settings">{isPresident ? 'Settings' : 'View club settings'}</Link>
                {api.mode === 'demo' && (
                  <label className="field">
                    <span>Preview as</span>
                    <select
                      aria-label="Preview role"
                      value={me.role}
                      onChange={(e) => {
                        switchDemo({ club: me.club.id, role: e.target.value as typeof me.role });
                        navigate('/events');
                      }}
                    >
                      {roles.map((role) => (
                        <option key={role} value={role}>
                          {roleLabels[role]}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <button className="text-button" onClick={signOut} disabled={signingOut}>
                  <LogOut size={15} /> {signingOut ? 'Signing out…' : 'Sign out'}
                </button>
              </div>
            </details>
          </div>
        </header>
        {offline && (
          <div role="alert" className="connection-banner">
            Can't reach ClubOps. Your edits are kept on this page.
          </div>
        )}
        {api.mode === 'demo' && (
          <div className="demo-strip">
            <span>DEMO WORKSPACE</span> Sample club data · nothing is sent to OSA, Google or a
            sponsor.
          </div>
        )}
        {me.role === 'adviser' && (
          <section className="read-only-strip" aria-label="Adviser access">
            Adviser view · browse your club's workspace with read-only access.
          </section>
        )}
        <main
          id="main"
          className="page"
          key={`${api.mode}:${me.club.id}:${me.user.member_id}:${me.role}`}
        >
          <RoleTour />
          <Outlet />
        </main>
        <footer className="page-footer">
          <span>
            ClubOps <span>·</span> More club. Less admin.
          </span>
          <span>
            Made for your cabinet <span className="footer-dot" />
          </span>
        </footer>
      </div>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {navigation
          .filter((item) =>
            ['/chat', '/events', '/review', '/calendar', '/inbox', '/knowledge'].includes(item.to),
          )
          .map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to}>
              <span>
                <Icon size={21} />
                {to === '/review' && me.counts.review > 0 && <b>{me.counts.review}</b>}
              </span>
              {label}
            </NavLink>
          ))}
      </nav>
    </div>
  );
}

function NotFound() {
  return (
    <>
      <PageHeading
        eyebrow="404"
        title="This page took a wrong turn."
        description="It may have moved, or the link may be incomplete."
      />
      <Link to="/events" className="button primary">
        Back to Events <ArrowRight size={16} />
      </Link>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Shell />}>
            <Route index element={<Navigate to="/events" replace />} />
            <Route path="events" element={<Events />} />
            <Route path="events/new" element={<NewEvent />} />
            <Route path="events/:id" element={<EventDetail />} />
            <Route path="chat" element={<Chat />} />
            <Route path="review" element={<Review />} />
            <Route path="calendar" element={<Calendar />} />
            <Route path="inbox" element={<Inbox />} />
            <Route path="knowledge" element={<Knowledge />} />
            <Route path="knowledge/:id" element={<KnowledgeFact />} />
            <Route path="handover" element={<Handover />} />
            <Route path="settings" element={<Settings />} />
            <Route path="setup" element={<Setup />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AppProvider>
    </BrowserRouter>
  );
}
