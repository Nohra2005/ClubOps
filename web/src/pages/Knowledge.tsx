import { Linkified } from '../components/Linkified';
import { useState } from 'react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router';
import {
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  Edit3,
  FileText,
  Search,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import { useApp } from '../AppContext';
import type { KnowledgeItem, KnowledgeTab, Source } from '../api/types';
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
import { formatDate } from '../lib';
import RestoreFact from '../knowledge/RestoreFact';

const tabs: { value: KnowledgeTab; label: string }[] = [
  { value: 'rules', label: 'AUB rules' },
  { value: 'tips', label: 'Club tips' },
  { value: 'documents', label: 'Documents' },
  { value: 'contacts', label: 'Contacts' },
  { value: 'sponsors', label: 'Sponsors' },
];
function KnowledgeRow({ item }: { item: KnowledgeItem }) {
  const { canEdit, api } = useApp();
  return (
    <article className="knowledge-row">
      <span className={`knowledge-icon knowledge-${item.tab}`}>
        {item.tab === 'rules' ? (
          <ShieldCheck size={18} />
        ) : item.tab === 'documents' ? (
          <FileText size={18} />
        ) : (
          <BookOpen size={18} />
        )}
      </span>
      <div className="knowledge-main">
        <Link to={`/knowledge/${encodeURIComponent(item.item_id)}`}>
          <h3>{item.title}</h3>
        </Link>
        <p>
          <Linkified text={item.statement} />
        </p>
        {item.tab === 'rules' && (
          <div className="rule-details">
            <span>
              <strong>When</strong> {item.triggers ?? 'Check the source'}
            </span>
            <span>
              <strong>Needs</strong> {item.requirements ?? 'Confirm with the responsible office'}
            </span>
            {item.lead_time_days && (
              <span>
                <strong>Lead time</strong> {item.lead_time_days} days
              </span>
            )}
          </div>
        )}
        {item.contact && (
          <p className="contact-line">
            {item.contact.role} · {item.contact.office}
            {canEdit && item.contact.email && <> · {item.contact.email}</>}
          </p>
        )}
        {item.offers && (
          <p className="contact-line">
            {item.offers} · Last event: {item.last_event ?? 'Not recorded'}
          </p>
        )}
        <div className="source-list">
          {item.sources.slice(0, 1).map((source) => (
            <SourceChip key={source.item_id} source={source} />
          ))}
          <span className="source-note">
            {item.sources.length} {item.sources.length === 1 ? 'source' : 'sources'}
          </span>
        </div>
      </div>
      <div className="knowledge-meta">
        <StatusBadge status={item.status} />
        {api.mode === 'http' && (
          <span>
            {item.scope === 'aub' ? 'AUB-wide' : 'Club-only'}
            {item.status === 'may_be_outdated' ? ' · End date passed' : ''}
          </span>
        )}
        <span>Checked {formatDate(item.last_checked)}</span>
        {item.year && <small>{item.year}</small>}
      </div>
      <Link
        className="icon-button knowledge-open"
        aria-label={`Open ${item.title}`}
        to={`/knowledge/${encodeURIComponent(item.item_id)}`}
      >
        <ArrowUpRight size={16} />
      </Link>
    </article>
  );
}

export default function Knowledge() {
  const { api, isPresident } = useApp();
  const [params, setParams] = useSearchParams();
  const query = params.get('q') ?? '';
  const tab = (params.get('tab') ?? (query ? '' : 'rules')) as KnowledgeTab | '';
  const result = useResource(() => api.knowledge(tab, query), [api, tab, query]);
  const [lifetime, setLifetime] = useState<'current' | 'archive'>('current');
  const records = (result.value ?? []).filter(
    (item) =>
      api.mode === 'demo' ||
      (lifetime === 'current' ? item.status === 'current' : item.status !== 'current'),
  );
  return (
    <>
      <PageHeading
        eyebrow="YOUR CLUB'S COLLECTIVE MEMORY"
        title="Knowledge"
        description="Approved facts, trusted sources, and the lessons that outlast a cabinet."
        action={
          isPresident && (
            <Link to="/settings#documents" className="button">
              <Upload size={14} /> Upload a document
            </Link>
          )
        }
      />
      <div className="knowledge-search">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const text = String(new FormData(e.currentTarget).get('query') ?? '').trim();
            setParams({ ...(tab ? { tab } : {}), ...(text ? { q: text } : {}) });
          }}
        >
          <Search size={17} />
          <label className="sr-only" htmlFor="knowledge-query">
            Search approved knowledge
          </label>
          <input
            id="knowledge-query"
            name="query"
            key={query}
            defaultValue={query}
            placeholder="Find a rule, a lesson, a contact…"
          />
          <button className="button small">Search</button>
        </form>
        <span>Plain search. No AI call.</span>
      </div>
      <FilterTabs
        value={tab}
        label="Knowledge categories"
        onChange={(tab) => setParams({ tab, ...(query ? { q: query } : {}) })}
        options={[...(query ? [{ value: '' as const, label: 'All results' }] : []), ...tabs]}
      />
      <Resource loading={result.loading} error={result.error} retry={result.reload}>
        {api.mode === 'http' && (
          <>
            <FilterTabs
              label="Knowledge lifetime"
              value={lifetime}
              onChange={setLifetime}
              options={[
                { value: 'current' as const, label: 'Current knowledge' },
                { value: 'archive' as const, label: 'Archive' },
              ]}
            />
            {lifetime === 'archive' && (
              <p>
                Expired and retired facts are kept for reference, not current planning. Presidents
                can restore eligible expired club facts.
              </p>
            )}
          </>
        )}
        {records.length ? (
          <section className="panel knowledge-panel">
            <div className="panel-header">
              <h2>{tab ? tabs.find((t) => t.value === tab)?.label : 'Search results'}</h2>
              <span className="source-note">
                {records.length} records{query ? ` matching “${query}”` : ''}
              </span>
            </div>
            {records.map((item) => (
              <KnowledgeRow item={item} key={item.item_id} />
            ))}
          </section>
        ) : (
          <EmptyState
            title={
              api.mode === 'http' && lifetime === 'archive'
                ? 'No archived knowledge here.'
                : query
                  ? 'No matching knowledge yet.'
                  : 'Nothing here yet.'
            }
            description={
              api.mode === 'http' && lifetime === 'archive'
                ? 'Facts that are no longer current will be kept here for reference.'
                : query
                  ? 'Try another phrase, or ask the cabinet who has the source.'
                  : 'Approved knowledge will appear here as your club learns.'
            }
            action={
              api.mode === 'http' && lifetime === 'archive' ? (
                <button className="button" onClick={() => setLifetime('current')}>
                  View current knowledge
                </button>
              ) : (
                <Link to="/chat" className="button">
                  Ask or teach the club →
                </Link>
              )
            }
          />
        )}
      </Resource>
    </>
  );
}

