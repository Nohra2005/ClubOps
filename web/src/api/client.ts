import type {
  AgentRun,
  CalendarData,
  ChatReply,
  Draft,
  DraftType,
  EventDetail,
  EventFields,
  EventSummary,
  HandoverGuide,
  KnowledgeItem,
  KnowledgeTab,
  Me,
  Member,
  ReviewCard,
  ReviewDecision,
  ReviewFilter,
  Role,
  SetupStep,
  Task,
  Usage,
} from './types';

import { ApiError } from './errors';
import { readAgentRun, readAnswer, readDraft } from './contract-responses';
export { ApiError } from './errors';
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
}
export type Transport = (path: string, options?: RequestOptions) => Promise<unknown>;

export class ApiClient {
  constructor(
    private transport: Transport,
    readonly mode: 'demo' | 'http',
  ) {}
  private request<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.transport(path, options) as Promise<T>;
  }
  private post<T>(path: string, body?: unknown) {
    return this.request<T>(path, { method: 'POST', body });
  }
  private extension<T>(action: string, body?: unknown): Promise<T> {
    if (this.mode !== 'demo')
      return Promise.reject(
        new ApiError('This action is not available yet. Your changes are still on this page.', 501),
      );
    return this.post<T>(`/__ui/${action}`, body);
  }
  me() {
    return this.request<Me>('/me');
  }
  events() {
    return this.request<EventSummary[]>('/events');
  }
  event(id: string) {
    return this.request<EventDetail>(`/events/${encodeURIComponent(id)}`);
  }
  plan(description: string) {
    return this.post<{ run_id: string }>('/events/plan', { description });
  }
  async run(id: string, signal?: AbortSignal) {
    const value = await this.request<unknown>(`/runs/${encodeURIComponent(id)}`, { signal });
    return this.mode === 'http' ? readAgentRun(value, id) : (value as AgentRun);
  }
  async answerRun(id: string, text: string) {
    const value = await this.post<unknown>(`/runs/${encodeURIComponent(id)}/answer`, { text });
    return this.mode === 'http' ? readAgentRun(value, id) : (value as AgentRun);
  }
  editEvent(id: string, fields: Partial<EventFields>) {
    return this.request<EventDetail>(`/events/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: { fields },
    });
  }
  rebuild(id: string) {
    return this.post<{ run_id: string }>(`/events/${encodeURIComponent(id)}/rebuild`);
  }
  approvePlan(id: string, revision: number) {
    return this.post<EventDetail>(`/events/${encodeURIComponent(id)}/approve-plan`, { revision });
  }
  task(id: string, fields: Partial<Pick<Task, 'state' | 'owner_role'>>) {
    return this.request<Task>(`/tasks/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: fields,
    });
  }
  async draft(id: string, type: DraftType, instruction?: string) {
    const value = await this.post<unknown>(`/events/${encodeURIComponent(id)}/drafts/${type}`, {
      instruction,
    });
    return this.mode === 'http' ? readDraft(value, id, type) : (value as Draft);
  }
  afterEvent(id: string, answers: Record<string, string>) {
    return this.post<{ draft: Draft; review_count: number }>(
      `/events/${encodeURIComponent(id)}/after-event`,
      { answers },
    );
  }
  async ask(text: string) {
    const value = await this.post<unknown>('/chat/ask', { text });
    return this.mode === 'http' ? readAnswer(value) : (value as ChatReply);
  }
  async teach(text: string) {
    const value = await this.post<unknown>('/chat/teach', { text });
    return this.mode === 'http' ? readAnswer(value) : (value as ChatReply);
  }
  review(filter: ReviewFilter = 'all') {
    return this.request<ReviewCard[]>(`/review?filter=${filter}`);
  }
  decide(id: string, decision: ReviewDecision) {
    return this.post<ReviewCard>(`/review/${encodeURIComponent(id)}`, decision);
  }
  calendar(month: string) {
    return this.request<CalendarData>(`/calendar?month=${month}`);
  }
  knowledge(tab: KnowledgeTab | '', q = '') {
    return this.request<KnowledgeItem[]>(`/knowledge?tab=${tab}&q=${encodeURIComponent(q)}`);
  }
  fact(id: string) {
    return this.request<KnowledgeItem>(`/knowledge/${encodeURIComponent(id)}`);
  }
  handover(role: Role) {
    return this.request<HandoverGuide>(`/handover/${role}`);
  }
  cabinet() {
    return this.request<Member[]>('/cabinet');
  }
  addMember(member: Omit<Member, 'member_id'>) {
    return this.post<Member>('/cabinet', member);
  }
  removeMember(id: string) {
    return this.request<void>('/cabinet', { method: 'DELETE', body: { member_id: id } });
  }
  upload(file: File) {
    const body = new FormData();
    body.append('file', file);
    return this.post<KnowledgeItem>('/documents', body);
  }
  usage() {
    return this.request<Usage>('/usage');
  }
  setup(answer?: string) {
    return this.post<SetupStep>('/setup/next', answer === undefined ? {} : { answer });
  }
  approval(event_id: string, approval_id: string, status: string) {
    return this.extension('approval', { event_id, approval_id, status });
  }
  saveProposal(event_id: string, field_id: string, value: string) {
    return this.extension('proposal', { event_id, field_id, value });
  }
  saveDraft(event_id: string, type: DraftType, text: string) {
    return this.extension('draft', { event_id, type, text });
  }
  saveLeaders(event_id: string, leaders: EventDetail['leaders'], route: string) {
    return this.extension('leaders', { event_id, leaders, route });
  }
  feedback(id: string, value: string, reason: string) {
    return this.extension('feedback', { id, value, reason });
  }
  suggestEdit(item_id: string, text: string) {
    return this.extension('knowledge-edit', { item_id, text });
  }
  retire(item_id: string) {
    return this.extension('knowledge-retire', { item_id });
  }
  signOff(role: Role) {
    return this.extension('handover-signoff', { role });
  }
  google(connected: boolean) {
    return this.extension('google', { connected });
  }
  changeRole(member_id: string, role: Role) {
    return this.extension('member-role', { member_id, role });
  }
  async continueRun(run_id: string) {
    if (this.mode === 'http') {
      const value = await this.post<unknown>(`/runs/${encodeURIComponent(run_id)}/continue`);
      return { run_id: readAgentRun(value, run_id).run_id };
    }
    return this.extension<{ run_id: string }>('run-continue', { run_id });
  }
  stopRun(run_id: string) {
    return this.extension('run-stop', { run_id });
  }
}

