import { useRef, useState } from 'react';
import { Link } from 'react-router';
import {
  ArrowUpRight,
  BarChart3,
  FileText,
  Link2,
  Mail,
  Plus,
  Trash2,
  Upload,
  Users,
} from 'lucide-react';
import { useApp } from '../AppContext';
import { roleLabels, roles, type Member, type Role } from '../api/types';
import {
  PageHeading,
  EmptyState,
  ErrorNotice,
  Modal,
  Resource,
  StatusBadge,
} from '../components/ui';
import { useAction, useResource } from '../hooks';
import ForwardingPanel from '../inbox/ForwardingPanel';

export default function Settings() {
  const { api, canEdit, isPresident, notify, refresh } = useApp();
  const members = useResource(() => api.cabinet(), [api]);
  const usage = useResource(() => api.usage(), [api]);
  const documents = useResource(() => api.knowledge('documents'), [api]);
  const calendar = useResource(() => api.calendar('2026-10'), [api]);
  const action = useAction();
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<Member>();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<Role>('events');
  const [pasted, setPasted] = useState('');
  const uploadRef = useRef<HTMLInputElement>(null);
  const cost = usage.value;
  return (
    <>
      <PageHeading
        title="Settings"
        description="Your cabinet, connections, source documents, and a clear view of AI spend."
      />
      {!isPresident && (
        <div className="notice warning">
          Ask your president to change members, documents or connections.
          {canEdit
            ? ' You can practice verifying your own forwarding address below.'
            : ' Your view is read only.'}
        </div>
      )}
      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Settings sections">
          <a href="#cabinet">
            <Users size={14} />
            Cabinet
          </a>
          <a href="#calendar">
            <Link2 size={14} />
            Google Calendar
          </a>
          <a href="#forwarding">
            <Mail size={14} />
            OSA email inbox
          </a>
          <a href="#documents">
            <FileText size={14} />
            Documents
          </a>
          <a href="#usage">
            <BarChart3 size={14} />
            AI cost
          </a>
        </nav>
        <div className="settings-sections">
          <section className="panel" id="transition">
            <h2>Cabinet transition</h2>
            <p>
              Prepare the outgoing questions and help the next officer find their way. This
              introduction does not replace adding members or assigning their roles.
            </p>
            <Link to="/handover" className="button">
              {isPresident ? 'Prepare cabinet handover' : 'Open role introduction'}
            </Link>
          </section>
          <section className="panel" id="cabinet">
            <div className="panel-header">
              <div>
                <h2>Your cabinet</h2>
                <p>Reminders follow the role, even when the person changes.</p>
              </div>
              {isPresident && (
                <button className="button small" onClick={() => setAdding(true)}>
                  <Plus size={12} /> Add member
                </button>
              )}
            </div>
            <Resource loading={members.loading} error={members.error} retry={members.reload}>
              <div className="cabinet-list">
                {members.value?.map((member) => (
                  <div className="cabinet-row" key={member.member_id}>
                    <span className="avatar">
                      {member.name
                        .split(' ')
                        .map((n) => n[0])
                        .slice(0, 2)
                        .join('')}
                    </span>
                    <div>
                      <strong>{member.name}</strong>
                      <span>{member.email}</span>
                    </div>
                    {isPresident ? (
                      <select
                        aria-label={`Role for ${member.name}`}
                        value={member.role}
                        disabled={action.pending}
                        onChange={async (e) => {
                          const result = await action.run(() =>
                            api.changeRole(member.member_id, e.target.value as Role),
                          );
                          if (result.ok) {
                            members.reload();
                            refresh();
                          }
                        }}
                      >
                        {roles.map((role) => (
                          <option key={role} value={role}>
                            {roleLabels[role]}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="role-label">{roleLabels[member.role]}</span>
                    )}
                    {isPresident && (
                      <button
                        className="icon-button"
                        aria-label={`Remove ${member.name}`}
                        onClick={() => setRemoving(member)}
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </Resource>
          </section>
          <section className="panel" id="calendar">
            <div className="panel-header">
              <div>
                <h2>Google Calendar</h2>
                <p>Approved plans become calendar items. ClubOps is the source of truth.</p>
              </div>
              <span className="google-calendar-icon">G</span>
            </div>
            <Resource loading={calendar.loading} error={calendar.error} retry={calendar.reload}>
              <div className="connection-row">
                <div>
                  <StatusBadge status={calendar.value?.connected ? 'current' : 'draft'} />
                  <p>
                    {calendar.value?.connected
                      ? api.mode === 'demo'
                        ? 'Demo connection enabled. No Google account is connected.'
                        : 'Your club calendar is connected.'
                      : 'Connect the shared club calendar to deliver reminders.'}
                  </p>
                </div>
                <a className="text-button" href="#forwarding">
                  Check connection setup →
                </a>
              </div>
              <Link className="text-button" to="/calendar">
                View club calendar <ArrowUpRight size={12} />
              </Link>
            </Resource>
          </section>
          <ForwardingPanel />
          <section className="panel" id="inbox">
            <div className="panel-header">
              <div>
                <h2>Manual email notes</h2>
                <p>
                  Only paste content you are authorized to share. AI runs when you click; facts
                  always enter Review first.
                </p>
              </div>
              <Mail size={20} className="section-line-icon" />
            </div>
            {isPresident && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const result = await action.run(() => api.teach(pasted));
                  if (result.ok) {
                    setPasted('');
                    refresh();
                    notify('Email text sent to Review. No fact was approved.');
                  }
                }}
              >
                <label className="field">
                  <span>Or paste an authorized email</span>
                  <textarea
                    rows={5}
                    value={pasted}
                    onChange={(e) => setPasted(e.target.value)}
                    maxLength={20000}
                    required
                    placeholder="Paste the email text here…"
                  />
                </label>
                <div className="form-actions">
                  <button
                    className="button small primary"
                    disabled={action.pending || !pasted.trim()}
                  >
                    Prepare facts for Review
                  </button>
                </div>
              </form>
            )}
          </section>
          <section className="panel" id="documents">
            <div className="panel-header">
              <div>
                <h2>Source documents</h2>
                <p>Keep the source and its year. Re-check anything that may be outdated.</p>
              </div>
              {isPresident && (
                <>
                  <input
                    className="sr-only"
                    type="file"
                    accept={api.mode === 'http' ? '.pdf,.txt,.md,.csv,.eml,.xlsx' : '.pdf,.txt'}
                    ref={uploadRef}
                    aria-label="Upload source document"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const result = await action.run(() => api.upload(file));
                      if (result.ok) {
                        documents.reload();
                        refresh();
                        notify('Document uploaded for review. Its contents are not approved yet.');
                      }
                      e.target.value = '';
                    }}
                  />
                  <button
                    className="button small"
                    disabled={action.pending}
                    onClick={() => uploadRef.current?.click()}
                  >
                    <Upload size={12} /> Upload
                  </button>
                </>
              )}
            </div>
            <Resource loading={documents.loading} error={documents.error} retry={documents.reload}>
              {documents.value?.length ? (
                documents.value.map((document) => (
                  <div className="document-row" key={document.item_id}>
                    <FileText size={17} />
                    <div>
                      <Link to={`/knowledge/${document.item_id}`}>{document.title}</Link>
                      <small>{document.year ?? 'Year not recorded'}</small>
                    </div>
                    <StatusBadge status={document.status} />
                  </div>
                ))
              ) : (
                <EmptyState
                  title="No documents yet."
                  description={
                    api.mode === 'http'
                      ? 'Upload an authorized text document or expense spreadsheet to begin.'
                      : 'Upload an authorized PDF or text file to begin.'
                  }
                />
              )}
            </Resource>
            <p className="inline-note upload-note">
              {api.mode === 'http'
                ? 'TXT, MD, CSV, EML or XLSX · up to 2 MB'
                : 'PDF or text · up to 10 MB'}
              {' · uploaded content stays unverified until reviewed.'}
            </p>
          </section>
          <section className="panel" id="usage">
            <div className="panel-header">
              <div>
                <h2>AI cost this month</h2>
                <p>Saved results stay saved. Opening a page never regenerates them.</p>
              </div>
              <BarChart3 size={20} className="section-line-icon" />
            </div>
            <Resource loading={usage.loading} error={usage.error} retry={usage.reload}>
              {cost && (
                <>
                  <div className="usage-summary">
                    <div>
                      <span>Total spend</span>
                      <strong>${cost.cost_usd.toFixed(3)}</strong>
                      <small>
                        {cost.month}
                        {api.mode === 'demo' ? ' · simulated usage' : ''}
                      </small>
                    </div>
                    <div>
                      <span>{cost.calls_label ?? 'AI calls'}</span>
                      <strong>{cost.calls}</strong>
                      <small>Explicit actions only</small>
                    </div>
                    <div>
                      <span>Most expensive feature</span>
                      <strong className="usage-feature">{cost.most_expensive_feature}</strong>
                      <small>8 steps / $0.05 per plan</small>
                    </div>
                  </div>
                  <div className="usage-breakdown">
                    {cost.by_feature.map((feature) => (
                      <div key={feature.name}>
                        <span>
                          {feature.name}
                          <small>
                            {feature.calls} {cost.calls_label ? 'steps' : 'calls'}
                          </small>
                        </span>
                        <div className="progress-track">
                          <span
                            style={{
                              width: `${(feature.cost_usd / Math.max(cost.cost_usd, 0.001)) * 100}%`,
                            }}
                          />
                        </div>
                        <strong>${feature.cost_usd.toFixed(3)}</strong>
                      </div>
                    ))}
                  </div>
                  {cost.run_metrics && (
                    <div className="usage-summary">
                      <div>
                        <span>Recorded plans completed</span>
                        <strong>{cost.run_metrics.successful_plans}</strong>
                        <small>{cost.run_metrics.failed_runs} failed runs</small>
                      </div>
                      <div>
                        <span>Cost per successful recorded plan</span>
                        <strong>
                          {cost.run_metrics.cost_per_successful_plan == null
                            ? 'Not available'
                            : `$${cost.run_metrics.cost_per_successful_plan.toFixed(3)}`}
                        </strong>
                        <small>Includes failed spend in recorded runs</small>
                      </div>
                    </div>
                  )}
                  {cost.metrics_note && <p className="inline-note">{cost.metrics_note}</p>}
                  {cost.trace_metrics_available === false && (
                    <p className="inline-note">
                      Token, latency and retry metrics have not been recorded yet.
                    </p>
                  )}
                  {cost.trace_metrics?.map((feature) => (
                    <div className="inline-note" key={feature.name}>
                      <strong>{feature.name}</strong>: {feature.tokens_in} input /{' '}
                      {feature.tokens_out} output tokens · {feature.latency_ms} ms ·{' '}
                      {feature.retries} retries · {feature.failures} failures
                    </div>
                  ))}
                </>
              )}
            </Resource>
          </section>
          {isPresident && (
            <Link className="text-button" to="/setup">
              Revisit your club setup <ArrowUpRight size={13} />
            </Link>
          )}
          <ErrorNotice message={action.error} />
        </div>
      </div>
      <Modal open={adding} title="Add a cabinet member" onClose={() => setAdding(false)}>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const result = await action.run(() => api.addMember({ name, email, role }));
            if (result.ok) {
              setAdding(false);
              setName('');
              setEmail('');
              members.reload();
              notify('Member added to the cabinet.');
            }
          }}
        >
          <div className="form-grid">
            <label className="field wide">
              <span>Name</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={120}
              />
            </label>
            <label className="field wide">
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                maxLength={254}
                placeholder={
                  api.mode === 'demo'
                    ? 'Use a sample address, e.g. member@example.com'
                    : 'Email address'
                }
              />
            </label>
            <label className="field wide">
              <span>Role</span>
              <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
                {roles.map((role) => (
                  <option key={role} value={role}>
                    {roleLabels[role]}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <ErrorNotice message={action.error} />
          <div className="form-actions">
            <button className="button primary" disabled={action.pending}>
              Add member
            </button>
            <button className="button" type="button" onClick={() => setAdding(false)}>
              Cancel
            </button>
          </div>
        </form>
      </Modal>
      <Modal open={!!removing} title="Remove this member?" onClose={() => setRemoving(undefined)}>
        <p>
          {removing?.name} will no longer hold this cabinet seat. Check who should receive their
          role's reminders.
        </p>
        <ErrorNotice message={action.error} />
        <div className="form-actions">
          <button
            className="button danger"
            disabled={action.pending}
            onClick={async () => {
              if (!removing) return;
              const result = await action.run(() => api.removeMember(removing.member_id));
              if (result.ok) {
                setRemoving(undefined);
                members.reload();
                refresh();
              }
            }}
          >
            Remove member
          </button>
          <button className="button" onClick={() => setRemoving(undefined)}>
            Cancel
          </button>
        </div>
      </Modal>
    </>
  );
}
