import { useState } from 'react';
import { Link } from 'react-router';
import { useApp } from '../AppContext';
import { ErrorNotice, Modal, PageHeading, Resource } from '../components/ui';
import { PreviewNotice } from '../inbox/ForwardingPanel';
import { skipReasons } from '../inbox/preview';
import { useInboxPreview } from '../inbox/useInboxPreview';
import { useAction, useResource } from '../hooks';
import type { WaitingEmail } from '../inbox/http-metadata';

function HttpInbox() {
  const { api, refresh } = useApp();
  const waiting = useResource(() => api.inbox(), [api]);
  const skipped = useResource(() => api.skippedInbox(), [api]);
  const read = useAction();
  const release = useAction();
  const [selected, setSelected] = useState<WaitingEmail>();
  const [completed, setCompleted] = useState<string[]>([]);
  const [unconfirmed, setUnconfirmed] = useState<{ id: string; snapshot?: WaitingEmail[] }[]>([]);
  const [feedback, setFeedback] = useState<string>();
  const [reasons, setReasons] = useState<string[]>([]);
  const blocked = (id: string) =>
    unconfirmed.some(
      (entry) =>
        entry.id === id &&
        (!waiting.value ||
          waiting.value === entry.snapshot ||
          waiting.loading ||
          Boolean(waiting.error)),
    );
  async function readAnyway(id: string) {
    const result = await release.run(() => api.allowInbox(id));
    if (!result.ok) return;
    setFeedback('Released. It is in the waiting list above; nothing has been read yet.');
    waiting.reload();
    skipped.reload();
  }
  async function confirmRead() {
    if (!selected) return;
    const message = selected;
    const result = await read.run(async () => {
      try {
        return await api.captureInbox(message.id);
      } catch (error) {
        setUnconfirmed((previous) => [
          ...previous.filter((entry) => entry.id !== message.id),
          { id: message.id, snapshot: waiting.value },
        ]);
        throw error;
      }
    });
    if (!result.ok) return;
    const cards = new Set(result.value.proposals).size;
    setCompleted((previous) => [...new Set([...previous, message.id])]);
    setUnconfirmed((previous) => previous.filter((entry) => entry.id !== message.id));
    const added = new Set(result.value.applied ?? []).size;
    setFeedback(
      added
        ? `Read result received. ${added} new fact(s) added to Knowledge. ${cards} change(s) to existing rules or odd cases wait in Review for your check.`
        : cards
          ? `Read result received. ${cards} Review card(s) proposed; none approved.`
          : 'Read result received. No facts were proposed; no fact was approved.',
    );
    setReasons(result.value.skipped);
    setSelected(undefined);
    waiting.reload();
    refresh();
  }
  return (
    <>
      <p className="notice">
        Listing and refreshing metadata are free. An AI read starts only after a separate
        confirmation and may cost money. Forwarding changes are not connected here yet.
      </p>
      {feedback && <p role="status">{feedback}</p>}
      {reasons.length > 0 && (
        <ul>
          {reasons.map((reason, index) => (
            <li key={index}>{reason}</li>
          ))}
        </ul>
      )}
      {!selected && <ErrorNotice message={read.error} />}
      <section className="panel" aria-label="Waiting email">
        <div className="panel-header">
          <h2>Waiting email</h2>
          <button
            className="button small"
            disabled={waiting.loading || read.pending}
            onClick={waiting.reload}
          >
            Refresh waiting email
          </button>
        </div>
        <Resource loading={waiting.loading} error={waiting.error} retry={waiting.reload}>
          {waiting.value?.length === 0 && <p>No waiting email.</p>}
          <div className="inbox-message-list">
            {waiting.value?.map((message) => (
              <article className="inbox-message" key={message.id}>
                <h3>{message.subject || '(No subject)'}</h3>
                <p>Received: {message.date || 'Not supplied'}</p>
                <p>Forwarded by: {message.forwarded_by || 'Not supplied'}</p>
                {completed.includes(message.id) ? (
                  <p>Read result already received. Check Review; no repeat read from this page.</p>
                ) : (
                  <button
                    className="button small"
                    disabled={read.pending || blocked(message.id)}
                    onClick={() => {
                      read.clearError();
                      setSelected(message);
                    }}
                  >
                    {blocked(message.id) ? 'Refresh before retrying' : 'Read this · costs money'}
                  </button>
                )}
              </article>
            ))}
          </div>
        </Resource>
      </section>
      <section className="panel" aria-label="Skipped email">
        <div className="panel-header">
          <h2>Skipped by free checks</h2>
          <button className="button small" disabled={skipped.loading} onClick={skipped.reload}>
            Refresh skipped email
          </button>
        </div>
        <p>These messages were refused before a model read. The server supplies each reason.</p>
        <ErrorNotice message={release.error} />
        <Resource loading={skipped.loading} error={skipped.error} retry={skipped.reload}>
          {skipped.value?.length === 0 && <p>No skipped email.</p>}
          <div className="inbox-message-list">
            {skipped.value?.map((message) => (
              <article className="inbox-message" key={message.id}>
                <h3>{message.subject || '(No subject)'}</h3>
                <p>{message.why}</p>
                <p className="inline-note">Reason: {message.reason}</p>
                {message.reason === 'original_sender_not_osa' && (
                  <button
                    className="button small"
                    disabled={release.pending}
                    onClick={() => void readAnyway(message.id)}
                  >
                    Read anyway
                  </button>
                )}
              </article>
            ))}
          </div>
        </Resource>
      </section>
      <Link to="/settings#forwarding">Check forwarding setup →</Link>
      <Link className="text-button" to="/review">
        Check Review →
      </Link>
      <Modal
        open={Boolean(selected)}
        title="Read this email with AI?"
        onClose={() => {
          if (!read.pending) setSelected(undefined);
        }}
      >
        <p>{selected?.subject || '(No subject)'}</p>
        <p>
          This starts a paid AI read. No price estimate is available. Any proposed facts go to
          Review; this does not approve them.
        </p>
        <p>
          If the result is not confirmed, refresh Inbox and check Review before choosing another
          paid attempt. Refreshing does not read the email.
        </p>
        <ErrorNotice message={read.error} />
        <div className="form-actions">
          <button
            className="button primary"
            disabled={read.pending || !selected || blocked(selected.id)}
            onClick={confirmRead}
          >
            {read.pending ? 'Reading…' : 'Confirm paid read'}
          </button>
          <button className="button" disabled={read.pending} onClick={() => setSelected(undefined)}>
            Cancel
          </button>
        </div>
      </Modal>
    </>
  );
}

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
  const { api, canEdit, me } = useApp();
  return (
    <>
      <PageHeading
        title="Inbox"
        description="Authorized OSA forwards wait here until your cabinet chooses what to read."
      />
      {api.mode === 'demo' ? (
        <DemoInbox />
      ) : canEdit ? (
        <HttpInbox key={`${me.club.id}:${me.user.member_id}`} />
      ) : (
        <section className="panel">
          <h2>Inbox is for cabinet members.</h2>
          <p>This adviser session does not request private inbox metadata or read email.</p>
        </section>
      )}
    </>
  );
}
