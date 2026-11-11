import { ApiError, type RequestOptions, type Transport } from './client';
import { isShared } from './review-policy';
import {
  clubs,
  createWorkspace,
  DEMO_TODAY,
  eventFor,
  demoTimestamp,
  proposalFor,
} from './fixtures';
import {
  draftLabels,
  roleLabels,
  type AgentRun,
  type CalendarItem,
  type ChatReply,
  type Draft,
  type DraftType,
  type EventDetail,
  type EventFields,
  type KnowledgeItem,
  type Me,
  type ReviewCard,
  type Role,
  type Workspace,
} from './types';

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}
export const sessionKey = 'clubops.demo.session.v1';
export const workspaceKey = (club: string) => `clubops.demo.workspace.v1.${club}`;
export interface DemoSession {
  club: string;
  role: Role;
}
export function readSession(storage: StorageLike): DemoSession {
  try {
    const value = JSON.parse(storage.getItem(sessionKey) ?? '{}');
    if (clubs.some((c) => c.id === value.club) && Object.keys(roleLabels).includes(value.role))
      return value;
  } catch {
    /* A damaged preview session resets safely. */
  }
  return { club: 'running-club', role: 'president' };
}
const id = (prefix: string) => `${prefix}-${crypto.randomUUID()}`;
const now = () => new Date().toISOString();
const clone = <T>(value: T): T => structuredClone(value);
const requiredText = (value: unknown, max = 20_000): string => {
  if (typeof value !== 'string' || !value.trim() || value.length > max)
    throw new ApiError('Please enter some text before continuing.', 422);
  return value.trim();
};
const setupQuestions = [
  "What is your club or society's official name?",
  'Are you a club or a faculty society? If a society, which faculty?',
  'Which department or office advises your club? Keep personal contact details in Cabinet, not here.',
  "Which cabinet roles handle which responsibilities? Use roles, not people's names or contact details.",
  'What are your signature events and activities?',
  'Which venues do you usually use, and for what?',
  'Which organizations sponsor or partner with your club? Omit personal contact details.',
  'What recurring dates or seasonal activities should the next cabinet know about?',
  'Which communication channels do you use? Do not paste private links, credentials or contact details.',
  'What practical lesson should the next cabinet carry forward?',
];

