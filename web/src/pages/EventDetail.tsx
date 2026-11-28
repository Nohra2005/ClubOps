import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import {
  ArrowLeft,
  CalendarDays,
  Clock3,
  Copy,
  Download,
  Edit3,
  LockKeyhole,
  MapPin,
  MessageCircle,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { useApp } from '../AppContext';
import { DEMO_TODAY } from '../api/fixtures';
import {
  roleLabels,
  roles,
  type EventDetail as EventData,
  type ProposalAnswer,
  type DraftType,
} from '../api/types';
import { AgentSteps } from '../components/AgentSteps';
import { DraftCard } from '../components/DraftCard';
import { EventFieldsForm, validateEventFields } from '../components/EventFieldsForm';
import { Feedback } from '../components/Feedback';
import {
  PageHeading,
  ApproveBar,
  EmptyState,
  ErrorNotice,
  FilterTabs,
  Modal,
  OriginTag,
  Resource,
  SourceChip,
  StatusBadge,
} from '../components/ui';
import { useAction, useResource } from '../hooks';
import { copyText, downloadText, formatDate, formatTime, todayInBeirut } from '../lib';

function EditEvent({
  event,
  onClose,
  onSaved,
}: {
  event: EventData;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { api } = useApp();
  const action = useAction();
  const [fields, setFields] = useState(event.fields);
  const [error, setError] = useState('');
  return (
    <Modal open title="Edit event details" onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const error = validateEventFields(fields);
          setError(error ?? '');
          if (error) return;
          const result = await action.run(() => api.editEvent(event.event_id, fields));
          if (result.ok) onSaved();
        }}
      >
        <p>
          Changing details creates a new revision. Review a rebuilt plan before approving it again.
        </p>
        <EventFieldsForm fields={fields} onChange={setFields} />
        <ErrorNotice message={error || action.error} />
        <div className="form-actions">
          <button className="button primary" disabled={action.pending}>
            {action.pending ? 'Saving…' : 'Save details'}
          </button>
          <button type="button" className="button" onClick={onClose}>
            Cancel
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ProposalRow({ answer, onSaved }: { answer: ProposalAnswer; onSaved: () => void }) {
  const { api, canEdit } = useApp();
  const { id = '' } = useParams();
  const action = useAction();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(answer.value);
  return (
    <div className={`proposal-row${!answer.value ? ' is-missing' : ''}`}>
      <span className="question-number">{answer.field_id.toUpperCase()}</span>
      <div>
        <div className="proposal-label">
          <h3>{answer.label}</h3>
          <OriginTag origin={answer.origin} />
        </div>
        {editing ? (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const result = await action.run(() => api.saveProposal(id, answer.field_id, value));
              if (result.ok) {
                setEditing(false);
                onSaved();
              }
            }}
          >
            <label className="field">
              <span className="sr-only">Answer to {answer.label}</span>
              <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                rows={3}
                maxLength={3000}
                autoFocus
              />
            </label>
            <div className="form-actions">
              <button className="button small primary" disabled={action.pending}>
                Save answer
              </button>
              <button className="button small" type="button" onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <>
            <p className={!answer.value ? 'missing-value' : ''}>
              {answer.value || 'Needs your input'}
            </p>
            {answer.source ? (
              <SourceChip source={answer.source} />
            ) : (
              answer.value && <span className="source-note">Confirmed event details</span>
            )}
          </>
        )}
        <ErrorNotice message={action.error} />
      </div>
      {canEdit && !editing && (
        <button
          className="icon-button"
          aria-label={`Edit ${answer.label}`}
          onClick={() => setEditing(true)}
        >
          <Edit3 size={14} />
        </button>
      )}
    </div>
  );
}

