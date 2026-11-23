/** C-35 UI fixtures only. These are not API contracts or server authorization. */
export const PREVIEW_TODAY = '2026-11-12';
export const PREVIEW_CODE = 'DEMO-4821';
export type ConnectionState = 'disconnected' | 'pending' | 'connected' | 'expired' | 'failed';
export type SkipReason = 'unverified_sender' | 'not_osa' | 'already_read' | 'missing_headers';
export const skipReasons: Record<SkipReason, string> = {
  unverified_sender: 'The forwarding address has not been verified.',
  not_osa: 'ClubOps only reads e-mails forwarded from OSA staff.',
  already_read: 'This original e-mail has already been read. No second paid read is needed.',
  missing_headers: 'The original sender could not be checked. Keep the Outlook forwarding headers.',
};
export interface PreviewMessage {
  id: string;
  subject: string;
  received: string;
  status: 'waiting' | 'skipped' | 'read' | 'failed';
  reason?: SkipReason;
}
export interface PreviewCard {
  id: string;
  statement: string;
  quote: string;
  expires: string;
  archived: boolean;
  approved: boolean;
  shared: boolean;
  addToCalendar: boolean;
  audience: 'cabinet' | 'events';
}
export interface PreviewState {
  connection: ConnectionState;
  reader: 'pending' | 'granted' | 'failed';
  address: string;
  verification: 'none' | 'pending' | 'verified' | 'expired';
  forwardingTest: 'not_tested' | 'waiting' | 'passed' | 'failed';
  outcome: 'success' | 'partial' | 'failed';
  messages: PreviewMessage[];
  cards: PreviewCard[];
  attempts: number;
  proposed: number;
  error: string;
}
export type PreviewAction =
  | { type: 'connection'; value: ConnectionState }
  | { type: 'reader'; value: PreviewState['reader'] }
  | { type: 'address'; value: string }
  | { type: 'verify'; code: string }
  | { type: 'expire_verification' }
  | { type: 'test_forwarding' }
  | { type: 'test_result'; value: 'passed' | 'failed' }
  | { type: 'outcome'; value: PreviewState['outcome'] }
  | { type: 'read'; ids: string[] }
  | {
      type: 'approve_card';
      id: string;
      expires: string;
      shared: boolean;
      addToCalendar: boolean;
      audience: PreviewCard['audience'];
    }
  | { type: 'restore'; id: string; expires: string };

export function initialPreview(): PreviewState {
  return {
    connection: 'disconnected',
    reader: 'pending',
    address: '',
    verification: 'none',
    forwardingTest: 'not_tested',
    outcome: 'success',
    attempts: 0,
    proposed: 0,
    error: '',
    messages: [
      {
        id: 'sample-1',
        subject: 'Synthetic OSA note: room booking deadline',
        received: '12 Nov, 09:00',
        status: 'waiting',
      },
      {
        id: 'sample-2',
        subject: 'Synthetic OSA note: proposal attachment',
        received: '12 Nov, 09:10',
        status: 'waiting',
      },
      {
        id: 'sample-3',
        subject: 'Synthetic non-OSA forward',
        received: '12 Nov, 09:15',
        status: 'skipped',
        reason: 'not_osa',
      },
    ],
    cards: [
      {
        id: 'deadline-preview',
        statement: 'Synthetic example: send the room request by 30 November.',
        quote:
          'Example office note: please send the room request by 30 November. This is not an AUB rule.',
        expires: '2026-11-30',
        archived: false,
        approved: false,
        shared: false,
        addToCalendar: true,
        audience: 'cabinet',
      },
      {
        id: 'archive-preview',
        statement: 'Synthetic example: last term’s room-request date.',
        quote: 'Example from a previous term; not a current AUB rule.',
        expires: '2026-11-01',
        archived: true,
        approved: true,
        shared: false,
        addToCalendar: false,
        audience: 'cabinet',
      },
    ],
  };
}

