import { useState } from 'react';
import { Link } from 'react-router';
import { ArrowRight, ArrowUpRight, CalendarDays, Check, Flag, MapPin, Plus } from 'lucide-react';
import { useApp } from '../AppContext';
import type { EventSummary } from '../api/types';
import { DEMO_TODAY } from '../api/fixtures';
import { PageHeading, EmptyState, FilterTabs, Resource, StatusBadge } from '../components/ui';
import { useResource } from '../hooks';
import { formatDate, formatTime } from '../lib';

function EventCard({ event }: { event: EventSummary }) {
  const day = new Date(event.start).getDate();
  const month = new Date(event.start).toLocaleDateString('en-GB', { month: 'short' });
  return (
    <Link
      to={`/events/${encodeURIComponent(event.event_id)}`}
      className={`event-card${event.status === 'closed' ? ' event-past' : ''}`}
    >
      <div className="event-card-top">
        <span className="event-category">
          <Flag size={12} /> {event.event_type === 'weekly_run' ? 'CLUB RUN' : 'CLUB EVENT'}
        </span>
        <StatusBadge status={event.status} />
      </div>
      <div className="event-card-main">
        <div className="event-date">
          <span>{month}</span>
          <strong>{day}</strong>
        </div>
        <div>
          <h3>{event.title}</h3>
          <p>
            <MapPin size={11} />
            {event.venue}
          </p>
          <p>
            <CalendarDays size={11} />
            {formatDate(event.start)} · {formatTime(event.start)}
          </p>
        </div>
      </div>
      <div className="event-card-bottom">
        <div className="task-progress">
          <div className="progress-track">
            <span
              style={{ width: `${(event.tasks_done / Math.max(1, event.task_count)) * 100}%` }}
            />
          </div>
          <span>
            {event.tasks_done} of {event.task_count} tasks done
          </span>
        </div>
        {event.overdue_tasks > 0 && (
          <span className="overdue-note">
            <i />
            {event.overdue_tasks} overdue
          </span>
        )}
        <ArrowUpRight size={17} />
      </div>
    </Link>
  );
}

export default function Events() {
  const { api, me, canEdit } = useApp();
  const events = useResource(() => api.events(), [api]);
  const [filter, setFilter] = useState('all');
  const list = events.value ?? [];
  const groups = [
    {
      value: 'upcoming',
      label: 'Upcoming',
      note: 'A few good things to look forward to.',
      events: list.filter((e) => !['done', 'closed', 'cancelled'].includes(e.status)),
    },
    {
      value: 'followup',
      label: 'Needs after-event form',
      note: 'Keep the lessons before they slip away.',
      events: list.filter((e) => e.status === 'done'),
    },
    {
      value: 'past',
      label: 'Past',
      note: 'Done, documented, and ready for the next team.',
      events: list.filter((e) => ['closed', 'cancelled'].includes(e.status)),
    },
  ];
  return (
    <>
      <PageHeading
        eyebrow="YOUR CLUB, IN MOTION"
        title="Events"
        description="From the first idea to the last lesson. Keep every event moving."
        action={
          canEdit && (
            <Link to="/events/new" className="button primary">
              <Plus size={15} /> Plan an event
            </Link>
          )
        }
      />
      {!events.error && (
        <div className="event-hero">
          <div>
            <div className="hero-kicker">
              <span /> A LITTLE LESS ADMIN. A LOT MORE CLUB.
            </div>
            <h2>
              Good events start
              <br />
              with a clear plan.
            </h2>
            <p>
              Bring the idea. ClubOps helps you find the details,
              <br className="desktop-break" /> the deadlines, and the lessons worth keeping.
            </p>
            {canEdit ? (
              <Link to="/events/new" className="button hero-button">
                Let's plan something <ArrowRight size={15} />
              </Link>
            ) : (
              <Link to="/handover" className="button hero-button">
                Explore your club's guide <ArrowRight size={15} />
              </Link>
            )}
            <span className="hero-footnote">
              <Check size={12} /> Drafted by ClubOps. Approved by your cabinet.
            </span>
          </div>
          <div className="hero-plan" aria-hidden="true">
            <div className="hero-plan-label">
              <span className="mini-symbol">c.</span> THE NEXT GOOD THING
            </div>
            <div className="hero-plan-title">
              An idea. A plan.
              <br />A day to remember.
            </div>
            <div className="hero-plan-row">
              <span className="hero-check">
                <Check size={11} />
              </span>{' '}
              The right approvals<span className="mini-pill">Checked</span>
            </div>
            <div className="hero-plan-row">
              <span className="hero-check">
                <Check size={11} />
              </span>{' '}
              A deadline for every task
            </div>
            <div className="hero-plan-row">
              <span className="hero-check">
                <Check size={11} />
              </span>{' '}
              Your club's know-how
            </div>
            <div className="hero-plan-footer">
              THE FINAL SAY IS ALWAYS YOURS <ArrowUpRight size={16} />
            </div>
          </div>
        </div>
      )}
      <div className="events-overview">
        <div>
          <span className="overview-icon">
            <CalendarDays size={17} />
          </span>
          <strong>{groups[0].events.length}</strong>
          <span>upcoming events</span>
        </div>
        <div>
          <span className="overview-icon amber">
            <Flag size={17} />
          </span>
          <strong>{list.filter((e) => e.overdue_tasks > 0).length}</strong>
          <span>need your attention</span>
        </div>
        <Link to="/review">
          <span className="overview-icon">
            <Check size={17} />
          </span>
          <strong>{me.counts.review}</strong>
          <span>waiting in Review</span>
          <ArrowUpRight size={14} />
        </Link>
      </div>
      <div className="events-list-toolbar">
        <FilterTabs
          value={filter}
          label="Filter events"
          onChange={setFilter}
          options={[
            { value: 'all', label: 'All events', count: list.length },
            ...groups.map((g) => ({
              value: g.value,
              label: g.value === 'followup' ? 'Follow-up' : g.label,
              count: g.events.length,
            })),
          ]}
        />
        <span className="list-date">{formatDate(DEMO_TODAY, true)}</span>
      </div>
      <Resource loading={events.loading} error={events.error} retry={events.reload}>
        {list.length === 0 ? (
          <EmptyState
            title="No events yet."
            description="Your next club memory starts with an idea."
            action={
              canEdit && (
                <Link to="/events/new" className="button primary">
                  <Plus size={14} /> Plan an event
                </Link>
              )
            }
          />
        ) : (
          groups
            .filter((g) => filter === 'all' || g.value === filter)
            .map((group) => (
              <section className="event-group" key={group.value}>
                <div className="group-heading">
                  <h2>
                    {group.label}
                    <span>{group.events.length}</span>
                  </h2>
                  <p>{group.note}</p>
                </div>
                {group.events.length ? (
                  <div className="event-grid">
                    {group.events.map((event) => (
                      <EventCard key={event.event_id} event={event} />
                    ))}
                  </div>
                ) : (
                  <p className="inline-note">Nothing here right now.</p>
                )}
              </section>
            ))
        )}
      </Resource>
    </>
  );
}
