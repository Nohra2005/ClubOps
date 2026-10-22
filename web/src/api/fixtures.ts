import type { Club, EventDetail, EventFields, KnowledgeItem, Member, ProposalAnswer, Source, Workspace } from './types';

/** Entirely synthetic examples. No fixture is an authoritative AUB rule or real club record. */
export const DEMO_TODAY = '2026-10-22';
export const clubs: Club[] = [
  { id: 'running-club', name: 'Running Club', initials: 'RC', setup_complete: true },
  { id: 'asme', name: 'ASME', initials: 'AS', setup_complete: false },
];
export const venueSource: Source = { item_id: 'kh-demo-venue', label: 'Demo venue guide', kind: 'document', authority: 'official_document', quote: 'Synthetic example for this demo: request the venue two weeks before the event. This is not an AUB policy.' };
export const coffeeSource: Source = { item_id: 'kh-demo-coffee', label: 'Cabinet note · example', kind: 'note', authority: 'stated_by_president', quote: 'Synthetic example: Cedar Coffee asked for ten days of notice and an estimated head count.' };
export const debriefSource: Source = { item_id: 'kh-demo-welcome', label: 'Welcome run debrief · example', kind: 'debrief', quote: 'Synthetic example: marking pace groups clearly helped new members feel welcome.' };

export const proposalLabels = [
  'Club / society name', 'Club name if not listed', "Requester's first name", "Requester's last name", "Requester's AUB ID", "Requester's position", "Requester's AUB email", "Requester's phone",
  'Event title', 'Event type', 'Other event type', 'Sustainable development goals', 'Starting date', 'Starting time (24-hour)', 'Ending date', 'Ending time (24-hour)', 'Location', 'Event description', 'Materials needed', 'Catering', 'Speaker details and CVs', 'Audience', 'Expected attendance', 'Non-AUB guest list', 'Admission', 'Ticket price', 'Funding source', 'Food and beverage suppliers', 'Promotional material', 'Expense form', 'Funding confirmation', "Adviser's name", "Adviser's email",
];

export function proposalFor(fields: EventFields, clubName: string): ProposalAnswer[] {
  const answers: Record<number, string> = { 1: clubName, 3: 'Alex', 4: 'Morgan', 6: 'President', 9: fields.title, 10: 'Sport', 13: fields.date, 14: fields.time, 15: fields.date, 16: fields.end_time, 17: fields.venue, 18: fields.description, 19: 'To confirm', 20: fields.catering, 22: fields.audience, 23: fields.expected_attendance, 25: 'Free entry', 27: fields.budget === '0' ? 'No expenses' : 'To confirm', 28: fields.catering === 'No' ? 'Not applicable' : fields.sponsors, 32: 'Robin Taylor' };
  return proposalLabels.map((label, i) => ({ field_id: `q${String(i + 1).padStart(2, '0')}`, label, value: answers[i + 1] ?? '', origin: answers[i + 1] ? ([1, 3, 4, 6, 32].includes(i + 1) ? 'retrieved' : 'stated') : 'missing', ...([1, 3, 4, 6, 32].includes(i + 1) ? { source: { item_id: 'kh-demo-profile', label: 'Demo club profile', kind: 'note' as const, quote: 'Synthetic cabinet profile used only for the frontend demo.' } } : {}) }));
}

