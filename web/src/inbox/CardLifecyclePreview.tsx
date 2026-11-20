import { useState } from 'react';
import { useApp } from '../AppContext';
import { ErrorNotice, FilterTabs } from '../components/ui';
import { PREVIEW_TODAY, type PreviewCard } from './preview';
import { PreviewNotice } from './ForwardingPanel';
import { useInboxPreview } from './useInboxPreview';

function CardForm({ card }: { card: PreviewCard }) {
  const { dispatch, isPresident } = useInboxPreview();
  const [expires, setExpires] = useState(card.expires);
  const [shared, setShared] = useState(card.shared);
  const [addToCalendar, setAddToCalendar] = useState(card.addToCalendar);
  const [audience, setAudience] = useState(card.audience);
  return (
    <article
      className="inbox-message"
      aria-label={card.archived ? 'Archived sample deadline' : 'Sample deadline card'}
    >
      <h3>{card.statement}</h3>
      <blockquote>{card.quote}</blockquote>
      <p>
        <strong>{card.shared ? 'AUB-wide' : 'Club-only'}</strong> ·{' '}
        {card.archived
          ? 'Archived; excluded from this preview’s active list'
          : card.approved
            ? 'Approved in preview only'
            : 'Pending in preview'}
      </p>
      {card.archived && (
        <p>Old expiry: {card.expires}. Previous dates are hints, not current rules.</p>
      )}
      {card.approved && !card.archived ? (
        <p>
          Expiry: {card.expires || 'None'}.{' '}
          {card.addToCalendar
            ? `Calendar choice: ${card.audience === 'cabinet' ? 'whole cabinet' : 'events role'}. No Google event was created.`
            : 'Calendar not requested.'}
        </p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            dispatch(
              card.archived
                ? { type: 'restore', id: card.id, expires }
                : { type: 'approve_card', id: card.id, expires, shared, addToCalendar, audience },
            );
          }}
        >
          <label className="field">
            <span>{card.archived ? 'New expiry for Restore' : 'Expiry date'}</span>
            <input
              type="date"
              value={expires}
              disabled={!isPresident}
              onChange={(e) => setExpires(e.target.value)}
              required={card.archived}
            />
          </label>
          {!card.archived && (
            <>
              <label className="field">
                <span>Card audience</span>
                <select
                  value={shared ? 'shared' : 'club'}
                  disabled={!isPresident}
                  onChange={(e) => setShared(e.target.value === 'shared')}
                >
                  <option value="club">Club-only</option>
                  <option value="shared">AUB-wide · operator approval required</option>
                </select>
              </label>
              <label className="starter-confirm">
                <input
                  type="checkbox"
                  checked={addToCalendar}
                  disabled={!isPresident}
                  onChange={(e) => setAddToCalendar(e.target.checked)}
                />
                <span>Add to calendar when approved (preview only)</span>
              </label>
              {addToCalendar && (
                <label className="field">
                  <span>Who is this deadline for?</span>
                  <select
                    value={audience}
                    disabled={!isPresident}
                    onChange={(e) => setAudience(e.target.value as typeof audience)}
                  >
                    <option value="cabinet">Whole cabinet</option>
                    <option value="events">Events role</option>
                  </select>
                </label>
              )}
            </>
          )}
          {isPresident && (
            <div className="form-actions">
              <button className="button small" type="submit" disabled={shared && !card.archived}>
                {card.archived ? 'Restore sample' : 'Approve sample deadline'}
              </button>
            </div>
          )}
          {shared && !card.archived && (
            <p className="notice warning">
              AUB-wide publication needs the operator workflow. It cannot be approved here.
            </p>
          )}
        </form>
      )}
    </article>
  );
}
function DemoLifecycle() {
  const { state } = useInboxPreview();
  const [view, setView] = useState<'active' | 'archive'>('active');
  const cards = state.cards.filter((card) => card.archived === (view === 'archive'));
  return (
    <section className="panel lifecycle-preview" aria-label="Deadline lifecycle preview">
      <div className="panel-header">
        <div>
          <h2>Deadline lifecycle preview</h2>
          <p>Practice expiry, calendar choices and Restore on separate sample cards.</p>
        </div>
      </div>
      <PreviewNotice />
      <p className="inline-note">
        Fixed sample date: {PREVIEW_TODAY}. These cards are separate from the Review queue below.
        Expiry/archive and new shared-publication policy await T-48; the current server approval
        rules are unchanged.
      </p>
      <FilterTabs
        value={view}
        label="Sample card views"
        onChange={setView}
        options={[
          { value: 'active', label: 'Active samples' },
          { value: 'archive', label: 'Archive samples' },
        ]}
      />
      {cards.length ? (
        cards.map((card) => <CardForm card={card} key={`${card.id}:${card.archived}`} />)
      ) : (
        <p>No sample cards in this view.</p>
      )}
      <ErrorNotice message={state.error} />
    </section>
  );
}
export default function CardLifecyclePreview() {
  const { api } = useApp();
  return api.mode === 'demo' ? <DemoLifecycle /> : null;
}
