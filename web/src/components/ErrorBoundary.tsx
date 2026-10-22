import { Component, type ReactNode } from 'react';

export class ErrorBoundary extends Component<{ children: ReactNode },{ failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <main className="boot"><h1>This page couldn't open.</h1><p>Your saved work is still here. Reload the page to try again.</p><button className="button primary" onClick={() => window.location.reload()}>Reload page</button><a className="button" href="/events">Back to Events</a></main> : this.props.children; }
}
