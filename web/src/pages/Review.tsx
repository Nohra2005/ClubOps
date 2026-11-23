import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Check, CheckCheck, FileText, GitMerge, Scale, ShieldCheck, Upload, X } from 'lucide-react';
import { useApp } from '../AppContext';
import type { ReviewCard, ReviewDecision, ReviewFilter, Source } from '../api/types';
import { canBatchApprove, canReview, isShared, reviewGroups } from '../api/review-policy';
import {
  PageHeading,
  EmptyState,
  ErrorNotice,
  FilterTabs,
  Modal,
  Resource,
  SourceChip,
  StatusBadge,
} from '../components/ui';
import { useAction, useResource } from '../hooks';
import CardLifecyclePreview from '../inbox/CardLifecyclePreview';

const authority = { official_document: 3, office_email: 2, stated_by_president: 1 };
function ReviewSource({ source }: { source: Source }) {
  return (
    <>
      {source.quote ? (
        <blockquote>{source.quote}</blockquote>
      ) : (
        <p className="inline-note">
          No source quote supplied. Check the original source before approving.
        </p>
      )}
      <SourceChip source={source} />
    </>
  );
}
function ReviewItem({
  card,
  reload,
  highlighted,
  scopeChanged,
}: {
  card: ReviewCard;
  reload: () => void;
  highlighted: boolean;
  scopeChanged: (id: string, changed: boolean) => void;
}) {
  const { api, canEdit, isPresident, notify } = useApp();
  const action = useAction();
  const ref = useRef<HTMLElement>(null);
  const openedAt = useRef('');
  const [dialog, setDialog] = useState<'edit' | 'reject' | 'both' | null>(null);
  const [text, setText] = useState(card.statement);
  const [reason, setReason] = useState('');
  const [shared, setShared] = useState(isShared(card));
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting) && !openedAt.current)
        openedAt.current = new Date().toISOString();
    });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  const scopeChoice = ['fact', 'merge', 'disagreement', 'rule'].includes(card.type);
  async function decide(decision: string) {
    const payload: ReviewDecision = {
      decision,
      opened_at: openedAt.current || new Date().toISOString(),
      decided_at: new Date().toISOString(),
      ...(dialog === 'edit' ? { edited_text: text } : {}),
      ...(reason.trim() ? { reason } : {}),
      ...(scopeChoice && isPresident ? { shared } : {}),
    };
    const result = await action.run(() => api.decide(card.id, payload));
    if (result.ok) {
      setDialog(null);
      notify(
        result.value.status === 'waiting_second_president'
          ? 'Waiting for a second president. This rule is not approved yet.'
          : decision === 'reject'
            ? 'Proposal rejected.'
            : 'Review decision saved.',
      );
      reload();
    }
  }
  const Icon =
    card.type === 'rule'
      ? ShieldCheck
      : card.type === 'disagreement'
        ? Scale
        : card.type === 'merge'
          ? GitMerge
          : card.type === 'document'
            ? FileText
            : CheckCheck;
  const canDecide = canReview(card, canEdit, isPresident);
  const strongerA =
    authority[card.source.authority ?? 'stated_by_president'] >
    authority[card.alternative?.source.authority ?? 'stated_by_president'];
  return (
    <article className={`review-card${highlighted ? ' highlighted' : ''}`} ref={ref} id={card.id}>
      <div className="review-card-heading">
        <span className={`review-icon review-${card.type}`}>
          <Icon size={18} />
        </span>
        <div>
          <span className="tiny-label">
            {card.type === 'rule' ? 'AUB-WIDE RULE' : card.kind.toUpperCase()}
          </span>
          <h3>{card.title}</h3>
          {isShared(card) && <span className="tiny-label">Shared with all AUB clubs</span>}
        </div>
        <StatusBadge status={card.status} />
      </div>
      {(card.warning || card.outdated) && (
        <section className="notice warning" aria-label="Source warnings">
          <div>
            {card.warning && <p>{card.warning}</p>}
            {card.outdated && <p>This source may be outdated. Check the current version first.</p>}
            <p>Review this proposal individually. It is excluded from batch approval.</p>
          </div>
        </section>
      )}
      {card.alternative ? (
        <div className="review-comparison">
          <div>
            <div className="comparison-heading">
              {card.type === 'merge' ? 'Proposed fact' : 'Version A'}
              {card.type === 'disagreement' && strongerA && <span>Stronger source</span>}
            </div>
            <p>{card.statement}</p>
            <ReviewSource source={card.source} />
          </div>
          <div>
            <div className="comparison-heading">
              {card.type === 'merge' ? 'Already in Knowledge' : 'Version B'}
              {card.type === 'disagreement' &&
                !strongerA &&
                card.alternative.source.authority !== card.source.authority && (
                  <span>Stronger source</span>
                )}
            </div>
            <p>{card.alternative.statement}</p>
            <ReviewSource source={card.alternative.source} />
          </div>
        </div>
      ) : (
        <>
          <p className="review-statement">{card.statement}</p>
          <ReviewSource source={card.source} />
        </>
      )}
      {isShared(card) && (
        <p className="rule-note">
          <ShieldCheck size={13} /> Only a president can approve knowledge shared with all AUB
          clubs.
        </p>
      )}
      {scopeChoice && canDecide && isPresident && (
        <label className="field">
          <span>Knowledge sharing</span>
          <span>
            <input
              type="checkbox"
              role="switch"
              checked={shared}
              disabled={action.pending}
              onChange={(event) => {
                setShared(event.target.checked);
                scopeChanged(card.id, event.target.checked !== isShared(card));
              }}
              aria-label="Share with all AUB clubs"
            />{' '}
            Share with all AUB clubs
          </span>
          <span className="inline-note">
            {shared
              ? 'Use for sourced knowledge that applies to every club.'
              : 'Keep this knowledge in your club.'}{' '}
            The choice is saved only when you confirm a decision. Existing shared knowledge stays
            shared.
          </span>
        </label>
      )}
      {card.type === 'plan' ? (
        <div className="review-actions">
          <Link
            className="button small primary"
            to={`/events/${encodeURIComponent(card.event_id!)}`}
          >
            Open the plan →
          </Link>
          <span className="inline-note">Review and approve from the event page.</span>
        </div>
      ) : card.status === 'waiting_second_president' ? (
        <p className="inline-note">
          Your confirmation is recorded. The rule stays unconfirmed until the second president
          responds.
        </p>
      ) : canDecide ? (
        <div className="review-actions">
          {card.type === 'disagreement' ? (
            <>
              <button
                className="button small primary"
                disabled={action.pending}
                onClick={() => decide('keep_a')}
              >
                Keep A
              </button>
              <button
                className="button small"
                disabled={action.pending}
                onClick={() => decide('keep_b')}
              >
                Keep B
              </button>
              <button
                className="button small"
                disabled={action.pending}
                onClick={() => setDialog('both')}
              >
                Both are true
              </button>
            </>
          ) : card.type === 'merge' ? (
            <>
              <button
                className="button small primary"
                disabled={action.pending}
                onClick={() => decide('merge')}
              >
                <GitMerge size={12} /> {card.op === 'update' ? 'Replace old' : 'Merge'}
              </button>
              <button
                className="button small"
                disabled={action.pending}
                onClick={() => decide('keep_both')}
              >
                {card.op === 'update' ? 'Add as new rule' : 'Keep both'}
              </button>
            </>
          ) : card.type === 'document' ? (
            <>
              <input
                type="file"
                accept=".pdf,.txt"
                aria-label="Upload replacement document"
                ref={file}
                className="sr-only"
                onChange={async (e) => {
                  const upload = e.target.files?.[0];
                  if (!upload) return;
                  const result = await action.run(() => api.upload(upload));
                  if (result.ok) {
                    notify('New version uploaded for verification.');
                    reload();
                  }
                }}
              />
              {isPresident && (
                <button
                  className="button small primary"
                  disabled={action.pending}
                  onClick={() => file.current?.click()}
                >
                  <Upload size={12} /> Upload new version
                </button>
              )}
              <button
                className="button small"
                disabled={action.pending}
                onClick={() => decide('still_valid')}
              >
                Still valid
              </button>
            </>
          ) : (
            <>
              <button
                className="button small primary"
                disabled={action.pending}
                onClick={() => decide('approve')}
              >
                <Check size={12} />
                {action.pending ? 'Saving…' : 'Approve'}
              </button>
              <button
                className="button small"
                disabled={action.pending}
                onClick={() => setDialog('edit')}
              >
                Edit then approve
              </button>
              <button
                className="text-button muted"
                disabled={action.pending}
                onClick={() => setDialog('reject')}
              >
                <X size={12} /> Reject
              </button>
            </>
          )}
        </div>
      ) : !isPresident && (isShared(card) || card.type === 'rule') && canEdit ? (
        <p className="inline-note">A president needs to review this shared knowledge.</p>
      ) : null}
      <ErrorNotice message={action.error} />
      <Modal
        open={dialog !== null}
        title={
          dialog === 'edit'
            ? 'Edit before approving'
            : dialog === 'both'
              ? 'When are both versions true?'
              : 'Reject this proposal?'
        }
        onClose={() => setDialog(null)}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            decide(dialog === 'reject' ? 'reject' : dialog === 'both' ? 'both' : 'approve');
          }}
        >
          {dialog === 'edit' ? (
            <label className="field">
              <span>Proposed statement</span>
              <textarea
                rows={5}
                value={text}
                onChange={(e) => setText(e.target.value)}
                required
                maxLength={2000}
              />
            </label>
          ) : (
            <label className="field">
              <span>
                {dialog === 'both' ? 'Explain the context for each version' : 'Reason (optional)'}
              </span>
              <textarea
                rows={4}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required={dialog === 'both'}
                maxLength={2000}
              />
            </label>
          )}
          <div className="form-actions">
            <button
              className="button primary"
              disabled={action.pending || (dialog === 'both' && !reason.trim())}
            >
              {action.pending
                ? 'Saving…'
                : dialog === 'reject'
                  ? 'Reject proposal'
                  : 'Confirm decision'}
            </button>
            <button className="button" type="button" onClick={() => setDialog(null)}>
              Cancel
            </button>
          </div>
          <ErrorNotice message={action.error} />
        </form>
      </Modal>
    </article>
  );
}

