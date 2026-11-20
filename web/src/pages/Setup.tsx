import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router';
import { ArrowRight, BookOpen, Check, MessageCircle, ShieldCheck } from 'lucide-react';
import { useApp } from '../AppContext';
import { storage } from '../api';
import type { SetupStep } from '../api/types';
import { PageHeading, ErrorNotice } from '../components/ui';
import { useAction, useResource } from '../hooks';
import StarterChecklist from '../components/StarterChecklist';
import ForwardingPanel from '../inbox/ForwardingPanel';

export default function Setup() {
  const { api, me, isPresident, refresh } = useApp();
  const navigate = useNavigate();
  const rules = useResource(() => api.knowledge('rules'), [api]);
  const [step, setStep] = useState<SetupStep>();
  const [answer, setAnswer] = useState('');
  const [history, setHistory] = useState<{ question: string; answer: string }[]>([]);
  const action = useAction();
  if (!isPresident) return <Navigate to="/events" replace />;
  async function next(value?: string) {
    const result = await action.run(() => api.setup(value));
    if (result.ok) {
      if (step && value !== undefined)
        setHistory((previous) => [
          ...previous,
          { question: step.question, answer: value === '[skip]' ? 'Skipped for now' : value },
        ]);
      setStep(result.value);
      if (value !== undefined || result.value.index !== step?.index || result.value.done)
        setAnswer('');
      storage.setItem(`clubops.setup.paused.${me.club.id}`, 'no');
      if (result.value.done) refresh();
    }
  }
  const stop = () => {
    storage.setItem(`clubops.setup.paused.${me.club.id}`, 'yes');
    navigate('/events');
  };
  return (
    <div className="setup-page">
      <PageHeading
        eyebrow="YOUR CLUB, WITH A HEAD START"
        title={
          !step
            ? `Welcome, ${me.club.name}.`
            : step.done
              ? 'A good beginning.'
              : 'Make this workspace yours.'
        }
        description="Start with shared rules. Add your club's own people, places and lessons."
      />
      {!step?.done && (
        <p className="inline-note">
          Complete setup in one tab so each answer stays with its question. No chat history is
          required.
        </p>
      )}
      {!step ? (
        <section className="panel setup-welcome">
          <div className="setup-welcome-icon">
            <BookOpen size={31} />
          </div>
          <h2>Shared rules are the starting point.</h2>
          <p>
            {rules.loading ? (
              'Checking the shared rulebook…'
            ) : api.mode === 'demo' ? (
              <>{rules.value?.length ?? 0} synthetic rule examples are available in this demo.</>
            ) : rules.value?.length ? (
              <>{rules.value.length} approved shared AUB rules are available to this club.</>
            ) : (
              'No approved shared rules are available yet. Ask your president to load the sourced rulebook.'
            )}{' '}
            Setup answers never create or approve AUB rules.
          </p>
          <div className="setup-promises">
            <div>
              <ShieldCheck size={17} />
              <span>Every new fact goes to Review first.</span>
            </div>
            <div>
              <MessageCircle size={17} />
              <span>Short questions, one at a time. About ten minutes.</span>
            </div>
            <div>
              <Check size={17} />
              <span>Skip a question or stop whenever you need to.</span>
            </div>
          </div>
          <div className="form-actions">
            <button className="button primary" disabled={action.pending} onClick={() => next()}>
              {action.pending ? 'Opening setup…' : 'Start or resume club setup'}
              <ArrowRight size={14} />
            </button>
            <button className="text-button" onClick={stop}>
              Do this later
            </button>
          </div>
          <ErrorNotice message={action.error || rules.error} />
        </section>
      ) : step.done ? (
        <>
          <section className="panel setup-complete">
            <span className="setup-check">
              <Check size={28} />
            </span>
            <h2>Your club interview is complete.</h2>
            <p>
              The interview is complete. Any facts extracted from your answers are waiting in
              Review; none were approved here. Skipped or uninformative answers may produce no
              facts.
            </p>
            <p>You can add more knowledge later in Chat. Setup does not change cabinet accounts.</p>
            <div className="form-actions">
              <Link className="button primary" to="/review">
                Review what we learned <ArrowRight size={14} />
              </Link>
              <Link className="button" to="/events">
                Open Events
              </Link>
            </div>
          </section>
          <StarterChecklist />
        </>
      ) : (
        <>
          <div className="setup-progress">
            <div>
              <span>Getting to know your club</span>
              <strong>
                {step.index} of {step.total}
              </strong>
            </div>
            <div className="progress-track">
              <span style={{ width: `${((step.index - 1) / step.total) * 100}%` }} />
            </div>
          </div>
          {history.length > 0 && (
            <details className="setup-history">
              <summary>Your answers so far ({history.length})</summary>
              {history.map((row, i) => (
                <div key={i}>
                  <strong>{row.question}</strong>
                  <p>{row.answer}</p>
                </div>
              ))}
            </details>
          )}
          <section className="panel setup-question">
            <span className="assistant-avatar">c.</span>
            <h2>{step.question}</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (answer.trim()) next(answer.trim());
              }}
            >
              <label className="field">
                <span className="sr-only">Your setup answer</span>
                <textarea
                  autoFocus
                  rows={5}
                  maxLength={2000}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Tell us what you know…"
                  required
                />
              </label>
              <div className="form-actions">
                <button className="button primary" disabled={action.pending || !answer.trim()}>
                  {action.pending ? 'Saving your answer…' : 'Next question'}
                  <ArrowRight size={14} />
                </button>
                <button
                  className="text-button"
                  type="button"
                  disabled={action.pending}
                  onClick={() => next('[skip]')}
                >
                  Skip this question
                </button>
              </div>
              <ErrorNotice message={action.error} />
              {action.error && (
                <button
                  className="text-button"
                  type="button"
                  disabled={action.pending}
                  onClick={() => next()}
                >
                  Resume saved setup
                </button>
              )}
            </form>
          </section>
          <button className="text-button stop-setup" onClick={stop} disabled={action.pending}>
            Stop for now · saved progress is kept
          </button>
          <p className="inline-note">
            Next question may use AI to propose facts. Skipping or resuming does not call AI.
            Nothing runs while you type. Omit personal contact details and private links.
          </p>
        </>
      )}
      <ForwardingPanel />
    </div>
  );
}