export function httpTransport(base = '/api'): Transport {
  return async (path, options = {}) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 65_000);
    const abort = () => controller.abort();
    options.signal?.addEventListener('abort', abort, { once: true });
    if (options.signal?.aborted) controller.abort();
    try {
      const form = options.body instanceof FormData;
      const method = options.method ?? 'GET';
      const response = await fetch(`${base.replace(/\/$/, '')}${path}`, {
        method,
        credentials: 'include',
        headers: {
          ...(method !== 'GET' ? { 'X-Requested-With': 'ClubOps' } : {}),
          ...(options.body && !form ? { 'Content-Type': 'application/json' } : {}),
        },
        body: options.body
          ? form
            ? (options.body as FormData)
            : JSON.stringify(options.body)
          : undefined,
        signal: controller.signal,
      });
      if (!response.ok)
        throw new ApiError(
          response.status === 401
            ? 'Please sign in to continue.'
            : response.status === 403
              ? "You don't have permission for this action."
              : response.status === 409
                ? 'This item changed. Reload it before approving.'
                : response.status === 501
                  ? 'This feature is not connected to the server yet. Your edits are still here.'
                  : "ClubOps couldn't finish this. Your edits are still on this page.",
          response.status,
        );
      if (response.status === 204) return undefined;
      if (!response.headers.get('content-type')?.includes('application/json'))
        throw new ApiError('ClubOps returned an unreadable response. Please try again.', 502);
      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (options.signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
      throw new ApiError(
        controller.signal.aborted
          ? 'This took too long. Your edits are still here. Try again.'
          : "Can't reach ClubOps. Your edits are kept on this page.",
      );
    } finally {
      clearTimeout(timeout);
      options.signal?.removeEventListener('abort', abort);
    }
  };
}
