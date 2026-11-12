import { useState } from 'react';
import { Link } from 'react-router';
import { useApp } from '../AppContext';
import { ErrorNotice, Modal, PageHeading } from '../components/ui';
import { PreviewNotice } from '../inbox/ForwardingPanel';
import { skipReasons } from '../inbox/preview';
import { useInboxPreview } from '../inbox/useInboxPreview';

function DemoInbox() {
  const { state, dispatch, canEdit } = useInboxPreview();
  const [selected, setSelected] = useState<string[]>([]);
  const readable = state.messages.filter((message) =>
    ['waiting', 'failed'].includes(message.status),
  );
  const failed = state.messages.filter((message) => message.status === 'failed').length;
  const completed = state.messages.filter((message) => message.status === 'read').length;
  return (
    <>
      <PreviewNotice />
      <section className="panel" aria-label="Waiting email">
        <div className="panel-header">
          <div>
            <h2>Waiting email</h2>
            <p>Fetching and sender checks are free. AI reads only after you confirm.</p>
          </div>
        </div>
        <p>
          Connection: <strong>{state.connection}</strong>.{' '}
          <Link to="/settings#forwarding">Check forwarding and connections →</Link>
        </p>
        <p className="inline-note">
          The two waiting samples represent messages that already passed server sender checks. They
          are independent of the verification practice in Settings. No private sender allowlist is
          displayed.
        </p>
        {canEdit && (
          <details className="preview-scenarios">
            <summary>Demo read outcomes</summary>
            <label className="field">
              <span>Next simulated read result</span>
              <select
                value={state.outcome}
                onChange={(e) =>
                  dispatch({ type: 'outcome', value: e.target.value as typeof state.outcome })
                }
              >
                <option value="success">All selected reads succeed</option>
                <option value="partial">Second sample fails; others succeed</option>
                <option value="failed">All selected reads fail</option>
              </select>
            </label>
          </details>
        )}
        {canEdit && readable.length > 0 && (
          <div className="form-actions">
            <button
              className="button small primary"
              disabled={state.connection !== 'connected'}
              onClick={() => setSelected(readable.map((message) => message.id))}
            >
              Read waiting email · costs money
            </button>
          </div>
        )}
        {state.connection !== 'connected' && (
          <p className="notice warning">
            Nothing can be read until the president connects or reconnects the inbox.
          </p>
        )}
        <div className="inbox-message-list">
          {state.messages.map((message) => (
            <article className="inbox-message" key={message.id} aria-label={message.subject}>
              <h3>{message.subject}</h3>
              <p>
                {message.received} · <strong>{message.status}</strong>
              </p>
              {message.reason && <p>{skipReasons[message.reason]}</p>}
              {message.status === 'read' && (
                <p>Sample fact proposed for Review. No fact approved; no second paid read.</p>
              )}
              {message.status === 'failed' && (
                <p role="status">
                  Read failed. Other successful messages are kept. Retry only this message when
                  ready.
                </p>
              )}
              {canEdit && ['waiting', 'failed'].includes(message.status) && (
                <button
                  className="button small"
                  disabled={state.connection !== 'connected'}
                  onClick={() => setSelected([message.id])}
                >
                  {message.status === 'failed'
                    ? 'Retry this read · costs money'
                    : 'Read this · costs money'}
                </button>
              )}
            </article>
          ))}
        </div>
        <p role="status">
          {completed} read · {failed} failed · {state.proposed} sample facts proposed, none
          approved.
        </p>
        <ErrorNotice message={state.error} />
        <Link className="text-button" to="/review">
          Review knowledge separately →
        </Link>
      </section>
      <Modal
        open={selected.length > 0}
        title="Read selected email?"
        onClose={() => setSelected([])}
      >
        <p>
          In the live flow, this calls AI and costs money. No charge estimate is available yet.
          Successful messages are not read again on retry.
        </p>
        <p>
          <strong>This is a synthetic preview:</strong> confirming simulates {selected.length}{' '}
          selected read{selected.length === 1 ? '' : 's'}. It makes no model call or payment and
          approves no fact.
        </p>
        <div className="form-actions">
          <button
            className="button primary"
            onClick={() => {
              dispatch({ type: 'read', ids: selected });
              setSelected([]);
            }}
          >
            Confirm simulated read
          </button>
          <button className="button" onClick={() => setSelected([])}>
            Cancel
          </button>
        </div>
      </Modal>
    </>
  );
}
export default function Inbox() {
  const { api } = useApp();
  return (
    <>
      <PageHeading
        eyebrow="FETCH FOR FREE, READ BY CHOICE"
        title="Inbox"
        description="Authorized OSA forwards wait here until your cabinet chooses what to read."
      />
      {api.mode === 'demo' ? (
        <DemoInbox />
      ) : (
        <section className="panel">
          <h2>Inbox integration is not available yet.</h2>
          <p>No email was fetched or read. Your existing knowledge and Review are unchanged.</p>
          <Link to="/settings#forwarding">Check forwarding setup →</Link>
        </section>
      )}
    </>
  );
}
