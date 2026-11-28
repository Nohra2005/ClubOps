import { useState } from 'react';
import { Link } from 'react-router';
import { useApp } from '../AppContext';
import { roleLabels, roles, type EventSummary } from '../api/types';
import { ErrorNotice, Modal, PageHeading, Resource } from '../components/ui';
import { useAction, useResource } from '../hooks';
import { formatDate } from '../lib';
import { localDate, type TurnoverAction } from '../turnover/model';

import PrepareTerm from '../turnover/PrepareTerm';
import Roster from '../turnover/Roster';

const cabinetRoles = roles.filter((role) => role !== 'adviser');

function WorkToCarry({
  events,
}: {
  events: { value?: EventSummary[]; loading: boolean; error?: string; reload: () => void };
}) {
  const { me } = useApp();
  const open = events.value?.filter(
    (event) => !['done', 'closed', 'cancelled'].includes(event.status),
  );
  return (
    <section className="panel" aria-label="Work to carry forward">
      <h2>Work to carry forward</h2>
      <Resource loading={events.loading} error={events.error} retry={events.reload}>
        {open?.length === 0 && <p>No active events.</p>}
        <ul className="turnover-work">
          {open?.map((event) => (
            <li key={event.event_id}>
              <Link to={`/events/${encodeURIComponent(event.event_id)}`}>{event.title}</Link>
              <span>
                {Math.max(0, event.task_count - event.tasks_done)} unfinished tasks
                {event.overdue_tasks > 0 ? `, ${event.overdue_tasks} overdue` : ''}
              </span>
            </li>
          ))}
        </ul>
      </Resource>
      <p>
        Tasks keep their assigned roles.{' '}
        <Link to="/review">{me.counts.review} items await review.</Link>
      </p>
      <p>
        Approved knowledge keeps its sources and expiry dates.{' '}
        <Link to="/handover">Read the role references</Link>.
      </p>
    </section>
  );
}