export function eventFor(id: string, title: string, date: string, status: EventDetail['status'], clubName = 'Running Club'): EventDetail {
  const fields: EventFields = { title, date, time: '17:00', end_time: '18:30', venue: 'Campus meeting point', audience: 'Club members', expected_attendance: '30–40', budget: '0', sponsors: 'Cedar Coffee (not confirmed)', has_prizes: 'No', catering: 'No', partner_clubs: '', description: 'An easy-paced, welcoming run around campus. Meet the cabinet, find your pace group, and stay for a chat afterward.' };
  const taskDefs = [
    ['venue', 'Confirm the meeting point', '2026-10-21', 'events', 'overdue'],
    ['coffee', 'Confirm coffee with the sponsor', '2026-10-25', 'sponsorship', 'todo'],
    ['announcement', 'Share the announcement', '2026-10-27', 'communications', 'todo'],
    ['leaders', 'Assign the pace group leaders', '2026-10-28', 'events', 'done'],
  ] as const;
  return {
    event_id: id, title, start: `${date}T17:00:00+03:00`, end: `${date}T18:30:00+03:00`, venue: fields.venue, status, task_count: 4, tasks_done: status === 'closed' || status === 'done' ? 4 : 1, overdue_tasks: status === 'planned' ? 1 : 0, event_type: 'weekly_run', plan_outdated: false,
    revision: 1, fields, origins: Object.fromEntries(Object.keys(fields).map(key => [key, { origin: key === 'venue' ? 'retrieved' : 'stated', ...(key === 'venue' ? { source: venueSource } : {}) }])),
    approvals: [
      { approval_id: `${id}/venue`, name: 'Venue confirmation', why: 'Confirm the meeting point with the responsible office.', deadline: '2026-10-21', status: 'needed', uncertain: false, source: venueSource },
      { approval_id: `${id}/proposal`, name: 'OSA event proposal', why: 'Prepare the event paperwork for a cabinet member to submit.', deadline: '2026-10-25', status: 'requested', uncertain: false, source: { item_id: 'kh-demo-form', label: 'Demo proposal checklist', kind: 'document', quote: 'This is a synthetic checklist for demonstrating the interface.' } },
      { approval_id: `${id}/guests`, name: 'Guest access · check this', why: 'The audience is not yet confirmed. Check before inviting guests.', deadline: '2026-10-25', status: 'needed', uncertain: true, source: venueSource },
    ],
    tasks: taskDefs.map(([key, text, due, role, state]) => ({ task_id: `${id}/${key}`, event_id: id, title: text, due, owner_role: role, state: status === 'closed' || status === 'done' ? 'done' : state, source: key === 'coffee' ? coffeeSource : venueSource })),
    proposal: proposalFor(fields, clubName), drafts: {}, tips: [{ item_id: coffeeSource.item_id, title: 'Give your sponsor time', statement: 'For this demo, Cedar Coffee needs ten days of notice.', source: coffeeSource }, { item_id: debriefSource.item_id, title: 'Make the pace groups clear', statement: 'Label each group so new members know where to start.', source: debriefSource }],
    route: 'Campus loop · 5 km · meet at the main entrance', leaders: [{ id: 'lead-1', name: 'Sam Lee', pace: 'Easy · 7:00/km' }, { id: 'lead-2', name: 'Jamie Reed', pace: 'Steady · 6:00/km' }],
    agent_run: { run_id: `run-${id}`, status: 'done', steps_used: 4, step_limit: 8, cost_usd: 0.018, event_id: id, steps: [{ n: 1, text: 'Read the event details', state: 'done' }, { n: 2, text: 'Found two relevant cabinet notes', state: 'done' }, { n: 3, text: 'Checked the demo venue requirements', state: 'done' }, { n: 4, text: 'Prepared tasks and the proposal draft', state: 'done' }] },
  };
}