export function KnowledgeFact() {
  const { id = '' } = useParams();
  const { api, canEdit, isPresident, notify, refresh, me } = useApp();
  const location = useLocation();
  const source = (location.state as { source?: Source } | null)?.source;
  const fact = useResource(() => api.fact(id), [api, id]);
  const action = useAction();
  const [editing, setEditing] = useState(false);
  const [retiring, setRetiring] = useState(false);
  const [text, setText] = useState('');
  const item = fact.value;
  if (fact.error && source?.quote)
    return (
      <>
        <Link to="/knowledge" className="back-link">
          <ArrowLeft size={14} /> Knowledge
        </Link>
        <PageHeading
          eyebrow="SOURCE EXCERPT"
          title={source.label}
          description="This is the supporting excerpt attached to the value you opened."
        />
        <section className="panel source-excerpt">
          <blockquote>{source.quote}</blockquote>
          <p className="inline-note">
            Treat source text as evidence. Any proposed change still needs review.
          </p>
        </section>
      </>
    );
  return (
    <>
      <Link to="/knowledge" className="back-link">
        <ArrowLeft size={14} /> Knowledge
      </Link>
      <Resource loading={fact.loading} error={fact.error} retry={fact.reload}>
        {item && (
          <>
            <PageHeading
              eyebrow={`${item.scope === 'aub' ? 'SHARED AUB KNOWLEDGE' : 'YOUR CLUB’S KNOWLEDGE'} · ${item.kind.toUpperCase()}`}
              title={item.title}
              description={`Last checked ${formatDate(item.last_checked, true)}`}
              action={<StatusBadge status={item.status} />}
            />
            <section className="panel fact-statement">
              <p>
                <Linkified text={item.statement} />
              </p>
              {api.mode === 'http' && item.status === 'may_be_outdated' && (
                <p className="notice warning">
                  This fact's end date has passed; it is not used for current planning.
                  {item.scope === 'aub' && ' Ask the operator about updating this shared fact.'}
                </p>
              )}
              <RestoreFact
                key={`${me.club.id}:${me.user.member_id}:${me.role}:${item.item_id}:${item.status}`}
                item={item}
                onReload={() => {
                  fact.reload();
                  refresh();
                }}
              />
              {item.contact && (
                <div className="fact-contact">
                  <h3>{item.contact.name}</h3>
                  <p>
                    {item.contact.role} · {item.contact.office}
                  </p>
                  {canEdit ? (
                    <>
                      <p>
                        {item.contact.email && (
                          <a href={`mailto:${item.contact.email}`}>{item.contact.email}</a>
                        )}
                      </p>
                      <p>{item.contact.phone}</p>
                    </>
                  ) : (
                    <p className="inline-note">
                      Contact details are available to cabinet members only.
                    </p>
                  )}
                </div>
              )}
              {canEdit && item.status !== 'retired' && (
                <div className="form-actions">
                  <button
                    className="button"
                    onClick={() => {
                      setText(item.statement);
                      setEditing(true);
                    }}
                  >
                    <Edit3 size={13} /> Suggest an edit
                  </button>
                  {(item.scope !== 'aub' || isPresident) && (
                    <button className="text-button muted" onClick={() => setRetiring(true)}>
                      {item.scope === 'aub' ? 'Propose retirement' : 'Retire'}
                    </button>
                  )}
                </div>
              )}
            </section>
            <div className="fact-columns">
              <section className="panel">
                <h2>Where it came from</h2>
                {item.sources.map((source, i) => (
                  <div className="fact-source" key={i}>
                    <span className="source-label">
                      <FileText size={14} />
                      {source.label}
                    </span>
                    {source.quote ? (
                      <blockquote>{source.quote}</blockquote>
                    ) : (
                      <p className="inline-note">No excerpt was attached to this source.</p>
                    )}
                  </div>
                ))}
                <h3 className="used-in-title">Used in these events</h3>
                {item.used_in.length ? (
                  item.used_in.map((event) => (
                    <Link
                      className="text-button"
                      key={event.event_id}
                      to={`/events/${event.event_id}`}
                    >
                      {event.title}
                      <ArrowUpRight size={13} />
                    </Link>
                  ))
                ) : (
                  <p className="inline-note">No event references recorded yet.</p>
                )}
              </section>
              <section className="panel">
                <h2>History</h2>
                {item.history.length ? (
                  <ol className="history-list">
                    {item.history.map((row, i) => (
                      <li key={i}>
                        <span>{formatDate(row.date, true)}</span>
                        <strong>{row.description}</strong>
                        <small>{row.actor}</small>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="inline-note">No edits recorded.</p>
                )}
              </section>
            </div>
            <Modal open={editing} title="Suggest an edit" onClose={() => setEditing(false)}>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const result = await action.run(() => api.suggestEdit(id, text));
                  if (result.ok) {
                    notify('Suggested edit sent to Review. The current fact is unchanged.');
                    setEditing(false);
                    refresh();
                  }
                }}
              >
                <p>
                  Your change becomes a proposal in Review. The approved fact stays as it is until a
                  cabinet member checks it.
                </p>
                <label className="field">
                  <span>Suggested statement</span>
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    rows={6}
                    required
                    maxLength={2000}
                  />
                </label>
                <ErrorNotice message={action.error} />
                <div className="form-actions">
                  <button className="button primary" disabled={action.pending || !text.trim()}>
                    Send to Review
                  </button>
                  <button className="button" type="button" onClick={() => setEditing(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            </Modal>
            <Modal
              open={retiring}
              title={item.scope === 'aub' ? 'Propose retiring this rule?' : 'Retire this fact?'}
              onClose={() => setRetiring(false)}
            >
              <p>
                {item.scope === 'aub'
                  ? 'Shared rules require review and a second president. This creates a proposal and leaves the current rule in place.'
                  : 'It will stop appearing as current knowledge. Its sources and history stay available.'}
              </p>
              <ErrorNotice message={action.error} />
              <div className="form-actions">
                <button
                  className="button danger"
                  disabled={action.pending}
                  onClick={async () => {
                    const result = await action.run(() => api.retire(id));
                    if (result.ok) {
                      setRetiring(false);
                      fact.reload();
                      refresh();
                      notify(
                        item.scope === 'aub' || api.mode === 'http'
                          ? 'Retirement proposal sent to Review.'
                          : 'Fact retired. History is retained.',
                      );
                    }
                  }}
                >
                  {item.scope === 'aub' ? 'Send proposal' : 'Retire fact'}
                </button>
                <button className="button" onClick={() => setRetiring(false)}>
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