function RunPlanner({ event, onSaved }: { event: EventData; onSaved: () => void }) {
  const { api, canEdit } = useApp();
  const action = useAction();
  const [leaders, setLeaders] = useState(event.leaders);
  const [route, setRoute] = useState(event.route);
  const [editing, setEditing] = useState(false);
  return (
    <section className="panel run-planner">
      <div className="panel-header">
        <div>
          <h3>The run planner</h3>
          <p>Route, pace groups, and who is leading the way.</p>
        </div>
        {canEdit && (
          <button className="text-button" onClick={() => setEditing(!editing)}>
            {editing ? 'Cancel' : 'Edit groups'}
          </button>
        )}
      </div>
      {leaders.filter((l) => l.name.trim()).length < 3 && (
        <div className="notice warning">
          Fewer than 3 leaders are assigned. Check coverage before the run.
        </div>
      )}
      {editing ? (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const result = await action.run(() => api.saveLeaders(event.event_id, leaders, route));
            if (result.ok) {
              setEditing(false);
              onSaved();
            }
          }}
        >
          <label className="field">
            <span>Route</span>
            <input
              value={route}
              onChange={(e) => setRoute(e.target.value)}
              required
              maxLength={500}
            />
          </label>
          {leaders.map((leader, i) => (
            <div className="leader-edit" key={leader.id}>
              <label className="field">
                <span>Leader {i + 1}</span>
                <input
                  value={leader.name}
                  required
                  maxLength={120}
                  onChange={(e) =>
                    setLeaders(
                      leaders.map((l) => (l.id === leader.id ? { ...l, name: e.target.value } : l)),
                    )
                  }
                />
              </label>
              <label className="field">
                <span>Pace group</span>
                <input
                  value={leader.pace}
                  required
                  maxLength={120}
                  onChange={(e) =>
                    setLeaders(
                      leaders.map((l) => (l.id === leader.id ? { ...l, pace: e.target.value } : l)),
                    )
                  }
                />
              </label>
              <button
                className="icon-button"
                type="button"
                aria-label={`Remove leader ${i + 1}`}
                onClick={() => setLeaders(leaders.filter((l) => l.id !== leader.id))}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <div className="form-actions">
            <button
              type="button"
              className="button small"
              onClick={() =>
                setLeaders([...leaders, { id: crypto.randomUUID(), name: '', pace: '' }])
              }
            >
              <Plus size={12} /> Add leader
            </button>
            <button className="button small primary" disabled={action.pending}>
              Save groups
            </button>
          </div>
          <ErrorNotice message={action.error} />
        </form>
      ) : (
        <>
          <p className="inline-note">
            <MapPin size={12} /> {event.route}
          </p>
          <div className="leader-list">
            {event.leaders.map((l) => (
              <div key={l.id}>
                <span className="avatar">
                  {l.name
                    .split(' ')
                    .map((n) => n[0])
                    .slice(0, 2)
                    .join('')}
                </span>
                <strong>
                  {l.name}
                  <small>{l.pace}</small>
                </strong>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function AfterEvent({ event, onSaved }: { event: EventData; onSaved: () => void }) {
  const { api, canEdit, notify, refresh } = useApp();
  const action = useAction();
  const [answers, setAnswers] = useState<Record<string, string>>(
    event.after_event ?? {
      attendance: '',
      went_well: '',
      went_wrong: '',
      sponsors: '',
      remember: '',
    },
  );
  if (event.fields.date > (api.mode === 'demo' ? DEMO_TODAY : todayInBeirut()))
    return (
      <EmptyState
        title="The story isn't finished yet."
        description={`The after-event form opens on ${formatDate(event.fields.date)}. Come back to keep the lessons once the event is over.`}
        action={
          <span className="locked-note">
            <LockKeyhole size={14} /> Available after the event
          </span>
        }
      />
    );
  async function submit(e: FormEvent) {
    e.preventDefault();
    const result = await action.run(() => api.afterEvent(event.event_id, answers));
    if (result.ok) {
      notify('Lessons sent to Review. They are not approved facts yet.');
      refresh();
      onSaved();
    }
  }
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>Keep the good lessons.</h2>
          <p>Your answers become proposals in Review. Nothing is learned silently.</p>
        </div>
      </div>
      <form onSubmit={submit}>
        <div className="form-grid">
          {[
            { key: 'attendance', label: 'How many people came?' },
            { key: 'sponsors', label: 'Which sponsors helped?' },
            { key: 'went_well', label: 'What went well?' },
            { key: 'went_wrong', label: 'What could be better?' },
            { key: 'remember', label: 'Anything the next cabinet should remember?' },
          ].map(({ key, label }) => (
            <label className={`field${key === 'remember' ? ' wide' : ''}`} key={key}>
              <span>{label}</span>
              {key === 'attendance' ? (
                <input
                  type="number"
                  min="0"
                  step="1"
                  required
                  value={answers[key]}
                  onChange={(e) => setAnswers({ ...answers, [key]: e.target.value })}
                  readOnly={!canEdit}
                />
              ) : (
                <textarea
                  rows={3}
                  value={answers[key]}
                  maxLength={2000}
                  onChange={(e) => setAnswers({ ...answers, [key]: e.target.value })}
                  readOnly={!canEdit}
                />
              )}
            </label>
          ))}
        </div>
        {canEdit && (
          <div className="form-actions">
            <button className="button primary" disabled={action.pending}>
              {action.pending
                ? 'Saving…'
                : event.after_event
                  ? 'Update after-event form'
                  : 'Send lessons to Review'}
            </button>
          </div>
        )}
        <ErrorNotice message={action.error} />
      </form>
      {event.drafts.impact_report && (
        <div className="impact-draft">
          <DraftCard
            type="impact_report"
            draft={event.drafts.impact_report}
            canEdit={canEdit}
            onGenerate={async (instruction) => {
              await api.draft(event.event_id, 'impact_report', instruction);
              onSaved();
            }}
            onSave={async (text) => {
              await api.saveDraft(event.event_id, 'impact_report', text);
              onSaved();
            }}
          />
        </div>
      )}
    </div>
  );
}

export default function EventDetail() {
  const { id = '' } = useParams();
  const { api, canEdit, notify, refresh } = useApp();
  const event = useResource(() => api.event(id), [api, id]);
  const members = useResource(() => api.cabinet(), [api]);
  const action = useAction();
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const tab = search.get('tab') ?? 'approvals';
  const [editing, setEditing] = useState(false);
  const [rebuild, setRebuild] = useState(false);
  const data = event.value;
  const reloaded = () => {
    event.reload();
    refresh();
  };
  return (
    <>
      <Link to="/events" className="back-link">
        <ArrowLeft size={14} /> All events
      </Link>
      <Resource loading={event.loading} error={event.error} retry={event.reload}>
        {data && (
          <>
            <PageHeading
              title={data.title}
              description={`Revision ${data.revision} ? ${formatDate(data.start, true)} · ${formatTime(data.start)}–${formatTime(data.end)} · ${data.venue}`}
              action={
                <div className="event-heading-actions">
                  <StatusBadge status={data.status} />
                  {api.mode === 'demo' && (
                    <Link
                      className="button"
                      to={`/chat?event=${encodeURIComponent(data.event_id)}&new=1`}
                    >
                      <MessageCircle size={14} /> Event chat
                    </Link>
                  )}
                  {canEdit && (
                    <button className="button" onClick={() => setEditing(true)}>
                      <Edit3 size={13} /> Edit details
                    </button>
                  )}
                </div>
              }
            />
            <div className="event-facts">
              <span>
                <CalendarDays size={14} />
                {formatDate(data.start)}
              </span>
              <span>
                <Clock3 size={14} />
                {formatTime(data.start)}
              </span>
              <span>
                <MapPin size={14} />
                {data.venue}
              </span>
              <span className="event-facts-right">
                {data.tasks_done} of {data.task_count} tasks done
              </span>
            </div>
            {data.plan_outdated && (
              <div className="notice warning">
                <RefreshCw size={17} />
                <div>
                  <strong>Plan is out of date — rebuild.</strong>
                  <p>The event details changed. Review a fresh plan before approving.</p>
                  {canEdit && (
                    <button
                      className="button small"
                      onClick={() => setRebuild(true)}
                      disabled={action.pending}
                    >
                      Rebuild plan
                    </button>
                  )}
                </div>
              </div>
            )}
            {data.agent_run?.infeasible && (
              <div className="notice error">
                <div>
                  <strong>
                    Too late for: {data.agent_run.infeasible.name} (needs{' '}
                    {data.agent_run.infeasible.lead_time_days} days).
                  </strong>
                  <p>
                    Earliest possible date: {formatDate(data.agent_run.infeasible.earliest_date)}.
                  </p>
                  {canEdit && (
                    <button className="button small" onClick={() => setEditing(true)}>
                      Change date
                    </button>
                  )}
                </div>
              </div>
            )}
            <FilterTabs
              value={tab}
              onChange={(tab) => setSearch({ tab })}
              label="Event sections"
              options={[
                { value: 'approvals', label: 'Approvals', count: data.approvals.length },
                { value: 'tasks', label: 'Tasks', count: data.tasks.length },
                { value: 'proposal', label: 'Proposal' },
                { value: 'drafts', label: 'Drafts' },
                { value: 'tips', label: 'Tips' },
                { value: 'after', label: 'After the event' },
              ]}
            />
            {tab === 'approvals' && (
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h2>What needs a green light?</h2>
                    <p>Check why each item applies and the source behind it.</p>
                  </div>
                </div>
                <div className="approval-list">
                  {data.approvals.map((row) => (
                    <div
                      className={`approval-row${row.uncertain ? ' uncertain-row' : ''}`}
                      key={row.approval_id}
                    >
                      <div>
                        <h3>{row.name}</h3>
                        <p>{row.why}</p>
                        <SourceChip source={row.source} />
                      </div>
                      <div className="approval-deadline">
                        <span>Due</span>
                        <strong>{formatDate(row.deadline)}</strong>
                        {row.uncertain && <StatusBadge status="uncertain" />}
                      </div>
                      {canEdit ? (
                        <label className="field">
                          <span className="sr-only">Status for {row.name}</span>
                          <select
                            value={row.status}
                            disabled={action.pending}
                            onChange={async (e) => {
                              const result = await action.run(() =>
                                api.approval(id, row.approval_id, e.target.value),
                              );
                              if (result.ok) event.reload();
                            }}
                          >
                            <option value="needed">Needed</option>
                            <option value="requested">Requested</option>
                            <option value="granted">Granted</option>
                          </select>
                        </label>
                      ) : (
                        <StatusBadge status={row.status} />
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}
            {tab === 'tasks' && (
              <>
                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <h2>A clear next step.</h2>
                      <p>Tasks are assigned by role, so they stay with the club.</p>
                    </div>
                  </div>
                  <div className="task-list">
                    {[...data.tasks]
                      .sort((a, b) => a.due.localeCompare(b.due))
                      .map((task) => (
                        <div
                          className={`task-row${task.state === 'done' ? ' task-done' : ''}`}
                          key={task.task_id}
                        >
                          {canEdit ? (
                            <input
                              type="checkbox"
                              aria-label={`Mark ${task.title} done`}
                              checked={task.state === 'done'}
                              disabled={action.pending}
                              onChange={async (e) => {
                                const result = await action.run(() =>
                                  api.task(task.task_id, {
                                    state: e.target.checked
                                      ? 'done'
                                      : task.due <
                                          (api.mode === 'demo' ? DEMO_TODAY : todayInBeirut())
                                        ? 'overdue'
                                        : 'todo',
                                  }),
                                );
                                if (result.ok) reloaded();
                              }}
                            />
                          ) : (
                            <span className="task-read-marker">
                              {task.state === 'done' ? '✓' : '○'}
                            </span>
                          )}
                          <div className="task-title">
                            <h3>{task.title}</h3>
                            {task.source && <SourceChip source={task.source} />}
                          </div>
                          <div>
                            <span className="due-label">{formatDate(task.due)}</span>
                            <StatusBadge status={task.state} />
                          </div>
                          {canEdit ? (
                            <select
                              aria-label={`Role for ${task.title}`}
                              value={task.owner_role}
                              title={
                                members.value?.find((m) => m.role === task.owner_role)?.name ??
                                'No role holder assigned'
                              }
                              onChange={async (e) => {
                                const result = await action.run(() =>
                                  api.task(task.task_id, {
                                    owner_role: e.target.value as typeof task.owner_role,
                                  }),
                                );
                                if (result.ok) event.reload();
                              }}
                              disabled={action.pending}
                            >
                              {roles
                                .filter((r) => r !== 'adviser')
                                .map((role) => (
                                  <option key={role} value={role}>
                                    {roleLabels[role]}
                                  </option>
                                ))}
                            </select>
                          ) : (
                            <span className="role-label">{roleLabels[task.owner_role]}</span>
                          )}
                        </div>
                      ))}
                  </div>
                </section>
                {data.event_type === 'weekly_run' && (
                  <RunPlanner event={data} onSaved={event.reload} />
                )}
              </>
            )}
            {tab === 'proposal' && (
              <section className="panel proposal-panel">
                <div className="panel-header">
                  <div>
                    <h2>The OSA proposal draft</h2>
                    <p>33 questions. Check missing answers and every source before submitting.</p>
                  </div>
                  <div className="compact-actions">
                    <button
                      className="button small"
                      onClick={async () => {
                        const result = await action.run(() =>
                          copyText(
                            data.proposal
                              .map(
                                (a) =>
                                  `${a.field_id.toUpperCase()} · ${a.label}\n${a.value || '[Needs your input]'}`,
                              )
                              .join('\n\n'),
                          ),
                        );
                        if (result.ok) notify('Proposal copied. Nothing was submitted.');
                      }}
                    >
                      <Copy size={12} /> Copy all
                    </button>
                    <button
                      className="button small"
                      onClick={() =>
                        downloadText(
                          `${data.event_id}-proposal.txt`,
                          data.proposal
                            .map(
                              (a) =>
                                `${a.field_id.toUpperCase()} · ${a.label}\n${a.value || '[Needs your input]'}`,
                            )
                            .join('\n\n'),
                        )
                      }
                    >
                      <Download size={12} /> Download text
                    </button>
                  </div>
                </div>
                {api.mode === 'demo' && (
                  <p className="inline-note">
                    Use sample information in this demo. This draft is never submitted to OSA.
                  </p>
                )}
                {data.proposal.map((answer) => (
                  <ProposalRow
                    key={`${answer.field_id}-${answer.value}`}
                    answer={answer}
                    onSaved={event.reload}
                  />
                ))}
              </section>
            )}
            {tab === 'drafts' && (
              <>
                <p className="inline-note">
                  Write only what you need. Each Write draft or Rewrite click uses AI. All text
                  stays a draft until you copy or open it.
                </p>
                <div className="draft-grid">
                  {(
                    [
                      'announcement',
                      'reminder',
                      'sponsor_email',
                      'instagram',
                      'poster',
                      'expense',
                      'volunteers',
                    ] as DraftType[]
                  ).map((type) => (
                    <DraftCard
                      key={type}
                      type={type}
                      draft={data.drafts[type]}
                      canEdit={canEdit}
                      onGenerate={async (instruction) => {
                        await api.draft(id, type, instruction);
                        event.reload();
                      }}
                      onSave={async (text) => {
                        await api.saveDraft(id, type, text);
                        event.reload();
                      }}
                    />
                  ))}
                </div>
              </>
            )}
            {tab === 'tips' && (
              <div className="tips-grid">
                {data.tips.map((tip) => (
                  <section className="panel" key={tip.item_id}>
                    <h3>{tip.title}</h3>
                    <p>{tip.statement}</p>
                    <SourceChip source={tip.source} />
                    <Feedback id={tip.item_id} />
                  </section>
                ))}
              </div>
            )}
            {tab === 'after' && <AfterEvent event={data} onSaved={event.reload} />}
            <ErrorNotice message={action.error} />
            {data.agent_run && <AgentSteps run={data.agent_run} folded />}
            {data.status === 'planned' && !data.plan_outdated && canEdit && (
              <ApproveBar
                title="Ready for your cabinet's approval."
                description={
                  api.mode === 'demo'
                    ? 'Demo approval updates this workspace only. No Google Calendar is changed.'
                    : 'Approving adds the plan’s tasks to your club calendar.'
                }
                pending={action.pending}
                onChanges={() => setEditing(true)}
                onApprove={async () => {
                  const result = await action.run(() => api.approvePlan(id, data.revision));
                  if (result.ok) {
                    notify(
                      api.mode === 'demo'
                        ? 'Plan approved in the demo. No external calendar was changed.'
                        : 'Plan approved.',
                    );
                    reloaded();
                  }
                }}
              />
            )}
            {data.approved_at && data.status === 'approved' && (
              <ApproveBar
                title=""
                description={`${formatDate(data.approved_at, true)} · this revision is approved.`}
                approvedBy={
                  members.value?.find((member) => member.member_id === data.approved_by)?.name ??
                  data.approved_by
                }
              />
            )}
            {editing && (
              <EditEvent
                event={data}
                onClose={() => setEditing(false)}
                onSaved={() => {
                  setEditing(false);
                  reloaded();
                }}
              />
            )}
            <Modal open={rebuild} title="Rebuild this plan?" onClose={() => setRebuild(false)}>
              <p>
                The agent will re-check the changed details. This starts a new AI run, with a limit
                of 8 steps or $0.05.
              </p>
              <p>Your saved draft stays available. The new plan needs your approval.</p>
              <ErrorNotice message={action.error} />
              <div className="form-actions">
                <button
                  className="button primary"
                  disabled={action.pending}
                  onClick={async () => {
                    const result = await action.run(() => api.rebuild(id));
                    if (result.ok)
                      navigate(`/events/new?run=${encodeURIComponent(result.value.run_id)}`);
                  }}
                >
                  {action.pending ? 'Starting…' : 'Rebuild plan'}
                </button>
                <button className="button" onClick={() => setRebuild(false)}>
                  Cancel
                </button>
              </div>
            </Modal>
          </>
        )}
      </Resource>
    </>
  );
}
