import { Link } from 'react-router';
import { useApp } from '../AppContext';
import { roleLabels } from '../api/types';
import { ErrorNotice } from '../components/ui';
import { useAction } from '../hooks';

export default function TermArrival() {
  const { api, me, refresh } = useApp();
  const action = useAction();
  const term = api.mode === 'demo' ? me.demo_term : undefined;
  if (!term || term.acknowledged || me.role === 'adviser') return null;
  return (
    <section className="panel term-arrival" aria-label="Your new cabinet term">
      <h2>{term.label}: your term has started</h2>
      <p>
        You are joining as {roleLabels[me.role].toLowerCase()}. Start with the work your cabinet is
        carrying forward.
      </p>
      <div className="form-actions">
        <Link className="button" to="/calendar">
          See commitments
        </Link>
        <Link className="button" to="/handover">
          Read your role reference
        </Link>
        <button
          className="button primary"
          disabled={action.pending}
          onClick={async () => {
            const result = await action.run(() =>
              api.changeTurnover({ kind: 'acknowledge', id: term.id }),
            );
            if (result.ok) refresh();
          }}
        >
          Start this term
        </button>
      </div>
      <ErrorNotice message={action.error} />
    </section>
  );
}
