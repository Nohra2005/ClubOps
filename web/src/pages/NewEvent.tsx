import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';
import { ArrowLeft, ArrowRight, Check, Sparkles } from 'lucide-react';
import { useApp } from '../AppContext';
import type { AgentRun, EventFields } from '../api/types';
import { storage } from '../api';
import { AgentSteps } from '../components/AgentSteps';
import { EventFieldsForm, validateEventFields } from '../components/EventFieldsForm';
import { PageHeading, ErrorNotice, Loading } from '../components/ui';
import { useAction } from '../hooks';

export default function NewEvent() {
  const { api, me, canEdit, refresh } = useApp();
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const descriptionKey = `clubops.unsent-event.${me.club.id}.${me.user.member_id}`;
  const [description, setDescription] = useState(() => storage.getItem(descriptionKey) ?? '');
  const [runId, setRunId] = useState(search.get('run') ?? '');
  const [run, setRun] = useState<AgentRun>();
  const [fields, setFields] = useState<EventFields>();
  const [pollRevision, setPollRevision] = useState(0);
  const [pollError, setPollError] = useState('');
  const [formError, setFormError] = useState('');
  const [checked, setChecked] = useState(false);
  const action = useAction();
  useEffect(() => {
    if (!runId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const poll = async () => {
      try {
        const next = await api.run(runId, controller.signal);
        if (!active) return;
        setRun(next);
        setPollError('');
        if (next.question?.kind === 'details' && next.details)
          setFields((current) => current ?? next.details);
        if (next.status === 'done' && next.event_id) {
          refresh();
          navigate(`/events/${encodeURIComponent(next.event_id)}`, { replace: true });
        } else if (next.status === 'working') timer = setTimeout(poll, 2000);
      } catch (error) {
        if (active)
          setPollError(error instanceof Error ? error.message : 'The plan could not be loaded.');
      }
    };
    poll();
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [api, runId, pollRevision]);
  if (!canEdit) return <Navigate to="/events" replace />;
  async function start() {
    const result = await action.run(() => api.plan(description));
    if (result.ok) {
      setRunId(result.value.run_id);
      setSearch({ run: result.value.run_id });
    }
  }
  async function answer(text: string) {
    const result = await action.run(() => api.answerRun(runId, text));
    if (result.ok) {
      setRun(result.value);
      setPollRevision((n) => n + 1);
    }
  }
  return (
    <div className="planning-page">
      <Link to="/events" className="back-link">
        <ArrowLeft size={14} /> All events
      </Link>
      <PageHeading
        title={
          run?.question?.kind === 'details'
            ? "Let's check the details."
            : runId
              ? 'A plan is taking shape.'
              : 'What are you planning?'
        }
        description={
          runId
            ? 'Your cabinet stays in control. Nothing is sent or approved here.'
            : 'Tell us the idea in your own words. We’ll help you work out the rest.'
        }
      />
      <ol className="flow-steps" aria-label="Planning progress">
        <li className={!runId ? 'current' : 'complete'}>
          <span>{runId ? <Check size={12} /> : '1'}</span>Describe it
        </li>
        <li className={run?.question?.kind === 'details' ? 'current' : runId ? 'complete' : ''}>
          <span>2</span>Check the details
        </li>
        <li className={runId && run?.question?.kind !== 'details' ? 'current' : ''}>
          <span>3</span>Build the plan
        </li>
      </ol>
      {!runId ? (
        <section className="panel describe-panel">
          <div className="describe-icon">
            <Sparkles size={22} />
          </div>
          <h2>Start with the idea.</h2>
          <p>
            A date, a place, a rough head count. Share what you know; ClubOps will ask about the
            rest.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              start();
            }}
          >
            <label className="field">
              <span className="sr-only">Describe your event</span>
              <textarea
                rows={7}
                required
                minLength={5}
                maxLength={2000}
                placeholder="A sunset 5K next Thursday, about 30 people, with coffee afterward…"
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  storage.setItem(descriptionKey, e.target.value);
                }}
              />
            </label>
            <div className="describe-bottom">
              <span>
                One click starts one run.
                <br />
                <strong>Up to 8 steps · $0.05 per run</strong>
              </span>
              <button
                className="button primary"
                disabled={action.pending || description.trim().length < 5}
              >
                {action.pending ? 'Starting…' : 'Plan it'}
                <ArrowRight size={15} />
              </button>
            </div>
            <ErrorNotice message={action.error} retry={start} />
          </form>
        </section>
      ) : (
        <>
          {!run && !pollError && <Loading />}
          {run?.question?.kind === 'details' && fields && (
            <form
              className="panel"
              onSubmit={(e) => {
                e.preventDefault();
                const error = validateEventFields(fields);
                setFormError(error ?? '');
                if (!error) answer(JSON.stringify(fields));
              }}
            >
              <div className="panel-header">
                <div>
                  <h2>A few details before we begin.</h2>
                  <p>Yellow values were guessed. Check them before confirming.</p>
                </div>
              </div>
              <EventFieldsForm fields={fields} origins={run.origins} onChange={setFields} />
              <label className="check-line">
                <input
                  type="checkbox"
                  required
                  checked={checked}
                  onChange={(e) => setChecked(e.target.checked)}
                />
                I checked the details, including any guessed values.
              </label>
              <ErrorNotice message={formError || action.error} />
              <div className="form-actions">
                <button className="button primary" disabled={action.pending || !checked}>
                  {action.pending ? 'Confirming…' : 'Confirm details'}
                  <ArrowRight size={15} />
                </button>
                <span className="inline-note">The agent can still ask about anything missing.</span>
              </div>
            </form>
          )}
          {run && (
            <AgentSteps
              run={run}
              pending={action.pending}
              error={action.error}
              onAnswer={answer}
              resumeSameRun={api.mode === 'http'}
              onContinue={async () => {
                const result = await action.run(() => api.continueRun(runId));
                if (result.ok) {
                  setRunId(result.value.run_id);
                  setSearch({ run: result.value.run_id });
                  setRun(undefined);
                  setPollRevision((n) => n + 1);
                }
              }}
              onStop={async () => {
                if (api.mode === 'http') {
                  navigate(
                    run.event_id ? `/events/${encodeURIComponent(run.event_id)}` : '/events',
                  );
                  return;
                }
                const result = await action.run(() => api.stopRun(runId));
                if (result.ok && run.event_id)
                  navigate(`/events/${encodeURIComponent(run.event_id)}`);
              }}
            />
          )}
          <ErrorNotice message={pollError} retry={() => setPollRevision((n) => n + 1)} />
        </>
      )}
    </div>
  );
}
