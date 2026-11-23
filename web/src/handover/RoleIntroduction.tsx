import { Link, useNavigate } from 'react-router';
import { ArrowRight, BookOpen, GraduationCap } from 'lucide-react';
import { useApp } from '../AppContext';
import { roleLabels } from '../api/types';
import { steps } from './progress';
import { useRoleLearning } from './RoleLearning';

export default function RoleIntroduction() {
  const { me, isPresident } = useApp();
  const { progress, update } = useRoleLearning();
  const navigate = useNavigate();
  const resumable = ['active', 'paused'].includes(progress.status);
  return (
    <section className="role-introduction" aria-labelledby="role-start-title">
      <span className="eyebrow">A NEW CABINET. THE CLUB’S MEMORY STAYS.</span>
      <h1 id="role-start-title">Start your role</h1>
      <p className="role-intro-lead">
        You don’t have to read everything before you begin. Find your next step, explore your club’s
        sources, and ask for help as you go.
      </p>
      <div className="role-intro-grid">
        <section className="panel">
          <GraduationCap size={28} aria-hidden="true" />
          <h2>
            {me.role === 'adviser'
              ? 'Explore the club’s reference guide'
              : `Your ${roleLabels[me.role].toLowerCase()} introduction`}
          </h2>
          <p>
            {me.role === 'adviser'
              ? 'Your access stays read only. The sourced guide and open questions are below.'
              : 'Four short stops through Events, Calendar, Knowledge and Chat. Skip, pause, or return whenever you need.'}
          </p>
          {me.role !== 'adviser' && (
            <>
              <p className="inline-note">
                {progress.status === 'complete'
                  ? 'Introduction finished. You can replay it anytime.'
                  : resumable
                    ? `Resume at step ${progress.step + 1} of ${steps.length}.`
                    : 'Optional introduction · no AI call to start'}
              </p>
              <button
                className="button primary"
                onClick={() => {
                  const index = resumable ? progress.step : 0;
                  update({ status: 'active', step: index });
                  navigate(steps[index].path);
                }}
              >
                {resumable
                  ? 'Resume walkthrough'
                  : progress.status === 'complete'
                    ? 'Replay walkthrough'
                    : 'Start walkthrough'}{' '}
                <ArrowRight size={14} />
              </button>
              {resumable && (
                <button className="text-button" onClick={() => update({ status: 'new', step: 0 })}>
                  Start again
                </button>
              )}
              <p className="inline-note">
                Saved in this browser for your current account, club and role. This is not a cabinet
                transfer or a handover sign-off.
              </p>
            </>
          )}
        </section>
        <section className="panel">
          <BookOpen size={28} aria-hidden="true" />
          <h2>Leaving something useful behind</h2>
          <p>
            Open the reference guide below. Check its sources and unanswered questions with the
            outgoing officer before teaching a new fact.
          </p>
          {me.role !== 'adviser' && (
            <Link className="button" to="/chat?prepare=1">
              Prepare an outgoing note
            </Link>
          )}
          {isPresident && (
            <p>
              <Link to="/settings#cabinet">Manage cabinet membership in Settings</Link>. Invitations
              and an automatic season change are not available yet.
            </p>
          )}
        </section>
      </div>
    </section>
  );
}