export default function Review() {
  const { api, canEdit, refresh, notify } = useApp();
  const [search, setSearch] = useSearchParams();
  const filter = (search.get('filter') ?? 'all') as ReviewFilter;
  const review = useResource(() => api.review(filter), [api, filter]);
  const batch = useAction();
  const [scopeDrafts, setScopeDrafts] = useState<Set<string>>(new Set());
  const batchEligible = (card: ReviewCard) => canBatchApprove(card) && !scopeDrafts.has(card.id);
  const scopeChanged = (id: string, changed: boolean) =>
    setScopeDrafts((previous) => {
      const next = new Set(previous);
      if (changed) next.add(id);
      else next.delete(id);
      return next;
    });
  const groupOpenedAt = useRef(new Date().toISOString());
  const groups = reviewGroups(review.value ?? []);
  const reload = () => {
    review.reload();
    refresh();
  };
  useEffect(() => {
    if (review.value && search.get('item'))
      document.getElementById(search.get('item')!)?.scrollIntoView({ block: 'center' });
  }, [review.value, search]);
  async function approveGroup(cards: ReviewCard[]) {
    const eligible = cards.filter(batchEligible);
    const result = await batch.run(async () => {
      let count = 0;
      try {
        for (const card of eligible) {
          await api.decide(card.id, {
            decision: 'approve',
            opened_at: groupOpenedAt.current,
            decided_at: new Date().toISOString(),
          });
          count++;
        }
        return count;
      } finally {
        reload();
      }
    });
    if (result.ok)
      notify(`${result.value} facts approved. Only unchanged, unflagged club facts were included.`);
  }
  return (
    <>
      <PageHeading
        eyebrow="A PERSON CHECKS IT FIRST"
        title="Review"
        description="New knowledge, changed rules, and plans waiting for your cabinet's judgment."
        action={
          <span className="review-total">
            <CheckCheck size={16} />
            {review.value?.length ?? '…'} waiting
          </span>
        }
      />
      <div className="review-intro">
        <ShieldCheck size={20} />
        <div>
          <strong>Your club's memory has a front door.</strong>
          <p>
            Check the source. Make the call. Nothing here becomes a fact until a cabinet member
            approves it. A president reviews knowledge shared with all AUB clubs.
          </p>
        </div>
      </div>
      <CardLifecyclePreview />
      <FilterTabs
        value={filter}
        onChange={(filter) => setSearch({ filter })}
        label="Review filters"
        options={[
          { value: 'all', label: 'All' },
          { value: 'facts', label: 'New facts' },
          { value: 'disagreements', label: 'Disagreements' },
          { value: 'documents', label: 'Old documents' },
          { value: 'plans', label: 'Plans' },
        ]}
      />
      <ErrorNotice message={batch.error} />
      <Resource loading={review.loading} error={review.error} retry={review.reload}>
        {groups.length === 0 ? (
          <EmptyState
            title="Nothing to review."
            description="You're all caught up. New lessons and proposed changes will appear here."
          />
        ) : (
          groups.map(({ key, title, cards }) => (
            <section className="review-group" key={key}>
              <div className="group-heading">
                <h2>
                  {title}
                  <span>
                    {cards.length} {cards.length === 1 ? 'item' : 'items'}
                  </span>
                </h2>
                {canEdit && cards.some(batchEligible) && (
                  <button
                    className="text-button"
                    disabled={batch.pending}
                    onClick={() => approveGroup(cards)}
                  >
                    <CheckCheck size={13} /> Approve all facts
                  </button>
                )}
              </div>
              {cards.map((card) => (
                <ReviewItem
                  key={card.id}
                  card={card}
                  highlighted={search.get('item') === card.id}
                  scopeChanged={scopeChanged}
                  reload={reload}
                />
              ))}
            </section>
          ))
        )}
      </Resource>
    </>
  );
}
