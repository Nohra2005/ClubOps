/** Frontend view models from the UI spec. These do not change the Python contracts. */
export type Role =
  | 'president'
  | 'vice_president'
  | 'secretary'
  | 'treasurer'
  | 'events'
  | 'sponsorship'
  | 'communications'
  | 'adviser';
export const roles: Role[] = [
  'president',
  'vice_president',
  'secretary',
  'treasurer',
  'events',
  'sponsorship',
  'communications',
  'adviser',
];
export const roleLabels: Record<Role, string> = {
  president: 'President',
  vice_president: 'Vice president',
  secretary: 'Secretary',
  treasurer: 'Treasurer',
  events: 'Events',
  sponsorship: 'Sponsorship',
  communications: 'Communications',
  adviser: 'Adviser',
};
export type Origin = 'stated' | 'retrieved' | 'computed' | 'inferred' | 'default' | 'missing';
export type EventStatus = 'draft' | 'planned' | 'approved' | 'done' | 'closed' | 'cancelled';
export type TaskState = 'todo' | 'due_today' | 'overdue' | 'done';
export type KnowledgeTab = 'rules' | 'tips' | 'documents' | 'contacts' | 'sponsors';
export type DraftType =
  | 'announcement'
  | 'reminder'
  | 'sponsor_email'
  | 'instagram'
  | 'poster'
  | 'expense'
  | 'volunteers'
  | 'impact_report';
