import { useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { ArrowRight, GraduationCap } from 'lucide-react';
import { useApp } from '../AppContext';
import { roleLabels } from '../api/types';
import { steps } from './progress';
import { useRoleLearning } from './RoleLearning';

export function RoleTour() {
  const { me, canEdit } = useApp();
  const { progress, update } = useRoleLearning();
  const location = useLocation();
  const navigate = useNavigate();
  const step = steps[progress.step];
  const active = progress.status === 'active';
  const onStep = location.pathname === step.path;
  useEffect(() => {
    if (!active || !onStep) return;
    const nodes = document.querySelectorAll(`a[href="${step.path}"]`);
    nodes.forEach((node) => node.classList.add('role-tour-highlight'));
    return () => nodes.forEach((node) => node.classList.remove('role-tour-highlight'));
  }, [active, onStep, step.path]);
  if (me.role === 'adviser' || !me.club.setup_complete) return null;
  if (!active) {
    if (location.pathname !== '/events' || !['new', 'paused'].includes(progress.status))
      return null;
    return (
      <section className="role-welcome" aria-label="Start your role">
        <GraduationCap size={24} aria-hidden="true" />
        <div>
          <strong>
            {progress.status === 'paused' ? 'Your introduction is waiting' : 'New to your role?'}
          </strong>
          <p>
            A short introduction for the {roleLabels[me.role].toLowerCase()}. Your club’s knowledge
            is already here.
          </p>
        </div>
        <Link className="button" to="/handover">
          {progress.status === 'paused' ? 'Resume introduction' : 'Start here'}{' '}
          <ArrowRight size={14} />
        </Link>
        <button className="text-button" onClick={() => update({ status: 'dismissed' })}>
          Dismiss
        </button>
      </section>
    );
  }
  return (
    <aside className="role-tour" aria-label="Role walkthrough">
      <span className="eyebrow">
        YOUR {roleLabels[me.role].toUpperCase()} INTRODUCTION · {progress.step + 1} OF{' '}
        {steps.length}
      </span>
      <h2>{step.title}</h2>
      <p>{step.text}</p>
      <p className="inline-note">
        Progress stays in this browser. You can pause or skip; this does not change your role.
      </p>
      {canEdit && (
        <Link
          to={`/chat?learning=1`}
          className="text-button"
          onClick={() => update({ learning: true })}
        >
          Ask about this step
        </Link>
      )}
      <div className="compact-actions">
        <button className="button" onClick={() => update({ status: 'paused' })}>
          Pause
        </button>
        {progress.step > 0 && (
          <button
            className="button"
            onClick={() => {
              update({ step: progress.step - 1 });
              navigate(steps[progress.step - 1].path);
            }}
          >
            Back
          </button>
        )}
        {!onStep ? (
          <button className="button primary" onClick={() => navigate(step.path)}>
            Open {step.target}
          </button>
        ) : (
          <>
            <button
              className="button"
              onClick={() => {
                if (progress.step === steps.length - 1) update({ status: 'complete' });
                else {
                  update({ step: progress.step + 1 });
                  navigate(steps[progress.step + 1].path);
                }
              }}
            >
              Skip this step
            </button>
            <button
              className="button primary"
              onClick={() => {
                if (progress.step === steps.length - 1) {
                  update({ status: 'complete' });
                  navigate('/handover');
                } else {
                  update({ step: progress.step + 1 });
                  navigate(steps[progress.step + 1].path);
                }
              }}
            >
              {progress.step === steps.length - 1 ? 'Finish introduction' : 'Next step'}
            </button>
          </>
        )}
      </div>
    </aside>
  );
}
