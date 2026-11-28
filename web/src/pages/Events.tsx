import { useState } from 'react';
import { Link } from 'react-router';
import { ArrowUpRight, CalendarDays, Check, Flag, MapPin, Plus } from 'lucide-react';
import { useApp } from '../AppContext';
import type { EventSummary } from '../api/types';
import { PageHeading, EmptyState, FilterTabs, Resource, StatusBadge } from '../components/ui';
import { useResource } from '../hooks';
import { formatDate, formatTime } from '../lib';
import TermArrival from '../turnover/TermArrival';

function EventCard({ event }: { event: EventSummary }) {
  const day = new Date(event.start).getDate();
  const month = new Date(event.start).toLocaleDateString('en-GB', { month: 'short' });
  return (
    <Link
      to={`/events/${encodeURIComponent(event.event_id)}`}
      className={`event-card${event.status === 'closed' ? ' event-past' : ''}`}
    >
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
        <StatusBadge status={event.status} />
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
      events: list.filter((e) => !['done', 'closed', 'cancelled'].includes(e.status)),
    },
    {
      value: 'followup',
      label: 'Needs after-event form',
      events: list.filter((e) => e.status === 'done'),
    },
    {
      value: 'past',
      label: 'Past',
      events: list.filter((e) => ['closed', 'cancelled'].includes(e.status)),
    },
  ];
  return (
    <>
      <PageHeading
        title="Events"
        action={
          canEdit && (
            <Link to="/events/new" className="button primary">
              <Plus size={15} /> Plan an event
            </Link>
          )
        }
      />
      <TermArrival events={events} />
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
      </div>
      <Resource loading={events.loading} error={events.error} retry={events.reload}>
        {list.length === 0 ? (
          <EmptyState
            title="No events yet."
            description="Create an event to start planning."
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
