import type { ChatMessage, ChatReply, EventDetail } from '../api/types';
import { formatDate, formatTime } from '../lib';

export interface Conversation {
  id: string;
  eventId: string | null;
  messages: ChatMessage[];
}

type Topic = 'schedule' | 'venue' | 'tasks';

function topicFor(text: string): Topic | undefined {
  if (/\b(venue|where|location)\b/i.test(text)) return 'venue';
  if (/\b(when|date|time|schedule)\b/i.test(text)) return 'schedule';
  if (/\b(tasks?|outstanding|unfinished)\b/i.test(text)) return 'tasks';
}

export function answerFromEvent(
  event: EventDetail,
  question: string,
  messages: ChatMessage[],
): ChatReply | undefined {
  const direct =
    /^(when|where|what(?: tasks?| time| date| venue)|which tasks?|are .*tasks?)\b/i.test(
      question.trim(),
    )
      ? topicFor(question)
      : undefined;
  const lastAnswer = messages.at(-1)?.reply;
  const topic =
    direct ??
    (/^can you repeat that\??$/i.test(question.trim()) &&
    lastAnswer?.kind === 'answer' &&
    lastAnswer.event_source === event.event_id
      ? topicFor(messages.at(-2)?.text ?? '')
      : undefined);
  if (!topic) return;
  const outstanding = event.tasks.filter((task) => task.state !== 'done');
  const text =
    topic === 'schedule'
      ? `${event.title} starts on ${formatDate(event.start, true)} at ${formatTime(event.start)}.`
      : topic === 'venue'
        ? `${event.title} is scheduled at ${event.venue || 'a venue that has not been set'}.`
        : outstanding.length
          ? `Open tasks for ${event.title}: ${outstanding.map((task) => task.title).join('; ')}.`
          : `There are no open tasks listed for ${event.title}.`;
  return {
    kind: 'answer',
    known: true,
    text,
    citations: [],
    basis: 'single_source',
    event_source: event.event_id,
  };
}
