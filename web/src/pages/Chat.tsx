import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { ArrowUp, CheckCheck, FileText, MessageCircle, Plus } from 'lucide-react';
import { useApp } from '../AppContext';
import { ChatLibrary } from '../chat/ChatLibrary';
import { type ChatMessage, type ChatReply } from '../api/types';
import { Feedback } from '../components/Feedback';
import {
  PageHeading,
  ErrorNotice,
  FallbackNotice,
  Modal,
  NotSure,
  SourceChip,
} from '../components/ui';
import { useAction } from '../hooks';

function Reply({ reply, id }: { reply: ChatReply; id: string }) {
  return (
    <div className="reply-content">
      {reply.kind === 'unknown' ? (
        <NotSure ask={reply.ask} lookIn={reply.look_in} explanation={reply.text} />
      ) : reply.kind === 'learned' ? (
        <div className="learned-card">
          <CheckCheck size={18} />
          <div>
            <strong>{reply.review_id ? 'New fact sent for review' : 'No new fact proposed'}</strong>
            <p>{reply.text}</p>
            {reply.review_id && (
              <Link to={`/review?item=${encodeURIComponent(reply.review_id)}`}>
                Review it before the club relies on it →
              </Link>
            )}
          </div>
        </div>
      ) : (
        <>
          <p>{reply.text}</p>
          {reply.basis === 'disputed' && (
            <div className="notice warning">
              <span>
                These sources disagree.{' '}
                <Link
                  to={
                    reply.review_id
                      ? `/review?item=${encodeURIComponent(reply.review_id)}`
                      : '/review'
                  }
                >
                  Review the disagreement
                </Link>{' '}
                before relying on this answer.
              </span>
            </div>
          )}
          <div className="source-list">
            {reply.event_source && (
              <Link
                className="source-chip"
                to={`/events/${encodeURIComponent(reply.event_source)}`}
              >
                <FileText size={11} /> Event details
              </Link>
            )}
            {reply.citations.map((source) => (
              <SourceChip key={source.item_id} source={source} />
            ))}
          </div>
        </>
      )}
      {'fallback' in reply && reply.fallback && <FallbackNotice />}
      <Feedback id={id} />
    </div>
  );
}

export default function Chat() {
  const { api, me } = useApp();
  return api.mode === 'demo' ? (
    <ChatLibrary key={JSON.stringify([me.club.id, me.user.member_id])} panel={ChatPanel} />
  ) : (
    <ChatPanel />
  );
}

export interface ChatPanelProps {
  initialMessages?: ChatMessage[];
  onTurn?: (messages: ChatMessage[]) => void;
  onActivity?: (pending: boolean) => void;
  eventTitle?: string;
  previewAsk?: (text: string, messages: ChatMessage[]) => Promise<ChatReply>;
  suggestions?: string[];
}