export const draftLabels: Record<DraftType, string> = {
  announcement: 'WhatsApp announcement',
  reminder: 'Reminder message',
  sponsor_email: 'Sponsor email',
  instagram: 'Instagram caption',
  poster: 'Poster text',
  expense: 'Expense form',
  volunteers: 'Volunteer shifts',
  impact_report: 'Impact report',
};
export interface Club {
  id: string;
  name: string;
  initials: string;
  setup_complete: boolean;
}
export interface Member {
  member_id: string;
  name: string;
  email: string;
  role: Role;
}
export interface Me {
  user: Member;
  role: Role;
  club: Club;
  counts: { overdue_events: number; review: number; reminders: number };
  demo?: boolean;
}
export interface Source {
  item_id: string;
  label: string;
  quote?: string;
  kind?: 'document' | 'email' | 'note' | 'debrief';
  authority?: 'official_document' | 'office_email' | 'stated_by_president';
}
export interface Provenance {
  origin: Origin;
  source?: Source;
}
export interface EventFields {
  title: string;
  date: string;
  time: string;
  end_time: string;
  venue: string;
  audience: string;
  expected_attendance: string;
  budget: string;
  sponsors: string;
  has_prizes: string;
  catering: string;
  partner_clubs: string;
  description: string;
}
export interface EventSummary {
  event_id: string;
  title: string;
  start: string;
  end: string;
  venue: string;
  status: EventStatus;
  task_count: number;
  tasks_done: number;
  overdue_tasks: number;
  event_type: string;
  plan_outdated: boolean;
}
export interface Approval {
  approval_id: string;
  name: string;
  why: string;
  deadline: string;
  status: 'needed' | 'requested' | 'granted';
  uncertain: boolean;
  source: Source;
}
export interface Task {
  task_id: string;
  event_id?: string;
  title: string;
  due: string;
  owner_role: Role;
  state: TaskState;
  requirement_id?: string;
  source?: Source;
}
export interface ProposalAnswer {
  field_id: string;
  label: string;
  value: string;
  origin: Origin;
  source?: Source;
}
export interface Draft {
  type: DraftType;
  text: string;
  recipient?: string;
  subject?: string;
  updated_at?: string;
  template_version?: string;
  based_on?: string[];
  state?: 'draft';
}
export interface Tip {
  item_id: string;
  title: string;
  statement: string;
  source: Source;
}
export interface Leader {
  id: string;
  name: string;
  pace: string;
}
export interface EventDetail extends EventSummary {
  revision: number;
  fields: EventFields;
  origins: Record<string, Provenance>;
  approvals: Approval[];
  tasks: Task[];
  proposal: ProposalAnswer[];
  drafts: Partial<Record<DraftType, Draft>>;
  tips: Tip[];
  leaders: Leader[];
  route: string;
  agent_run?: AgentRun;
  approved_at?: string;
  approved_by?: string;
  after_event?: Record<string, string>;
}
export interface AgentStep {
  n: number;
  tool?: string;
  text: string;
  state: 'done' | 'running' | 'question' | 'not_done' | 'failed';
}
export interface AgentRun {
  run_id: string;
  status: 'working' | 'waiting_for_user' | 'limit_reached' | 'done' | 'stopped' | 'failed';
  steps: AgentStep[];
  steps_used: number;
  step_limit: number;
  cost_usd: number;
  cost_limit_usd?: number;
  event_id?: string;
  question?: { text: string; kind: 'details' | 'text' };
  details?: EventFields;
  origins?: Record<string, Provenance>;
  fallback?: boolean;
  infeasible?: { name: string; lead_time_days: number; earliest_date: string };
}
export type ChatReply =
  | {
      kind: 'answer';
      known: true;
      text: string;
      basis: 'verified' | 'single_source' | 'disputed';
      citations: Source[];
      review_id?: string;
      fallback?: boolean;
    }
  | {
      kind: 'unknown';
      known: false;
      text: string;
      basis: 'none';
      ask: { who: string; role?: string | null };
      look_in?: string | null;
      fallback?: boolean;
    }
  | { kind: 'learned'; text: string; review_id: string };
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  reply?: ChatReply;
  feedback?: 'up' | 'down';
}
export type ReviewType = 'fact' | 'merge' | 'disagreement' | 'document' | 'plan' | 'rule';
export type ReviewFilter = 'all' | 'facts' | 'disagreements' | 'documents' | 'plans';
export interface ReviewCard {
  id: string;
  type: ReviewType;
  title: string;
  statement: string;
  source: Source;
  group: string;
  kind: string;
  op?: 'create' | 'merge' | 'update' | 'contradiction' | 'retire';
  alternative?: { statement: string; source: Source; valid_to?: string | null };
  event_id?: string;
  status: 'pending' | 'waiting_second_president' | 'approved' | 'rejected';
  opened_at?: string;
  decided_at?: string;
  warning?: string;
  outdated?: boolean;
  unlisted?: boolean;
  shared?: boolean;
  /** True on a Replace-old / Same-as card: the new version keeps the known fact's layer. */
  shared_locked?: boolean;
  /** End date (YYYY-MM-DD), or null when the fact never ends. Absent on cards from older servers. */
  valid_to?: string | null;
  /** Why ClubOps proposed this card, plain text. */
  why?: string;
  /** A rule's notice period in days (the longest one). */
  lead_time_days?: number;
}
export interface ReviewDecision {
  decision: string;
  shared?: boolean;
  edited_text?: string;
  /** YYYY-MM-DD sets the end date, '' clears it, absent keeps ClubOps' guess. */
  valid_to?: string;
  /** A rule's notice period in days; absent keeps ClubOps' guess. */
  lead_time_days?: number;
  reason?: string;
  opened_at: string;
  decided_at: string;
}
export interface CalendarItem {
  item_id: string;
  club_id?: string;
  event_id: string | null;
  task_id?: string;
  kind: 'event' | 'task';
  title: string;
  date: string;
  start?: string | null;
  end?: string | null;
  owner_role: Role | 'member' | 'all_cabinet';
  reminders?: {
    before_days?: number | null;
    on_day_at?: string | null;
    after_days?: number | null;
  }[];
  repeat_until_done?: boolean;
  link?: string | null;
  status: 'open' | 'done' | 'cancelled';
}
export interface CalendarData {
  items: CalendarItem[];
  connected: boolean;
  synced_at?: string;
}
export interface KnowledgeItem {
  item_id: string;
  title: string;
  statement: string;
  tab: KnowledgeTab;
  kind: string;
  scope: 'club' | 'aub';
  sources: Source[];
  last_checked: string;
  /** End date (YYYY-MM-DD), or null when the fact never ends. */
  valid_to?: string | null;
  last_used?: string;
  status: 'current' | 'may_be_outdated' | 'retired';
  triggers?: string;
  requirements?: string;
  lead_time_days?: number;
  year?: string;
  contact?: { name: string; role: string; office: string; email?: string; phone?: string };
  offers?: string;
  last_event?: string;
  history: { date: string; description: string; actor: string }[];
  used_in: { event_id: string; title: string }[];
  auto?: boolean;
}
export interface HandoverGuide {
  role: Role;
  sections: { title: string; entries: { text: string; source: Source; sources?: Source[] }[] }[];
  gaps: { topic: string; ask: string; look_in: string; question?: string }[];
  signed_off_at?: string;
  signed_off_by?: string;
}
export interface Usage {
  month: string;
  cost_usd: number;
  calls: number;
  calls_label?: string;
  run_metrics?: {
    recorded_runs: number;
    successful_plans: number;
    failed_runs: number;
    cost_per_successful_plan: number | null;
  };
  trace_metrics_available?: boolean;
  trace_metrics?: {
    name: string;
    calls: number;
    tokens_in: number;
    tokens_out: number;
    latency_ms: number;
    retries: number;
    failures: number;
    cost_usd: number;
  }[];
  metrics_note?: string;
  most_expensive_feature: string;
  by_feature: { name: string; calls: number; cost_usd: number }[];
}
export interface SetupStep {
  question: string;
  index: number;
  total: number;
  done: boolean;
  rules_count: number;
}
export interface Workspace {
  events: EventDetail[];
  review: ReviewCard[];
  knowledge: KnowledgeItem[];
  members: Member[];
  runs: Record<string, AgentRun & { polls?: number; phase?: string }>;
  connected: boolean;
  usage: Usage;
  setup_index: number;
  setup_complete: boolean;
  signoffs: Partial<Record<Role, string>>;
  signoff_versions?: Partial<Record<Role, string>>;
  feedback?: { id: string; value: string; reason: string; recorded_at: string }[];
  club_tasks?: Record<string, TaskState>;
}
