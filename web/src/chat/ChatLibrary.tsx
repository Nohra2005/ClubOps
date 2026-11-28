import { useId, useState, type ComponentType, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { CalendarDays, ChevronDown, MessageCircle, Plus } from 'lucide-react';
import { useApp } from '../AppContext';
import { storage } from '../api';
import type { ChatMessage, EventSummary } from '../api/types';
import { PageHeading, Resource } from '../components/ui';
import { useResource } from '../hooks';
import type { ChatPanelProps } from '../pages/Chat';
import { answerFromEvent, type Conversation } from './conversations';

function isMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<ChatMessage>;
  return (
    typeof item.id === 'string' &&
    typeof item.text === 'string' &&
    (item.role === 'user' || item.role === 'assistant')
  );
}

function readHistory(key: string, legacyKey: string): Conversation[] {
  try {
    const current = storage.getItem(key);
    if (current) {
      const threads: unknown = JSON.parse(current);
      return Array.isArray(threads)
        ? threads.filter(
            (thread) =>
              thread &&
              typeof thread.id === 'string' &&
              (thread.eventId === null || typeof thread.eventId === 'string') &&
              Array.isArray(thread.messages) &&
              thread.messages.length > 0 &&
              thread.messages.every(isMessage),
          )
        : [];
    }
    const previous: unknown = JSON.parse(storage.getItem(legacyKey) ?? '[]');
    const messages = Array.isArray(previous) ? previous.filter(isMessage) : [];
    return messages.length > 0 ? [{ id: 'previous-chat', eventId: null, messages }] : [];
  } catch {
    return [];
  }
}

export function ChatLibrary({ panel: Panel }: { panel: ComponentType<ChatPanelProps> }) {
  const { api, me } = useApp();
  const [search] = useSearchParams();
  const eventId = search.get('event');
  const events = useResource(() => api.events(), [api], true);
  const identity = JSON.stringify([me.club.id, me.user.member_id]);
  const historyKey = `clubops.chat.demo.threads.${identity}`;
  const legacyKey = `clubops.chat.demo.${me.club.id}.${me.user.member_id}`;
  const [threads, setThreads] = useState(() => readHistory(historyKey, legacyKey));
  const event = events.value?.find((item) => item.event_id === eventId);

  function save(id: string, messages: ChatMessage[]) {
    const current = readHistory(historyKey, legacyKey);
    const previous = current.find((thread) => thread.id === id && thread.eventId === eventId);
    const known = new Set(previous?.messages.map((message) => message.id));
    const transcript = [
      ...(previous?.messages ?? []),
      ...messages.filter((message) => !known.has(message.id)),
    ];
    const next = [
      { id, eventId, messages: transcript },
      ...current.filter((thread) => thread.id !== id || thread.eventId !== eventId),
    ];
    storage.setItem(historyKey, JSON.stringify(next));
    setThreads(next);
  }

  const spaces = (
    <nav aria-label="Chat spaces">
      <Link className="chat-scope" to="/chat" aria-current={!eventId ? 'page' : undefined}>
        <MessageCircle size={16} /> General
      </Link>
      <h2>Events</h2>
      <Resource
        loading={events.loading && !events.value}
        error={events.error}
        retry={events.reload}
      >
        {events.value?.length === 0 && <p>No events yet</p>}
        {events.value?.map((item) => (
          <Link
            className="chat-scope"
            key={item.event_id}
            to={`/chat?event=${encodeURIComponent(item.event_id)}`}
            aria-current={eventId === item.event_id ? 'page' : undefined}
          >
            <CalendarDays size={16} /> <span>{item.title}</span>
          </Link>
        ))}
      </Resource>
      <Link className="text-button chat-event-link" to="/events">
        Manage events
      </Link>
    </nav>
  );

  return (
    <>
      <PageHeading title="Chat" />
      {eventId && !event ? (
        <div className="chat-library">
          <aside className="chat-library-nav">{spaces}</aside>
          <Resource loading={events.loading} error={events.error} retry={events.reload}>
            <p>
              This event is unavailable. <Link to="/chat">Go to General</Link>
            </p>
          </Resource>
        </div>
      ) : (
        <ChatScope
          key={JSON.stringify([
            eventId,
            search.get('prepare'),
            search.get('role'),
            search.get('new'),
          ])}
          event={event}
          threads={threads.filter((thread) => thread.eventId === eventId)}
          save={save}
          panel={Panel}
          spaces={spaces}
        />
      )}
    </>
  );
}

function ChatScope({
  event,
  threads,
  save,
  panel: Panel,
  spaces,
}: {
  event?: EventSummary;
  threads: Conversation[];
  save: (id: string, messages: ChatMessage[]) => void;
  spaces: ReactNode;
  panel: ComponentType<ChatPanelProps>;
}) {
  const { api, canEdit } = useApp();
  const [search] = useSearchParams();
  const [selected, setSelected] = useState(
    () =>
      (search.get('prepare') !== '1' && !search.has('role') && !search.has('new')
        ? threads[0]?.id
        : undefined) ?? crypto.randomUUID(),
  );
  const [pending, setPending] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const historyId = useId();
  const active = threads.find((thread) => thread.id === selected);

  return (
    <div className="chat-library">
      <aside className="chat-library-nav" data-expanded={expanded}>
        <button
          type="button"
          className="chat-library-toggle"
          aria-expanded={expanded}
          aria-controls={historyId}
          onClick={() => setExpanded(!expanded)}
        >
          <MessageCircle size={16} /> Chat history <ChevronDown size={16} />
        </button>
        <div id={historyId} className="chat-library-nav-content">
          {spaces}
          <nav className="chat-threads" aria-label="Conversations">
            <h2>Conversations</h2>
            {threads.length === 0 && <p>No conversations yet</p>}
            {threads.map((thread) => (
              <button
                key={thread.id}
                className="chat-scope"
                aria-current={selected === thread.id ? 'true' : undefined}
                disabled={pending}
                onClick={() => setSelected(thread.id)}
              >
                <MessageCircle size={14} />
                <span>{thread.messages[0].text}</span>
              </button>
            ))}
          </nav>
        </div>
      </aside>
      <div className="chat-library-main">
        <header className="chat-scope-heading">
          <div>
            <h2>{event?.title ?? 'General'}</h2>
            {event && <Link to={`/events/${encodeURIComponent(event.event_id)}`}>View event</Link>}
          </div>
          {canEdit && (
            <button
              className="button primary"
              disabled={pending}
              onClick={() => setSelected(crypto.randomUUID())}
            >
              <Plus size={15} /> New chat
            </button>
          )}
        </header>
        <Panel
          key={selected}
          initialMessages={active?.messages}
          eventTitle={event?.title}
          onTurn={(messages) => save(selected, messages)}
          onActivity={setPending}
          suggestions={
            event ? ['When is this event?', 'Where is it?', 'What tasks are open?'] : undefined
          }
          previewAsk={async (text, messages) => {
            if (event) {
              const answer = answerFromEvent(await api.event(event.event_id), text, messages);
              if (answer) return answer;
            }
            const previous = messages.at(-1)?.reply;
            if (/^can you repeat that\??$/i.test(text.trim()) && previous?.kind === 'answer') {
              if (!previous.event_source) return previous;
            }
            return api.ask(text);
          }}
        />
      </div>
    </div>
  );
}