export function createWorkspace(clubId: string): Workspace {
  const shared: KnowledgeItem[] = [
    { item_id: venueSource.item_id, title: 'Venue booking notice', statement: 'Synthetic demo policy: allow two weeks to confirm the venue. Verify real requirements with the responsible AUB office.', tab: 'rules', kind: 'rule', scope: 'aub', sources: [venueSource], last_checked: DEMO_TODAY, status: 'current', triggers: 'Use of a booked venue', requirements: 'Written venue confirmation', lead_time_days: 14, history: [{ date: DEMO_TODAY, description: 'Synthetic example added to the demo', actor: 'Demo cabinet' }], used_in: [] },
    { item_id: 'kh-demo-form', title: 'Proposal checklist', statement: 'Use the published OSA form and confirm all missing information with the cabinet. This demo checklist does not establish policy.', tab: 'rules', kind: 'rule', scope: 'aub', sources: [{ item_id: 'kh-demo-form', label: 'Demo proposal checklist', kind: 'document' }], last_checked: DEMO_TODAY, status: 'current', history: [], used_in: [] },
  ];
  const members: Member[] = [
    { member_id: 'm-alex-demo', name: 'Alex Morgan', email: 'alex@example.com', role: 'president' },
    { member_id: 'm-sam-demo', name: 'Sam Lee', email: 'sam@example.com', role: 'events' },
    { member_id: 'm-jamie-demo', name: 'Jamie Reed', email: 'jamie@example.com', role: 'sponsorship' },
    { member_id: 'm-robin-demo', name: 'Robin Taylor', email: 'robin@example.com', role: 'adviser' },
  ];
  const running = clubId === 'running-club';
  const knowledge: KnowledgeItem[] = running ? [...shared,
    { item_id: coffeeSource.item_id, title: 'Give Cedar Coffee ten days', statement: 'Synthetic example: Cedar Coffee asks for ten days of notice and an estimated head count.', tab: 'tips', kind: 'procedure', scope: 'club', sources: [coffeeSource], last_checked: '2026-10-12', last_used: DEMO_TODAY, status: 'current', history: [{ date: '2026-10-12', description: 'Cabinet approved this synthetic example', actor: 'Alex Morgan' }], used_in: [{ event_id: 'ev-sunset-run', title: 'Sunset campus run' }] },
    { item_id: debriefSource.item_id, title: 'Make new runners feel welcome', statement: 'Clearly mark pace groups and introduce each leader before the run.', tab: 'tips', kind: 'lesson', scope: 'club', sources: [debriefSource], last_checked: '2026-10-16', last_used: '2026-10-16', status: 'current', history: [{ date: '2026-10-16', description: 'Lesson approved from a synthetic debrief', actor: 'Sam Lee' }], used_in: [{ event_id: 'ev-welcome-run', title: 'Welcome run' }] },
    { item_id: 'kh-demo-document', title: 'Demo club handbook', statement: 'Synthetic placeholder document for testing version review. Upload an authorized source to use real policy.', tab: 'documents', kind: 'document', scope: 'club', sources: [venueSource], last_checked: '2025-10-12', status: 'may_be_outdated', year: '2025–26', history: [], used_in: [] },
    { item_id: 'kh-demo-contact', title: 'Venue desk · example', statement: 'Synthetic venue contact for the demo. Confirm the actual office before making a request.', tab: 'contacts', kind: 'contact', scope: 'club', sources: [venueSource], last_checked: DEMO_TODAY, status: 'current', contact: { name: 'Demo venue desk', role: 'Venue coordinator', office: 'Example office', email: 'venue@example.com', phone: '+000 000 0000' }, history: [], used_in: [] },
    { item_id: 'kh-demo-sponsor', title: 'Cedar Coffee · example', statement: 'Synthetic sponsor: coffee for club runs. Not a real partnership.', tab: 'sponsors', kind: 'relationship', scope: 'club', sources: [coffeeSource], last_checked: '2026-10-12', status: 'current', offers: 'Coffee and refreshments', last_event: 'Welcome run', history: [], used_in: [] },
  ] : shared;
  return {
    events: running ? [eventFor('ev-sunset-run', 'Sunset campus run', '2026-10-29', 'planned'), eventFor('ev-community-relay', 'Community relay', '2026-11-05', 'approved'), eventFor('ev-welcome-run', 'Welcome run', '2026-10-16', 'done'), eventFor('ev-clean-up', 'Coastal clean-up', '2026-10-10', 'closed')] : [],
    review: running ? [
      { id: 'review-rule', type: 'rule', title: 'Venue guide update', statement: 'Synthetic proposed rule: confirm access with the venue desk.', source: venueSource, group: 'Demo venue guide', kind: 'rule', status: 'pending' },
      { id: 'review-coffee', type: 'fact', title: 'Head count before the run', statement: 'Synthetic example: send the sponsor a head count the day before the run.', source: coffeeSource, group: 'Welcome run debrief', kind: 'tip', status: 'pending' },
      { id: 'review-merge', type: 'merge', title: 'A familiar lesson', statement: 'Make the pace group signs easy to spot.', alternative: { statement: 'Clearly mark the pace groups before the run.', source: debriefSource }, source: debriefSource, group: 'Welcome run debrief', kind: 'lesson', status: 'pending' },
      { id: 'review-conflict', type: 'disagreement', title: 'Two different meeting times', statement: 'Synthetic guide: the meeting point opens at 07:00.', alternative: { statement: 'Synthetic email: access begins at 07:30 this semester.', source: { ...venueSource, label: 'Demo office email', kind: 'email', authority: 'office_email' } }, source: venueSource, group: 'Demo office email', kind: 'procedure', status: 'pending' },
      { id: 'review-document', type: 'document', title: 'Check the handbook version', statement: 'The demo handbook is from 2025–26 and may be out of date. Ask the president for the current version.', source: venueSource, group: 'Document check', kind: 'document', status: 'pending' },
      { id: 'review-plan', type: 'plan', title: 'Sunset campus run', statement: 'The plan is ready for a cabinet member to review.', source: debriefSource, group: 'Event plans', kind: 'plan', event_id: 'ev-sunset-run', status: 'pending' },
    ] : [], knowledge, members, runs: {}, connected: false,
    usage: { month: '2026-10', cost_usd: running ? 0.084 : 0, calls: running ? 7 : 0, most_expensive_feature: running ? 'Event planning' : 'None yet', by_feature: running ? [{ name: 'Event planning', calls: 3, cost_usd: 0.054 }, { name: 'Chat', calls: 4, cost_usd: 0.03 }] : [] },
    setup_index: 0, setup_complete: running, signoffs: {},
  };
}