function ChatPanel({
  initialMessages = [],
  onTurn,
  onActivity,
  eventTitle,
  previewAsk,
  suggestions = [
    'What do I need for an event with outside guests?',
    'Who do we contact about the venue?',
    'What did we learn from the last run?',
  ],
}: ChatPanelProps) {
  const { api, me, canEdit, refresh } = useApp();
  const [search] = useSearchParams();
  const [messages, setMessages] = useState(initialMessages);
  const [text, setText] = useState(
    search.get('prepare') === '1'
      ? 'For the next cabinet: what happened, what worked, and what still needs checking: '
      : search.get('role')
        ? `What should the ${search.get('role')?.replaceAll('_', ' ')} know?`
        : '',
  );
  const [mode, setMode] = useState<'ask' | 'teach'>(
    search.get('prepare') === '1' ? 'teach' : 'ask',
  );
  const [paste, setPaste] = useState(false);
  const [document, setDocument] = useState('');
  const action = useAction();
  const sending = useRef(false);
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'instant'
        : 'smooth',
      block: 'end',
    });
  }, [messages]);
  async function send(content = text, inputMode = mode) {
    if (!content.trim() || sending.current || !canEdit) return;
    sending.current = true;
    onActivity?.(true);
    const submitted = content;
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', text: submitted };
    setMessages([...messages, userMessage]);
    setText('');
    const result = await action.run(() => {
      if (inputMode === 'teach') return api.teach(content);
      return previewAsk ? previewAsk(submitted, messages) : api.ask(submitted);
    });
    if (result.ok) {
      const completed: ChatMessage[] = [
        ...messages,
        userMessage,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: result.value.text,
          reply: result.value,
        },
      ];
      setMessages(completed);
      onTurn?.(completed);
      setPaste(false);
      setDocument('');
      refresh();
    } else {
      setMessages(messages);
      if (inputMode === 'ask' || !paste) setText(content);
    }
    sending.current = false;
    onActivity?.(false);
  }
  return (
    <>
      {!onTurn && (
        <PageHeading
          title="Chat"
          action={
            canEdit && (
              <button
                className="button"
                onClick={() => {
                  setMessages([]);
                  action.clearError();
                }}
                disabled={action.pending}
              >
                <Plus size={14} /> New chat
              </button>
            )
          }
        />
      )}
      <section
        className="chat-workspace"
        aria-label={eventTitle ? `Chat about ${eventTitle}` : 'Chat'}
      >
        <div className="chat-messages" aria-live="polite" aria-relevant="additions">
          {messages.length === 0 ? (
            <div className="chat-welcome">
              <h2>{eventTitle ? `Ask about ${eventTitle}` : 'Ask a question'}</h2>
              {canEdit && (
                <div className="suggestions">
                  {suggestions.map((question) => (
                    <button key={question} onClick={() => setText(question)}>
                      {question}
                      <ArrowUp size={13} />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            messages.map((message) => (
              <article className={`chat-message message-${message.role}`} key={message.id}>
                <span className={message.role === 'assistant' ? 'assistant-avatar' : 'avatar'}>
                  {message.role === 'assistant'
                    ? 'c.'
                    : me.user.name
                        .split(' ')
                        .map((n) => n[0])
                        .slice(0, 2)
                        .join('')}
                </span>
                <div>
                  <div className="message-author">
                    {message.role === 'assistant' ? 'ClubOps' : me.user.name}
                  </div>
                  {message.reply ? (
                    <Reply reply={message.reply} id={message.id} />
                  ) : (
                    <p>{message.text}</p>
                  )}
                </div>
              </article>
            ))
          )}
          {action.pending && (
            <div className="thinking" role="status">
              <span className="assistant-avatar">c.</span>
              <span>
                Thinking<span className="thinking-dots">…</span>
              </span>
            </div>
          )}
          <div ref={bottom} />
        </div>
        <div className="chat-compose">
          {canEdit ? (
            <>
              <div className="compose-toolbar">
                <div className="segmented">
                  <button aria-pressed={mode === 'ask'} onClick={() => setMode('ask')}>
                    <MessageCircle size={12} /> Ask
                  </button>
                  <button aria-pressed={mode === 'teach'} onClick={() => setMode('teach')}>
                    <FileText size={12} /> Teach the club
                  </button>
                </div>
                <button className="text-button" onClick={() => setPaste(true)}>
                  <FileText size={12} /> Paste a document
                </button>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  send();
                }}
              >
                <label className="sr-only" htmlFor="chat-input">
                  {mode === 'ask' ? 'Ask your club' : 'Teach your club'}
                </label>
                <textarea
                  id="chat-input"
                  rows={2}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  maxLength={2000}
                  placeholder={
                    mode === 'ask'
                      ? 'Ask about an event, a contact, or a lesson…'
                      : 'What should the club remember? This goes to Review first.'
                  }
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                      e.preventDefault();
                      e.currentTarget.form?.requestSubmit();
                    }
                  }}
                />
                <button
                  className="send-button"
                  aria-label={mode === 'ask' ? 'Ask ClubOps' : 'Send fact for review'}
                  disabled={action.pending || !text.trim()}
                >
                  <ArrowUp size={20} />
                </button>
              </form>
              <div className="compose-note">
                <span>
                  {mode === 'teach' ? 'Nothing is learned until a cabinet member approves it.' : ''}
                </span>
                <span>
                  Enter to {mode === 'teach' ? 'teach' : 'ask'} · Shift + Enter for a new line
                </span>
              </div>
              <ErrorNotice message={action.error} retry={() => send()} />
            </>
          ) : (
            <p className="inline-note">
              Adviser view is read only. Browse Knowledge for your club's approved facts.
            </p>
          )}
        </div>
      </section>
      <Modal open={paste} title="Paste a document" onClose={() => setPaste(false)}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(document, 'teach');
          }}
        >
          <p>
            Paste an authorized email, message or document. Proposed lessons go to Review first.
          </p>
          <label className="field">
            <span>Document text</span>
            <textarea
              rows={10}
              maxLength={20000}
              required
              value={document}
              onChange={(e) => setDocument(e.target.value)}
              placeholder="Paste the text here…"
            />
          </label>
          <div className="form-actions">
            <button className="button primary" disabled={action.pending || !document.trim()}>
              {action.pending ? 'Preparing proposals…' : 'Send for review'}
            </button>
            <button type="button" className="button" onClick={() => setPaste(false)}>
              Cancel
            </button>
          </div>
          <ErrorNotice message={action.error} />
        </form>
      </Modal>
    </>
  );
}