function validDate(value: string) {
  return (
    /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    !Number.isNaN(Date.parse(value)) &&
    new Date(value).toISOString().slice(0, 10) === value
  );
}
const sampleAddress = /^[^\s@]+@(?:example\.(?:com|org|net)|[a-z0-9.-]+\.example)$/i;

/** Synchronous transitions also prevent repeated clicks from re-reading a completed sample. */
export function reducePreview(
  state: PreviewState,
  action: PreviewAction,
  access: { canEdit: boolean; isPresident: boolean },
): PreviewState {
  const fail = (error: string) => ({ ...state, error });
  if (!access.canEdit) return fail('This preview is read only for your role.');
  if (
    ['connection', 'reader', 'approve_card', 'restore'].includes(action.type) &&
    !access.isPresident
  )
    return fail('Ask the president to change this setting.');
  const next = { ...state, error: '' };
  switch (action.type) {
    case 'connection':
      return { ...next, connection: action.value, reader: 'pending', forwardingTest: 'not_tested' };
    case 'reader':
      return { ...next, reader: action.value };
    case 'address':
      if (!sampleAddress.test(action.value.trim()))
        return fail('Use a sample address such as member@example.com in this preview.');
      return {
        ...next,
        address: action.value.trim(),
        verification: 'pending',
        forwardingTest: 'not_tested',
      };
    case 'verify':
      if (state.verification !== 'pending')
        return fail('Start a new verification before checking a code.');
      if (action.code !== PREVIEW_CODE)
        return fail('That sample code does not match. Your address is still unverified.');
      return { ...next, verification: 'verified' };
    case 'expire_verification':
      return { ...next, verification: 'expired', forwardingTest: 'not_tested' };
    case 'test_forwarding':
      if (state.verification !== 'verified')
        return fail('Verify the sample sending address first.');
      if (state.connection !== 'connected')
        return fail('The inbox connection needs attention before testing forwarding.');
      return { ...next, forwardingTest: 'waiting' };
    case 'test_result':
      return state.forwardingTest === 'waiting'
        ? { ...next, forwardingTest: action.value }
        : fail('Start the forwarding test first.');
    case 'outcome':
      return { ...next, outcome: action.value };
    case 'read': {
      if (state.connection !== 'connected')
        return fail('Reconnect the inbox before reading. Nothing was read.');
      const ids = new Set(action.ids);
      let attempted = 0;
      let proposed = 0;
      const messages = state.messages.map((message): PreviewMessage => {
        if (!ids.has(message.id) || !['waiting', 'failed'].includes(message.status)) return message;
        attempted++;
        if (
          state.outcome === 'failed' ||
          (state.outcome === 'partial' && message.id === 'sample-2')
        )
          return { ...message, status: 'failed' };
        proposed++;
        return { ...message, status: 'read' };
      });
      return {
        ...next,
        messages,
        attempts: state.attempts + attempted,
        proposed: state.proposed + proposed,
      };
    }
    case 'approve_card':
    case 'restore': {
      if (action.expires && !validDate(action.expires)) return fail('Choose a valid expiry date.');
      if (action.type === 'restore' && (!action.expires || action.expires <= PREVIEW_TODAY))
        return fail('Choose a future expiry before restoring this sample.');
      if (action.type === 'approve_card' && action.shared)
        return fail(
          'AUB-wide publication needs the operator workflow. This preview cannot publish shared rules.',
        );
      return {
        ...next,
        cards: state.cards.map((card) => {
          if (
            card.id !== action.id ||
            (action.type === 'restore' && !card.archived) ||
            (action.type === 'approve_card' && (card.archived || card.approved))
          )
            return card;
          if (action.type === 'restore')
            return { ...card, expires: action.expires, archived: false };
          return {
            ...card,
            expires: action.expires,
            approved: true,
            archived: Boolean(action.expires && action.expires <= PREVIEW_TODAY),
            shared: action.shared,
            addToCalendar: action.addToCalendar,
            audience: action.audience,
          };
        }),
      };
    }
  }
}
