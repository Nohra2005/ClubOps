import { roleLabels, type Role } from '../api/types';

export const steps = [
  {
    path: '/events',
    title: 'Start with the work ahead',
    target: 'Events',
    text: 'Open a current event to see its plan and unresolved work. Starting a new plan is a separate action you choose.',
  },
  {
    path: '/calendar',
    title: 'Check the next commitments',
    target: 'Calendar',
    text: 'Look at upcoming tasks and who owns them. Check the connection status before expecting Google reminders.',
  },
  {
    path: '/knowledge',
    title: 'Learn how this club worked',
    target: 'Knowledge',
    text: 'Open a fact and check its source and date. Previous practice can be useful without being a current requirement.',
  },
  {
    path: '/chat',
    title: 'Ask for help in your role',
    target: 'Chat',
    text: 'Turn on role-learning help, then ask a question. Sending a question can use AI; opening this tour never does.',
  },
] as const;

export interface Progress {
  version: 1;
  status: 'new' | 'active' | 'paused' | 'complete' | 'dismissed';
  step: number;
  learning: boolean;
}
export const initialProgress = (): Progress => ({
  version: 1,
  status: 'new',
  step: 0,
  learning: false,
});
export function progressKey(mode: string, club: string, member: string, role: Role) {
  return `clubops.role-start.${JSON.stringify([1, mode, club, member, role])}`;
}
export function readProgress(value: string | null): Progress {
  try {
    const p: unknown = JSON.parse(value ?? 'null');
    if (typeof p !== 'object' || p === null) return initialProgress();
    const item = p as Record<string, unknown>;
    if (
      item.version !== 1 ||
      !['new', 'active', 'paused', 'complete', 'dismissed'].includes(String(item.status)) ||
      !Number.isInteger(item.step) ||
      Number(item.step) < 0 ||
      Number(item.step) >= steps.length ||
      typeof item.learning !== 'boolean'
    )
      return initialProgress();
    return {
      version: 1,
      status: item.status as Progress['status'],
      step: Number(item.step),
      learning: item.learning,
    };
  } catch {
    return initialProgress();
  }
}
// The role comes from /me, never a role query string or stored metadata.
export function learningQuestion(role: Role, step: number, question: string) {
  return `I am learning my ${roleLabels[role]} role. I have reached the introduction step "${steps[step]?.title ?? steps[0].title}". Please explain this step by step using approved club knowledge with sources. Distinguish previous practice from current rules and say when information is missing. My question: ${question}`;
}
