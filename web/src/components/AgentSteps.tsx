import { useState } from 'react';
import {
  AlertCircle,
  Check,
  ChevronDown,
  Circle,
  LoaderCircle,
  MessageCircle,
  Square,
} from 'lucide-react';
import type { AgentRun } from '../api/types';
import { ErrorNotice, FallbackNotice } from './ui';

export function AgentSteps({
  run,
  pending,
  error,
  onAnswer,
  onContinue,
  onStop,
  folded = false,
  resumeSameRun = false,
}: {
  run: AgentRun;
  pending?: boolean;
  error?: string;
  onAnswer?: (answer: string) => void;
  onContinue?: () => void;
  onStop?: () => void;
  folded?: boolean;
  resumeSameRun?: boolean;
}) {
  const [answer, setAnswer] = useState('');
  return (
    <section className="agent-panel">
      <details
        open={
          !folded ||
          run.status === 'working' ||
          run.status === 'waiting_for_user' ||
          run.status === 'limit_reached' ||
          run.status === 'stopped' ||
          run.status === 'failed'
        }
      >
        <summary>
          <span className="agent-icon">
            <Circle size={15} />
          </span>
          <span>
            {run.status === 'working' ? 'Building your plan' : 'How this plan was made'}
            <small>
              {run.steps_used} of {run.step_limit} steps · ${run.cost_usd.toFixed(3)} of $
              {run.cost_limit_usd ?? 0.05}
            </small>
          </span>
          <ChevronDown size={16} />
        </summary>
        <div className="agent-content">
          <ol className="agent-steps">
            {run.steps.map((step) => (
              <li key={step.n} className={`step-${step.state}`}>
                <span>
                  {step.state === 'done' ? (
                    <Check size={13} />
                  ) : step.state === 'running' ? (
                    <LoaderCircle size={14} className="spin" />
                  ) : step.state === 'question' ? (
                    <MessageCircle size={13} />
                  ) : (
                    <Square size={11} />
                  )}
                </span>
                <div>{step.text}</div>
                {step.state === 'not_done' && <small>Not done</small>}
                {step.state === 'failed' && <small>Failed</small>}
              </li>
            ))}
          </ol>
          {run.question?.kind === 'text' && onAnswer && (
            <form
              className="agent-question"
              onSubmit={(e) => {
                e.preventDefault();
                if (answer.trim()) onAnswer(answer.trim());
              }}
            >
              <label className="field">
                <span>{run.question.text}</span>
                <input
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  required
                  maxLength={1000}
                  placeholder="Your answer"
                />
              </label>
              <button className="button primary" disabled={pending || !answer.trim()}>
                {pending ? 'Continuing…' : 'Answer and continue'}
              </button>
            </form>
          )}
          {run.status === 'limit_reached' && (
            <div className="limit-note">
              <AlertCircle size={18} />
              <div>
                <strong>This run reached its limit.</strong>
                <p>
                  {resumeSameRun
                    ? 'Your partial plan is here. Continue gives this run another allowance of up to 8 steps / $0.05. Stop here leaves the run paused.'
                    : 'Your partial plan is here. Continue starts a new run with another allowance of up to 8 steps / $0.05.'}
                </p>
                <div className="form-actions">
                  {onContinue && (
                    <button className="button primary" onClick={onContinue} disabled={pending}>
                      {resumeSameRun ? 'Continue planning' : 'Continue · new run'}
                    </button>
                  )}
                  {onStop && (
                    <button className="button" onClick={onStop} disabled={pending}>
                      Stop here
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
          {run.status === 'stopped' && (
            <p className="inline-note">Stopped here. Your partial plan is saved as a draft.</p>
          )}
          {run.status === 'failed' && (
            <ErrorNotice message="This run failed. Your partial plan has not been approved. Go back to Events to try again." />
          )}
          {run.fallback && <FallbackNotice />}
          <ErrorNotice message={error} />
        </div>
      </details>
    </section>
  );
}