export function createMockTransport(
  storage: StorageLike,
  session: DemoSession,
  options: { delay?: number; scenario?: string } = {},
): Transport {
  const club = clubs.find((c) => c.id === session.club) ?? clubs[0];
  const load = (): Workspace => {
    try {
      const stored = JSON.parse(storage.getItem(workspaceKey(club.id)) ?? 'null');
      if (
        stored &&
        Array.isArray(stored.events) &&
        Array.isArray(stored.review) &&
        stored.runs &&
        stored.usage
      )
        return stored;
    } catch {
      /* Only synthetic demo data is re-seeded. */
    }
    return createWorkspace(club.id);
  };
  const save = (data: Workspace) => storage.setItem(workspaceKey(club.id), JSON.stringify(data));
  const mutateAllowed = (presidentOnly = false) => {
    if (session.role === 'adviser' || (presidentOnly && session.role !== 'president'))
      throw new ApiError("You don't have permission for this action.", 403);
  };
  const charge = (data: Workspace, feature: string, amount = 0.006) => {
    data.usage.calls += 1;
    data.usage.cost_usd = Number((data.usage.cost_usd + amount).toFixed(3));
    const row = data.usage.by_feature.find((r) => r.name === feature);
    if (row) {
      row.calls++;
      row.cost_usd = Number((row.cost_usd + amount).toFixed(3));
    } else data.usage.by_feature.push({ name: feature, calls: 1, cost_usd: amount });
    data.usage.most_expensive_feature =
      [...data.usage.by_feature].sort((a, b) => b.cost_usd - a.cost_usd)[0]?.name ?? 'None yet';
  };
  const findEvent = (data: Workspace, eventId: string) => {
    const event = data.events.find((e) => e.event_id === eventId);
    if (!event) throw new ApiError('This event could not be found in your club.', 404);
    return event;
  };
  const addFact = (data: Workspace, text: string, group = 'A cabinet note'): ReviewCard => {
    const card: ReviewCard = {
      id: id('review'),
      type: 'fact',
      title: text.slice(0, 70),
      statement: text,
      source: { item_id: id('kh-note'), label: group, quote: text, kind: 'note' },
      group,
      kind: 'lesson',
      status: 'pending',
    };
    data.review.push(card);
    return card;
  };
  const newRun = (data: Workspace, event: EventDetail, phase = 'details') => {
    const run: AgentRun & { phase: string; polls: number } = {
      run_id: id('run'),
      event_id: event.event_id,
      status: phase === 'details' ? 'waiting_for_user' : 'working',
      phase,
      polls: 0,
      details: clone(event.fields),
      origins: clone(event.origins),
      steps_used: 1,
      step_limit: 8,
      cost_usd: 0.006,
      steps: [{ n: 1, text: 'Read your event description', state: 'done' }],
      ...(phase === 'details'
        ? {
            question: {
              kind: 'details' as const,
              text: 'Check the details before I build the plan.',
            },
          }
        : {}),
      fallback: options.scenario === 'fallback',
    };
    data.runs[run.run_id] = run;
    return run;
  };
  const eventFromBody = (data: Workspace, body: Record<string, unknown>) =>
    findEvent(data, String(body.event_id));

  return async (rawPath: string, request: RequestOptions = {}) => {
    const delay = options.scenario === 'loading' ? 1800 : (options.delay ?? 180);
    if (request.signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => {
        request.signal?.removeEventListener('abort', abort);
        resolve();
      }, delay);
      const abort = () => {
        clearTimeout(timer);
        reject(new DOMException('Cancelled', 'AbortError'));
      };
      request.signal?.addEventListener('abort', abort, { once: true });
    });
    const url = new URL(rawPath, 'https://demo.invalid');
    const path = decodeURIComponent(url.pathname);
    const method = request.method ?? 'GET';
    const body = (request.body ?? {}) as Record<string, unknown>;
    const data = load();
    if (options.scenario === 'offline' && path !== '/me')
      throw new ApiError("Can't reach ClubOps. Your edits are kept on this page.");
    if (method !== 'GET') mutateAllowed();
    const paid =
      method === 'POST' &&
      (/^\/events\/(plan|[^/]+\/(rebuild|drafts\/[^/]+|after-event))$/.test(path) ||
        path.startsWith('/chat/') ||
        /^\/runs\/.+\/answer$/.test(path) ||
        (path === '/setup/next' &&
          body.answer !== undefined &&
          body.answer !== '[skip]' &&
          !data.setup_complete));
    if (paid && options.scenario === 'ai-error')
      throw new ApiError("ClubOps couldn't finish this. Nothing was saved or sent.", 503);
    let result: unknown;

    if (path === '/me') {
      const user = data.members.find((m) => m.role === session.role) ?? {
        member_id: `m-demo-${session.role}`,
        name: 'Taylor Quinn',
        email: 'taylor@example.com',
        role: session.role,
      };
      result = {
        user,
        role: session.role,
        club: { ...club, setup_complete: data.setup_complete },
        counts: {
          overdue_events: data.events.filter(
            (e) => e.overdue_tasks > 0 && !['done', 'closed', 'cancelled'].includes(e.status),
          ).length,
          review: data.review.filter((r) =>
            ['pending', 'waiting_second_president'].includes(r.status),
          ).length,
          reminders: data.events
            .flatMap((e) => e.tasks)
            .filter((t) => t.state === 'overdue' || t.state === 'due_today').length,
        },
        demo: true,
      } satisfies Me;
    } else if (path === '/events' && method === 'GET') {
      result =
        options.scenario === 'empty'
          ? []
          : data.events.map(
              ({
                event_id,
                title,
                start,
                end,
                venue,
                status,
                task_count,
                tasks_done,
                overdue_tasks,
                event_type,
                plan_outdated,
              }) => ({
                event_id,
                title,
                start,
                end,
                venue,
                status,
                task_count,
                tasks_done,
                overdue_tasks,
                event_type,
                plan_outdated,
              }),
            );
    } else if (path === '/events/plan' && method === 'POST') {
      const description = requiredText(body.description);
      const event = eventFor(
        id('ev'),
        description.split(/[.!\n]/)[0].slice(0, 80),
        '2026-11-05',
        'draft',
        club.name,
      );
      event.fields = { ...event.fields, description, has_prizes: '', sponsors: '', budget: '' };
      event.origins = Object.fromEntries(
        Object.keys(event.fields).map((k) => [
          k,
          {
            origin: ['title', 'description'].includes(k)
              ? 'stated'
              : !event.fields[k as keyof EventFields]
                ? 'missing'
                : 'inferred',
          },
        ]),
      );
      event.agent_run = undefined;
      data.events.unshift(event);
      charge(data, 'Event planning');
      result = { run_id: newRun(data, event).run_id };
    } else if (/^\/runs\/[^/]+$/.test(path) && method === 'GET') {
      const run = data.runs[path.split('/')[2]];
      if (!run) throw new ApiError('This plan could not be found. Start a new plan.', 404);
      if (run.status === 'working') {
        run.polls = (run.polls ?? 0) + 1;
        const event = findEvent(data, run.event_id!);
        run.steps = [
          { n: 1, text: 'Checked the confirmed details', state: 'done' },
          { n: 2, text: 'Looked for relevant club knowledge', state: 'done' },
          { n: 3, text: 'Checking the demo requirements', state: 'running' },
        ];
        run.steps_used = 3;
        if (run.polls >= 2 && options.scenario === 'limit' && run.phase !== 'resumed') {
          run.status = 'limit_reached';
          run.steps_used = 8;
          run.cost_usd = 0.05;
          run.steps.push({
            n: 8,
            text: 'Stopped at the run limit; proposal not done',
            state: 'not_done',
          });
        } else if (run.polls >= 2 && !event.fields.has_prizes) {
          run.status = 'waiting_for_user';
          run.question = { text: 'Will there be prizes?', kind: 'text' };
          run.steps.push({ n: 4, text: 'Will there be prizes?', state: 'question' });
        } else if (run.polls >= 2) {
          run.status = 'done';
          delete run.question;
          run.steps[2].state = 'done';
          run.steps.push({ n: 4, text: 'Prepared the tasks and proposal draft', state: 'done' });
          run.steps_used = 4;
          run.cost_usd = 0.018;
          event.status = 'planned';
          event.plan_outdated = false;
          event.proposal = proposalFor(event.fields, club.name);
          event.agent_run = clone(run);
        }
      }
      result = run;
    } else if (/^\/runs\/[^/]+\/answer$/.test(path) && method === 'POST') {
      const run = data.runs[path.split('/')[2]];
      if (!run || run.status !== 'waiting_for_user')
        throw new ApiError('This run is not waiting for an answer.', 409);
      const text = requiredText(body.text);
      const event = findEvent(data, run.event_id!);
      if (run.question?.kind === 'details') {
        let fields: EventFields;
        try {
          fields = JSON.parse(text);
        } catch {
          throw new ApiError('Please check the event details and try again.', 422);
        }
        for (const key of [
          'title',
          'date',
          'time',
          'end_time',
          'venue',
          'audience',
          'expected_attendance',
          'budget',
        ] as const)
          requiredText(fields[key], 500);
        if (fields.date < '2026-11-05')
          run.infeasible = {
            name: 'Demo venue confirmation',
            lead_time_days: 14,
            earliest_date: '2026-11-05',
          };
        event.fields = fields;
        event.title = fields.title;
        event.venue = fields.venue;
        event.start = demoTimestamp(fields.date, fields.time);
        event.end = demoTimestamp(fields.date, fields.end_time);
        event.origins = Object.fromEntries(
          Object.keys(fields).map((k) => [
            k,
            { origin: fields[k as keyof EventFields] ? 'stated' : 'missing' },
          ]),
        );
      } else event.fields.has_prizes = text;
      run.status = 'working';
      run.phase = 'planning';
      run.polls = 0;
      delete run.question;
      charge(data, 'Event planning');
      result = run;
    } else if (/^\/events\/[^/]+\/rebuild$/.test(path) && method === 'POST') {
      const event = findEvent(data, path.split('/')[2]);
      charge(data, 'Event planning');
      result = { run_id: newRun(data, event, 'planning').run_id };
    } else if (/^\/events\/[^/]+\/approve-plan$/.test(path) && method === 'POST') {
      const event = findEvent(data, path.split('/')[2]);
      if (event.plan_outdated || event.revision !== body.revision || event.status !== 'planned')
        throw new ApiError('This plan changed. Rebuild and review it before approving.', 409);
      event.status = 'approved';
      event.approved_at = now();
      event.approved_by =
        data.members.find((m) => m.role === session.role)?.name ?? roleLabels[session.role];
      data.review = data.review.filter((r) => r.type !== 'plan' || r.event_id !== event.event_id);
      result = event;
    } else if (/^\/events\/[^/]+\/drafts\/[^/]+$/.test(path) && method === 'POST') {
      const event = findEvent(data, path.split('/')[2]);
      const type = path.split('/')[4] as DraftType;
      if (!(type in draftLabels)) throw new ApiError('Unknown draft type.', 404);
      const text =
        type === 'sponsor_email'
          ? `Hello,\n\nOur club is planning ${event.title} on ${event.fields.date}. We would love to discuss supporting this event.\n\nWould you be available to talk?\n\nThank you,\nThe ${club.name} cabinet`
          : type === 'expense'
            ? `Expense draft · ${event.title}\nEstimated budget: ${event.fields.budget || 'to confirm'} USD\nItems and totals: add verified amounts before submitting.\nThis text does not replace the official Expense Form.`
            : `${event.title}\n${event.fields.date} · ${event.fields.time}\n${event.venue}\n\n${event.fields.description}\n\n${body.instruction ? `Requested change: ${String(body.instruction).slice(0, 500)}` : 'Check all details before sharing.'}`;
      const draft: Draft = {
        type,
        text,
        updated_at: now(),
        ...(type === 'sponsor_email'
          ? { recipient: 'sponsor@example.com', subject: `${event.title} · partnership enquiry` }
          : {}),
      };
      event.drafts[type] = draft;
      charge(data, 'Drafts');
      result = draft;
    } else if (/^\/events\/[^/]+\/after-event$/.test(path) && method === 'POST') {
      const event = findEvent(data, path.split('/')[2]);
      if (event.fields.date > DEMO_TODAY)
        throw new ApiError('The after-event form opens on the event date.', 409);
      const answers = body.answers as Record<string, string>;
      if (!answers || !/^\d+$/.test(answers.attendance ?? ''))
        throw new ApiError('Enter the number of people who attended.', 422);
      event.after_event = answers;
      event.status = 'closed';
      const card = addFact(
        data,
        [answers.went_well, answers.went_wrong, answers.remember].filter(Boolean).join('\n') ||
          'No additional lessons recorded.',
        `${event.title} debrief`,
      );
      const draft: Draft = {
        type: 'impact_report',
        text: `${event.title}\nAttendance: ${answers.attendance}\nWhat went well: ${answers.went_well}\nWhat to improve: ${answers.went_wrong}\nLessons: ${answers.remember}\n\nDraft — review before submitting.`,
        updated_at: now(),
      };
      event.drafts.impact_report = draft;
      charge(data, 'After-event review');
      result = { draft, review_count: card ? 1 : 0 };
    } else if (/^\/events\/[^/]+$/.test(path)) {
      const event = findEvent(data, path.split('/')[2]);
      if (method === 'PATCH') {
        const fields = body.fields as Partial<EventFields>;
        if (!fields || typeof fields !== 'object')
          throw new ApiError('No changes were supplied.', 422);
        for (const key of Object.keys(fields))
          if (!(key in event.fields)) throw new ApiError('Unknown event field.', 422);
        event.fields = { ...event.fields, ...fields };
        event.title = event.fields.title;
        event.venue = event.fields.venue;
        event.start = demoTimestamp(event.fields.date, event.fields.time);
        event.end = demoTimestamp(event.fields.date, event.fields.end_time);
        event.revision++;
        event.plan_outdated = true;
        if (event.status === 'approved') event.status = 'planned';
      }
      result = event;
    } else if (path.startsWith('/tasks/') && method === 'PATCH') {
      const taskId = path.slice('/tasks/'.length);
      const event = data.events.find((e) => e.tasks.some((t) => t.task_id === taskId));
      const task = event?.tasks.find((t) => t.task_id === taskId);
      if (!task || !event) {
        if (taskId.startsWith('club/') && ['todo', 'done'].includes(String(body.state))) {
          (data.club_tasks ??= {})[taskId] = body.state as 'todo' | 'done';
          save(data);
          return {
            task_id: taskId,
            title: 'Club reminder',
            due: DEMO_TODAY,
            owner_role: 'president',
            state: body.state,
          };
        }
        throw new ApiError('Task not found.', 404);
      }
      if (body.state !== undefined) {
        if (!['todo', 'done', 'due_today', 'overdue'].includes(String(body.state)))
          throw new ApiError('Unknown task state.', 422);
        task.state = body.state as typeof task.state;
      }
      if (body.owner_role !== undefined) {
        if (!(String(body.owner_role) in roleLabels)) throw new ApiError('Unknown role.', 422);
        task.owner_role = body.owner_role as Role;
      }
      event.tasks_done = event.tasks.filter((t) => t.state === 'done').length;
      event.overdue_tasks = event.tasks.filter((t) => t.state === 'overdue').length;
      result = task;
    } else if (path === '/chat/ask' && method === 'POST') {
      const text = requiredText(body.text);
      charge(data, 'Chat');
      const disputed = /disagree|conflict/i.test(text)
        ? data.review.find((card) => card.type === 'disagreement' && card.status === 'pending')
        : undefined;
      const itemId = /last|learn|welcome/i.test(text)
        ? 'kh-demo-welcome'
        : /coffee|cedar|sponsor/i.test(text)
          ? 'kh-demo-coffee'
          : /venue|contact|hostler/i.test(text)
            ? 'kh-demo-contact'
            : '';
      const item = data.knowledge.find(
        (item) => item.item_id === itemId && item.status === 'current',
      );
      result =
        disputed && disputed.alternative
          ? ({
              kind: 'answer',
              known: true,
              text: `Two sources disagree: ${disputed.statement} ${disputed.alternative.statement}`,
              basis: 'disputed',
              citations: [disputed.source, disputed.alternative.source],
              review_id: disputed.id,
              fallback: options.scenario === 'fallback',
            } satisfies ChatReply)
          : item && !/insurance|open.water|unknown|not sure|outside guests/i.test(text)
            ? ({
                kind: 'answer',
                known: true,
                text: item.statement,
                basis: 'verified',
                citations: [{ ...item.sources[0], item_id: item.item_id }],
                fallback: options.scenario === 'fallback',
              } satisfies ChatReply)
            : ({
                kind: 'unknown',
                known: false,
                text: "I don't know this yet.",
                basis: 'none',
                ask: {
                  who: 'Student Activities Office or the outgoing cabinet',
                  role: 'Confirm the responsible contact',
                },
                look_in: 'The current official club handbook and approved cabinet notes',
                fallback: options.scenario === 'fallback',
              } satisfies ChatReply);
    } else if (path === '/chat/teach' && method === 'POST') {
      const text = requiredText(body.text);
      const card = addFact(data, text);
      charge(data, 'Learning');
      result = { kind: 'learned', text, review_id: card.id } satisfies ChatReply;
    } else if (path === '/review' && method === 'GET') {
      const filter = url.searchParams.get('filter');
      result =
        options.scenario === 'empty'
          ? []
          : data.review
              .filter(
                (r) =>
                  ['pending', 'waiting_second_president'].includes(r.status) &&
                  (filter === 'facts'
                    ? ['fact', 'merge', 'rule'].includes(r.type)
                    : filter === 'disagreements'
                      ? r.type === 'disagreement'
                      : filter === 'documents'
                        ? r.type === 'document'
                        : filter === 'plans'
                          ? r.type === 'plan'
                          : true),
              )
              .sort((a, b) => Number(b.type === 'rule') - Number(a.type === 'rule'));
    } else if (/^\/review\/[^/]+$/.test(path) && method === 'POST') {
      const card = data.review.find((r) => r.id === path.split('/')[2]);
      if (!card) throw new ApiError('Review item not found.', 404);
      if (card.status !== 'pending')
        throw new ApiError('This item has already been reviewed.', 409);
      const decision = String(body.decision);
      if (card.type === 'plan') throw new ApiError('Approve this plan from its event page.', 422);
      if (body.shared !== undefined && typeof body.shared !== 'boolean')
        throw new ApiError('Choose whether this knowledge is shared.', 422);
      if (card.type === 'rule' || isShared(card) || body.shared === true) mutateAllowed(true);
      if (
        !body.opened_at ||
        !body.decided_at ||
        new Date(String(body.decided_at)) < new Date(String(body.opened_at))
      )
        throw new ApiError('Please reload this review card.', 422);
      if (decision === 'both' && !String(body.reason ?? '').trim())
        throw new ApiError('Explain when each version is true.', 422);
      card.statement =
        typeof body.edited_text === 'string' && body.edited_text.trim()
          ? body.edited_text.trim()
          : card.statement;
      card.opened_at = String(body.opened_at);
      card.decided_at = String(body.decided_at);
      card.shared = typeof body.shared === 'boolean' ? body.shared : isShared(card);
      card.status = decision === 'reject' ? 'rejected' : 'approved';
      if (decision === 'both' && card.alternative)
        card.statement += `\nAlso true: ${card.alternative.statement}\nContext: ${String(body.reason)}`;
      if (card.status === 'approved' && card.type === 'document') {
        const document = data.knowledge.find((k) => k.status === 'may_be_outdated');
        if (document) {
          document.status = 'current';
          document.last_checked = DEMO_TODAY;
        }
      }
      if (
        card.status === 'approved' &&
        card.type !== 'document' &&
        !(card.type === 'merge' && decision === 'merge')
      )
        data.knowledge.push({
          item_id: id('kh'),
          title: card.title,
          statement:
            decision === 'keep_b' && card.alternative ? card.alternative.statement : card.statement,
          tab: 'tips',
          kind: card.kind,
          scope: card.shared ? 'aub' : 'club',
          sources: [card.source],
          last_checked: DEMO_TODAY,
          status: 'current',
          history: [
            {
              date: DEMO_TODAY,
              description: 'Approved by the demo cabinet',
              actor: roleLabels[session.role],
            },
          ],
          used_in: [],
        });
      result = card;
    } else if (path === '/calendar') {
      const month = url.searchParams.get('month') ?? '2026-10';
      const items: CalendarItem[] = data.events
        .filter((e) => ['approved', 'done', 'closed'].includes(e.status) && !e.plan_outdated)
        .flatMap((e) => [
          {
            item_id: `${e.event_id}/event`,
            event_id: e.event_id,
            kind: 'event' as const,
            title: e.title,
            date: e.fields.date,
            start: e.start,
            end: e.end,
            owner_role: 'all_cabinet' as const,
            status: 'open' as const,
          },
          ...e.tasks.map((t) => ({
            item_id: t.task_id,
            task_id: t.task_id,
            event_id: e.event_id,
            kind: 'task' as const,
            title: t.title,
            date: t.due,
            owner_role: t.owner_role,
            status: t.state === 'done' ? ('done' as const) : ('open' as const),
          })),
        ])
        .filter((i) => i.date.startsWith(month));
      if (options.scenario !== 'empty')
        items.push({
          item_id: `club/rule-check-${month}`,
          task_id: `club/rule-check-${month}`,
          event_id: null,
          kind: 'task',
          title: 'Check the current OSA documents',
          date: `${month}-01`,
          owner_role: 'president',
          status: data.club_tasks?.[`club/rule-check-${month}`] === 'done' ? 'done' : 'open',
        });
      result = {
        items: options.scenario === 'empty' ? [] : items,
        connected: data.connected,
        ...(data.connected ? { synced_at: now() } : {}),
      };
    } else if (path === '/knowledge') {
      const tab = url.searchParams.get('tab');
      const q = (url.searchParams.get('q') ?? '').toLowerCase();
      result =
        options.scenario === 'empty'
          ? []
          : data.knowledge
              .filter(
                (k) =>
                  k.status !== 'retired' &&
                  (!tab || k.tab === tab) &&
                  `${k.title} ${k.statement}`.toLowerCase().includes(q),
              )
              .map((k) =>
                session.role === 'adviser' && k.contact
                  ? { ...k, contact: { ...k.contact, email: undefined, phone: undefined } }
                  : k,
              );
    } else if (/^\/knowledge\/[^/]+$/.test(path)) {
      const fact = data.knowledge.find((k) => k.item_id === path.split('/')[2]);
      if (!fact) throw new ApiError('This item could not be found in your club.', 404);
      result =
        session.role === 'adviser' && fact.contact
          ? { ...fact, contact: { ...fact.contact, email: undefined, phone: undefined } }
          : fact;
    } else if (path.startsWith('/handover/')) {
      const role = path.split('/')[2] as Role;
      if (!(role in roleLabels)) throw new ApiError('Unknown role.', 404);
      result = {
        role,
        sections: [
          {
            title: 'Your role',
            entries: [
              {
                text: `${roleLabels[role]}: keep decisions clear and hand over the sources behind them.`,
                source: {
                  item_id: 'kh-demo-role-template',
                  label: 'Demo role template',
                  kind: 'document',
                  quote:
                    'Synthetic role checklist: keep decisions and their sources clear for the next officer.',
                },
              },
            ],
          },
          {
            title: 'Club know-how',
            entries: data.knowledge
              .filter(
                (k) => ['tips', 'rules', 'sponsors'].includes(k.tab) && k.status === 'current',
              )
              .map((k) => ({ text: k.statement, source: k.sources[0] })),
          },
        ],
        gaps: [
          {
            topic: 'Who owns the yearly handover?',
            ask: 'The outgoing president',
            look_in: 'Cabinet meeting notes',
          },
        ],
        ...(data.signoffs[role] &&
        data.signoff_versions?.[role] ===
          JSON.stringify(data.knowledge.filter((k) => k.status === 'current'))
          ? { signed_off_at: data.signoffs[role], signed_off_by: 'Alex Morgan' }
          : {}),
      };
    } else if (path === '/cabinet') {
      if (method === 'POST') {
        mutateAllowed(true);
        const role = String(body.role) as Role;
        if (!(role in roleLabels)) throw new ApiError('Choose a cabinet role.', 422);
        const email = requiredText(body.email, 254);
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
          throw new ApiError('Enter a valid email address.', 422);
        const member = { member_id: id('m'), name: requiredText(body.name, 120), email, role };
        data.members.push(member);
        result = member;
      } else if (method === 'DELETE') {
        mutateAllowed(true);
        const removing = data.members.find((m) => m.member_id === body.member_id);
        if (
          removing?.role === 'president' &&
          data.members.filter((m) => m.role === 'president').length < 2
        )
          throw new ApiError('Keep at least one president in the cabinet.', 422);
        data.members = data.members.filter((m) => m.member_id !== body.member_id);
      } else result = data.members;
    } else if (path === '/documents' && method === 'POST') {
      mutateAllowed(true);
      const file = (request.body as FormData).get('file');
      if (
        !(file instanceof File) ||
        file.size > 10 * 1024 * 1024 ||
        !/\.(pdf|txt|md|csv|eml|xlsx)$/i.test(file.name)
      )
        throw new ApiError('Choose a supported synthetic document smaller than 10 MB.', 422);
      const document: KnowledgeItem = {
        item_id: id('kh-doc'),
        title: file.name,
        statement: 'Uploaded for review. The contents have not been verified.',
        tab: 'documents',
        kind: 'document',
        scope: 'club',
        sources: [{ item_id: id('kh-upload'), label: file.name, kind: 'document' }],
        last_checked: DEMO_TODAY,
        status: 'may_be_outdated',
        year: '2026–27',
        history: [],
        used_in: [],
      };
      data.knowledge.push(document);
      addFact(data, `Please verify the contents of ${file.name}.`, 'Document upload');
      result = document;
    } else if (path === '/usage') result = data.usage;
    else if (path === '/setup/next' && method === 'POST') {
      mutateAllowed(true);
      if (body.answer !== undefined && data.setup_index < setupQuestions.length) {
        const text = requiredText(body.answer, 2000);
        if (text !== '[skip]') {
          addFact(data, text, `${club.name} setup`);
          charge(data, 'Club setup');
        }
        data.setup_index++;
      }
      if (data.setup_index >= setupQuestions.length) data.setup_complete = true;
      result = {
        question: setupQuestions[data.setup_index] ?? 'Your club is ready to start.',
        index: Math.min(data.setup_index + 1, 10),
        total: 10,
        done: data.setup_complete,
        rules_count: data.knowledge.filter((k) => k.scope === 'aub').length,
      };
    } else if (path.startsWith('/__ui/')) {
      const action = path.slice(6);
      if (action === 'approval') {
        const row = eventFromBody(data, body).approvals.find(
          (a) => a.approval_id === body.approval_id,
        );
        if (!row || !['needed', 'requested', 'granted'].includes(String(body.status)))
          throw new ApiError('Approval not found.', 404);
        row.status = body.status as typeof row.status;
      } else if (action === 'proposal') {
        const row = eventFromBody(data, body).proposal.find((a) => a.field_id === body.field_id);
        if (!row) throw new ApiError('Question not found.', 404);
        row.value = String(body.value);
        row.origin = row.value.trim() ? 'stated' : 'missing';
        delete row.source;
      } else if (action === 'draft') {
        const row = eventFromBody(data, body).drafts[body.type as DraftType];
        if (!row) throw new ApiError('Write the draft first.', 404);
        row.text = String(body.text);
        row.updated_at = now();
      } else if (action === 'leaders') {
        const event = eventFromBody(data, body);
        event.leaders = body.leaders as EventDetail['leaders'];
        event.route = String(body.route);
      } else if (action === 'knowledge-edit') {
        const fact = data.knowledge.find((k) => k.item_id === body.item_id);
        if (!fact) throw new ApiError('Fact not found.', 404);
        addFact(data, requiredText(body.text), `Suggested edit: ${fact.title}`);
      } else if (action === 'knowledge-retire') {
        const fact = data.knowledge.find((k) => k.item_id === body.item_id);
        if (!fact) throw new ApiError('Fact not found.', 404);
        if (fact.scope === 'aub') {
          mutateAllowed(true);
          data.review.push({
            id: id('review-rule'),
            type: 'rule',
            title: `Retire: ${fact.title}`,
            statement: `Proposed retirement: ${fact.statement}`,
            source: fact.sources[0],
            group: 'Shared rule changes',
            kind: 'rule',
            status: 'pending',
          });
        } else fact.status = 'retired';
      } else if (action === 'handover-signoff') {
        mutateAllowed(true);
        data.signoffs[body.role as Role] = now();
        (data.signoff_versions ??= {})[body.role as Role] = JSON.stringify(
          data.knowledge.filter((k) => k.status === 'current'),
        );
      } else if (action === 'google') {
        mutateAllowed(true);
        data.connected = Boolean(body.connected);
      } else if (action === 'member-role') {
        mutateAllowed(true);
        const member = data.members.find((m) => m.member_id === body.member_id);
        if (!member || !(String(body.role) in roleLabels))
          throw new ApiError('Member or role not found.', 404);
        if (
          member.role === 'president' &&
          body.role !== 'president' &&
          data.members.filter((m) => m.role === 'president').length < 2
        )
          throw new ApiError('Assign another president before changing this role.', 422);
        member.role = body.role as Role;
      } else if (action === 'run-continue') {
        const run = data.runs[String(body.run_id)];
        if (!run || run.status !== 'limit_reached')
          throw new ApiError('This run cannot continue.', 409);
        const next = newRun(data, findEvent(data, run.event_id!), 'resumed');
        charge(data, 'Event planning');
        result = { run_id: next.run_id };
      } else if (action === 'run-stop') {
        const run = data.runs[String(body.run_id)];
        if (run) {
          run.status = 'stopped';
          findEvent(data, run.event_id!).agent_run = clone(run);
        }
      } else if (action === 'feedback') {
        (data.feedback ??= []).push({
          id: String(body.id),
          value: String(body.value),
          reason: String(body.reason),
          recorded_at: now(),
        });
      } else throw new ApiError('This action is not available.', 404);
    } else throw new ApiError('This action is not available yet.', 404);
    save(data);
    return clone(result);
  };
}