function DemoTurnover() {
  const { api, refresh } = useApp();
  const state = useResource(() => api.turnover(), [api]);
  const events = useResource(() => api.events(), [api]);
  const action = useAction();
  const [editing, setEditing] = useState(false);
  const [starting, setStarting] = useState(false);
  const [checked, setChecked] = useState(false);
  const [confirm, setConfirm] = useState<'activate' | 'cancel' | null>(null);
  const [confirmation, setConfirmation] = useState('');
  const value = state.value;
  const draft = value?.draft;
  async function change(next: TurnoverAction) {
    const result = await action.run(() => api.changeTurnover(next));
    if (result.ok) {
      setEditing(false);
      setStarting(false);
      setChecked(false);
      setConfirm(null);
      setConfirmation('');
      state.reload();
      if (next.kind === 'activate') refresh();
    }
  }
  return (
    <div className="turnover-flow">
      <p className="inline-note">Demo: saves in this browser; no invitations are sent.</p>
      <Resource loading={state.loading} error={state.error} retry={state.reload}>
        {value && (
          <>
            {value.active && (
              <section className="panel">
                <h2>Active term: {value.active.label}</h2>
                <p>
                  {formatDate(value.active.start_date, true)} –{' '}
                  {formatDate(value.active.end_date, true)}
                </p>
                <Roster members={value.active.members} />
                <div className="form-actions">
                  <Link className="button primary" to="/events">
                    Open workspace
                  </Link>
                  <Link className="button" to="/settings#cabinet">
                    View cabinet
                  </Link>
                </div>
                <details>
                  <summary>Previous cabinet</summary>
                  <Roster members={value.active.previous_members} />
                </details>
              </section>
            )}
            {!draft && value.active && !starting ? (
              <button className="button" onClick={() => setStarting(true)}>
                Prepare next turnover
              </button>
            ) : !draft || editing ? (
              <PrepareTerm
                key={`${draft?.id ?? 'next'}:${value.revision}`}
                initial={draft ?? undefined}
                pending={action.pending}
                save={(input) => void change({ kind: 'save', revision: value.revision, input })}
              />
            ) : (
              <>
                <section className="panel">
                  <div className="panel-header">
                    <h2>{draft.label}</h2>
                    <span>{draft.phase === 'ready' ? 'Ready to activate' : 'Draft'}</span>
                  </div>
                  <p>
                    {formatDate(draft.start_date, true)} – {formatDate(draft.end_date, true)}
                  </p>
                  <h3>Incoming cabinet</h3>
                  <Roster members={draft.officers} />
                  <p>
                    Unassigned roles:{' '}
                    {cabinetRoles
                      .filter((role) => !draft.officers.some((officer) => officer.role === role))
                      .map((role) => roleLabels[role])
                      .join(', ') || 'None'}
                    .
                  </p>
                  <p className="inline-note">Current advisers stay on the cabinet.</p>
                  <div className="form-actions">
                    <button
                      className="button"
                      disabled={action.pending}
                      onClick={() => {
                        setEditing(true);
                        action.clearError();
                      }}
                    >
                      Edit draft
                    </button>
                    <button
                      className="text-button"
                      disabled={action.pending}
                      onClick={() => setConfirm('cancel')}
                    >
                      Cancel turnover
                    </button>
                  </div>
                </section>
                <WorkToCarry events={events} />
                <section className="panel">
                  <h2>
                    {draft.phase === 'ready' ? 'Activate the next cabinet' : 'Review the handover'}
                  </h2>
                  {draft.phase === 'draft' ? (
                    <>
                      <label className="check-line">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(event) => setChecked(event.target.checked)}
                        />
                        I reviewed the incoming cabinet, vacancies and outstanding work.
                      </label>
                      <button
                        className="button primary"
                        disabled={!checked || action.pending || events.loading || !!events.error}
                        onClick={() =>
                          void change({ kind: 'review', revision: value.revision, id: draft.id })
                        }
                      >
                        Mark ready
                      </button>
                    </>
                  ) : (
                    <>
                      <p>
                        Activation replaces the current officers and keeps a record of their
                        cabinet. Work and knowledge carry forward.
                      </p>
                      {(localDate() < draft.start_date || localDate() > draft.end_date) && (
                        <p role="status">
                          Activate between {formatDate(draft.start_date, true)} and{' '}
                          {formatDate(draft.end_date, true)}. Dates do not activate a term
                          automatically.
                        </p>
                      )}
                      <button
                        className="button primary"
                        disabled={
                          action.pending ||
                          events.loading ||
                          !!events.error ||
                          localDate() < draft.start_date ||
                          localDate() > draft.end_date
                        }
                        onClick={() => {
                          setConfirmation('');
                          setConfirm('activate');
                        }}
                      >
                        Activate demo term
                      </button>
                    </>
                  )}
                </section>
              </>
            )}
            {value.history.length > 0 && (
              <section className="panel">
                <h2>Previous terms</h2>
                {[...value.history].reverse().map((term) => (
                  <details key={term.id}>
                    <summary>
                      {term.label} · {formatDate(term.start_date, true)} –{' '}
                      {formatDate(term.end_date, true)}
                    </summary>
                    <Roster members={term.members} />
                  </details>
                ))}
              </section>
            )}
          </>
        )}
      </Resource>
      {!confirm && <ErrorNotice message={action.error} />}
      <button
        className="text-button"
        disabled={action.pending || state.loading}
        onClick={state.reload}
      >
        Refresh turnover
      </button>
      <Modal
        open={confirm !== null}
        title={confirm === 'activate' ? 'Activate this cabinet?' : 'Cancel this turnover?'}
        onClose={() => {
          if (!action.pending) setConfirm(null);
        }}
      >
        {confirm === 'activate' ? (
          <>
            <p>
              The demo will switch to the incoming cabinet for <strong>{draft?.label}</strong>. The
              former cabinet remains in history.
            </p>
            <label className="field">
              <span>Type the term name to confirm</span>
              <input
                autoComplete="off"
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
              />
            </label>
          </>
        ) : (
          <p>The pending draft will be removed. Your active cabinet stays unchanged.</p>
        )}
        <ErrorNotice message={action.error} />
        <div className="form-actions">
          <button
            className="button primary"
            disabled={
              action.pending ||
              !draft ||
              (confirm === 'activate' && confirmation.trim() !== draft.label)
            }
            onClick={() => {
              if (draft && value && confirm)
                void change({ kind: confirm, id: draft.id, revision: value.revision });
            }}
          >
            {confirm === 'activate' ? 'Confirm activation' : 'Confirm cancellation'}
          </button>
          <button className="button" disabled={action.pending} onClick={() => setConfirm(null)}>
            Keep working
          </button>
        </div>
      </Modal>
    </div>
  );
}

export default function Turnover() {
  const { api, isPresident } = useApp();
  return (
    <>
      <PageHeading title="Cabinet turnover" />
      {!isPresident ? (
        <p>
          Only the president manages cabinet turnover.{' '}
          <Link to="/events">Return to your workspace</Link>.
        </p>
      ) : api.mode === 'demo' ? (
        <DemoTurnover />
      ) : (
        <section className="panel">
          <h2>Prepare the next cabinet</h2>
          <p>Term activation is not available yet. Your current cabinet remains active.</p>
          <div className="form-actions">
            <Link className="button" to="/settings#cabinet">
              Manage current cabinet
            </Link>
            <Link className="button" to="/handover">
              Read role references
            </Link>
          </div>
        </section>
      )}
    </>
  );
}
