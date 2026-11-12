import { useId, useState } from 'react';
import { Link } from 'react-router';
import { Copy } from 'lucide-react';
import { useApp } from '../AppContext';
import { ErrorNotice } from '../components/ui';
import { useAction } from '../hooks';
import { copyText } from '../lib';
import { PREVIEW_CODE, type ConnectionState } from './preview';
import { useInboxPreview } from './useInboxPreview';

export function PreviewNotice() {
  return (
    <p className="notice warning">
      Synthetic preview · no email, Google connection, model call or calendar change. Progress stays
      in this tab and resets on reload or account change.
    </p>
  );
}
const connectionText: Record<ConnectionState, string> = {
  disconnected: 'Disconnected. The president starts the Google connection.',
  pending: 'Waiting for Google authorization. No account is connected yet.',
  connected: 'Sample inbox connection ready. Shared-calendar reader access is checked separately.',
  expired:
    'Authorization expired. The president needs to reconnect. The Google app is in Testing mode.',
  failed: 'Connection failed. Nothing was read. Retry after the president checks the connection.',
};
function DemoForwarding() {
  const { state, dispatch, canEdit, isPresident } = useInboxPreview();
  const { notify } = useApp();
  const [address, setAddress] = useState('');
  const [code, setCode] = useState('');
  const action = useAction();
  const id = useId();
  // Reserved example domain; deliberately never construct a real club inbox from a client-side ID.
  const forwarding = 'clubops+sample-club@inbox.example';
  return (
    <>
      <PreviewNotice />
      <div className="inbox-preview-grid">
        <div>
          <h3>Club inbox connection</h3>
          <p role="status">{connectionText[state.connection]}</p>
          <p className="inline-note">
            One club calendar. Members receive invites in Gmail; ClubOps does not access members’
            own calendars.
          </p>
          {isPresident && (
            <label className="field">
              <span>Demo connection state</span>
              <select
                value={state.connection}
                onChange={(e) =>
                  dispatch({ type: 'connection', value: e.target.value as ConnectionState })
                }
              >
                {Object.keys(connectionText).map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
          )}
          <p>
            Shared-calendar reader access: <strong>{state.reader}</strong>
          </p>
          {isPresident && (
            <label className="field">
              <span>Demo reader access</span>
              <select
                value={state.reader}
                onChange={(e) =>
                  dispatch({ type: 'reader', value: e.target.value as typeof state.reader })
                }
              >
                <option>pending</option>
                <option>granted</option>
                <option>failed</option>
              </select>
            </label>
          )}
        </div>
        <div>
          <h3>Prove your sending address</h3>
          <p>Add your own extra sending address. A typed address alone is not verified.</p>
          <p>
            Sample address status: <strong>{state.verification}</strong>
            {state.address && <> · {state.address}</>}
          </p>
          {canEdit && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                dispatch({ type: 'address', value: address });
                setCode('');
              }}
            >
              <label className="field">
                <span>Sample sending address</span>
                <input
                  type="email"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="member@example.com"
                  required
                  maxLength={254}
                />
              </label>
              <button className="button small" type="submit">
                Start sample verification
              </button>
            </form>
          )}
          {state.verification === 'pending' && canEdit && (
            <>
              <p>
                Email this code from that address to the club’s forwarding address in the live flow.
                In this preview, use the sample code: <code>{PREVIEW_CODE}</code>. No email is sent
                or checked here.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  dispatch({ type: 'verify', code });
                }}
              >
                <label className="field">
                  <span>Sample verification code</span>
                  <input
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    autoComplete="off"
                    required
                    maxLength={32}
                  />
                </label>
                <button className="button small" type="submit">
                  Simulate received code
                </button>
              </form>
              <button
                className="text-button"
                onClick={() => dispatch({ type: 'expire_verification' })}
              >
                Simulate code expiry
              </button>
            </>
          )}
        </div>
      </div>
      <h3>Forward only OSA messages from Outlook</h3>
      <div className="inbox-address">
        <code>{forwarding}</code>
        <button
          className="icon-button"
          aria-label="Copy sample forwarding address"
          onClick={async () => {
            const result = await action.run(() => copyText(forwarding));
            if (result.ok) notify('Sample address copied. It cannot receive email.');
          }}
        >
          <Copy size={14} />
        </button>
      </div>
      <ol className="forwarding-steps">
        <li>
          Ask the president or operator for your club’s actual +tag address. The address above is an
          example only.
        </li>
        <li>
          In Outlook, open Settings → Mail → Rules and add a rule for the OSA senders your president
          confirms. Avoid forwarding every message.
        </li>
        <li>
          Choose Forward to the club’s +tag address. Keep the original From, Sent, To, Cc and
          Subject headers. Review the rule before saving it yourself.
        </li>
        <li>
          Forward one authorized OSA message, then test below. Fetching and sender checks are free;
          reading its contents with AI requires a separate click.
        </li>
      </ol>
      {canEdit && (
        <button className="button small" onClick={() => dispatch({ type: 'test_forwarding' })}>
          Test my forwarding
        </button>
      )}
      <p role="status" id={`${id}-test`}>
        Forwarding test: <strong>{state.forwardingTest.replaceAll('_', ' ')}</strong>
      </p>
      {state.forwardingTest === 'waiting' && canEdit && (
        <div className="form-actions">
          <button
            className="button small"
            onClick={() => dispatch({ type: 'test_result', value: 'passed' })}
          >
            Simulate test received
          </button>
          <button
            className="button small"
            onClick={() => dispatch({ type: 'test_result', value: 'failed' })}
          >
            Simulate test failure
          </button>
        </div>
      )}
      <p className="inline-note">
        A passed forwarding test verifies delivery only; it approves no facts. Private OSA sender
        lists and Google tokens stay on the server.
      </p>
      <Link className="text-button" to="/inbox">
        Open waiting email →
      </Link>
      <ErrorNotice message={state.error || action.error} />
    </>
  );
}
export default function ForwardingPanel() {
  const { api } = useApp();
  return (
    <section className="panel" id="forwarding" aria-label="Forwarding setup">
      <div className="panel-header">
        <div>
          <h2>Forwarding and connections</h2>
          <p>Verify who forwards, then choose which messages ClubOps reads.</p>
        </div>
      </div>
      {api.mode === 'demo' ? (
        <DemoForwarding />
      ) : (
        <p className="inline-note">
          Forwarding setup is not available on this server yet. Ask your president for the club’s
          verified forwarding address. No address or verification code is generated here.
        </p>
      )}
    </section>
  );
}
