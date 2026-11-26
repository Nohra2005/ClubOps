import { Link } from 'react-router';
import { useApp } from '../AppContext';
import { roleLabels, type EventSummary, type Me } from '../api/types';
import { ErrorNotice, Resource, SourceChip } from '../components/ui';
import { useAction, useResource } from '../hooks';
import { formatDate } from '../lib';

interface EventResource {
  value?: EventSummary[];
  loading: boolean;
  error?: string;
  reload: () => void;
}

export default function TermArrival({ events }: { events: EventResource }) {
  const { api, me } = useApp();
  const term = api.mode === 'demo' ? me.demo_term : undefined;
  if (!term || term.acknowledged || me.role === 'adviser') return null;
  return <IncomingBrief term={term} events={events} />;
}

function IncomingBrief({
  term,
  events,
}: {
  term: NonNullable<Me['demo_term']>;
  events: EventResource;
}) {
  const { api, me, refresh } = useApp();
  const action = useAction();
  const guide = useResource(() => api.handover(me.role), [api, me.role, term.id]);
  const open = (events.value ?? []).filter(
    (event) => !['done', 'closed', 'cancelled'].includes(event.status),
  );
  const references = (guide.value?.sections ?? [])
    .flatMap((section) => {
      const entry = section.entries.find((candidate) => candidate.text.trim());
      return entry ? [{ title: section.title, entry }] : [];
    })
    .slice(0, 2);
  return (
    <section className="panel term-arrival" aria-label="Your new cabinet term">
      <h2>{term.label} handover</h2>
      <p className="inline-note">
        {roleLabels[me.role]} · {formatDate(term.start_date, true)} –{' '}
        {formatDate(term.end_date, true)}
      </p>
      <div className="incoming-brief-grid">
        <section aria-label="Inherited work">
          <h3>Work in progress</h3>
          <Resource loading={events.loading} error={events.error} retry={events.reload}>
            {open.length ? (
              <ul className="turnover-work">
                {open.slice(0, 3).map((event) => (
                  <li key={event.event_id}>
                    <Link to={`/events/${encodeURIComponent(event.event_id)}`}>{event.title}</Link>
                    <span>{Math.max(0, event.task_count - event.tasks_done)} unfinished tasks</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No active events to carry forward.</p>
            )}
            <Link to="/review">{me.counts.review} items awaiting review</Link>
          </Resource>
        </section>
        <section aria-label="Approved role references">
          <h3>{roleLabels[me.role]} reference</h3>
          <Resource loading={guide.loading} error={guide.error} retry={guide.reload}>
            {references.length ? (
              references.map(({ title, entry }, index) => (
                <div className="incoming-reference" key={`${title}:${index}`}>
                  <strong>{title}</strong>
                  <p>{entry.text}</p>
                  <div className="source-list">
                    {(entry.sources?.length ? entry.sources : [entry.source]).map(
                      (source, sourceIndex) => (
                        <SourceChip key={`${source.item_id}:${sourceIndex}`} source={source} />
                      ),
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p>No approved role references yet.</p>
            )}
          </Resource>
        </section>
      </div>
      <div className="form-actions">
        <Link className="button" to="/calendar">
          See commitments
        </Link>
        <Link className="button" to="/handover">
          Read your role reference
        </Link>
        <button
          className="button primary"
          disabled={action.pending}
          onClick={async () => {
            const result = await action.run(() =>
              api.changeTurnover({ kind: 'acknowledge', id: term.id }),
            );
            if (result.ok) refresh();
          }}
        >
          Continue to workspace
        </button>
      </div>
      <ErrorNotice message={action.error} />
    </section>
  );
}
