import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import { useApp } from '../AppContext';
import { useAction, useResource } from '../hooks';
import type { GoogleService } from '../api/google-connections';
import { ErrorNotice, Modal, Resource } from './ui';

const states = {
  not_set_up: 'Not configured on the server',
  not_connected: 'Not connected',
  connected: 'Connected',
  reconnect: 'Reconnect needed',
};
export default function GoogleConnectionPanel(props: {
  service: GoogleService;
  onFetched?: () => void;
}) {
  const { api, canEdit } = useApp();
  return api.mode === 'http' && canEdit ? <Connection {...props} /> : null;
}
function Connection({ service, onFetched }: { service: GoogleService; onFetched?: () => void }) {
  const { api, isPresident } = useApp();
  const connection = useResource(() => api.googleConnection(service), [api, service]);
  const action = useAction();
  const [search] = useSearchParams();
  const [disconnecting, setDisconnecting] = useState(false);
  const [receipt, setReceipt] = useState('');
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const status = connection.value;
  const manage = service === 'calendar' ? isPresident : status?.can_manage === true;
  const name = service === 'calendar' ? 'Google Calendar' : 'Gmail inbox';
  const callback = search.get(service === 'calendar' ? 'google' : 'gmail');
  async function connect() {
    const result = await action.run(() => api.connectGoogle(service));
    if (result.ok && alive.current) window.location.assign(result.value);
  }
  async function disconnect() {
    const result = await action.run(() => api.disconnectGoogle(service));
    if (!alive.current) return;
    if (result.ok) {
      setDisconnecting(false);
      setReceipt('Disconnect request completed. Checking status.');
    }
    connection.reload();
  }
  async function fetchMail() {
    const result = await action.run(() => api.fetchInbox());
    if (!alive.current) return;
    connection.reload();
    if (result.ok) {
      setReceipt(
        `Fetched: ${result.value.queued} queued, ${result.value.skipped} skipped, ${result.value.not_for_a_club} without a club.`,
      );
      onFetched?.();
    }
  }
  return (
    <section className="panel" aria-label={`${name} connection`}>
      <div className="panel-header">
        <h2>{name}</h2>
        <button
          className="text-button"
          disabled={action.pending || connection.loading}
          onClick={connection.reload}
        >
          Refresh status
        </button>
      </div>
      {callback === 'denied' && (
        <p role="status">Google connection cancelled. You can try again.</p>
      )}
      {callback === 'failed' && (
        <p role="alert">Google connection failed. Check the connection status and try again.</p>
      )}
      {callback === 'connected' && (
        <p role="status">
          {status?.state === 'connected'
            ? `${name} connected.`
            : 'Google returned. The connection has not been confirmed yet.'}
        </p>
      )}
      <Resource loading={connection.loading} error={connection.error} retry={connection.reload}>
        {status && (
          <>
            <p>
              <strong>{states[status.state]}</strong>
              {status.source === 'host' ? ' ? configured on the host' : ''}
            </p>
            {service === 'calendar' && Number(status.access_changes_waiting) > 0 && (
              <p>{status.access_changes_waiting} cabinet access change(s) waiting.</p>
            )}
            {status.state === 'not_set_up' && (
              <p className="inline-note">Ask the host administrator to configure {name}.</p>
            )}
            {!manage && (
              <p className="inline-note">
                {service === 'calendar'
                  ? 'A president manages this connection.'
                  : 'An operator manages this connection.'}
              </p>
            )}
            <div className="form-actions">
              {manage &&
                status.can_connect &&
                status.state !== 'not_set_up' &&
                status.state !== 'connected' && (
                  <button className="button" disabled={action.pending} onClick={connect}>
                    {status.state === 'reconnect' ? 'Reconnect' : 'Connect'} {name}
                  </button>
                )}
              {manage && ['connected', 'reconnect'].includes(status.state) && (
                <button
                  className="button"
                  disabled={action.pending}
                  onClick={() => setDisconnecting(true)}
                >
                  Disconnect {name}
                </button>
              )}
              {service === 'gmail' && (
                <button
                  className="button primary"
                  disabled={action.pending || status.state !== 'connected'}
                  onClick={fetchMail}
                >
                  {action.pending ? 'Working?' : 'Fetch email'}
                </button>
              )}
            </div>
            {service === 'gmail' && (
              <p className="inline-note">
                Fetching is free. AI reading needs a separate confirmation.
              </p>
            )}
          </>
        )}
      </Resource>
      {receipt && <p role="status">{receipt}</p>}
      {!disconnecting && <ErrorNotice message={action.error} />}
      <Modal
        open={disconnecting}
        title={`Disconnect ${name}?`}
        onClose={() => {
          if (!action.pending) setDisconnecting(false);
        }}
      >
        <p>
          {service === 'calendar'
            ? 'Queued calendar items stay queued. Google access will be cancelled.'
            : 'This disconnects the shared inbox used by the clubs. It does not delete email.'}
        </p>
        <ErrorNotice message={action.error} />
        <div className="form-actions">
          <button className="button" disabled={action.pending} onClick={disconnect}>
            Confirm disconnect
          </button>
          <button
            className="button"
            disabled={action.pending}
            onClick={() => setDisconnecting(false)}
          >
            Cancel
          </button>
        </div>
      </Modal>
    </section>
  );
}
