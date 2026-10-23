import { useRef, useState } from 'react';
import { Link } from 'react-router';
import {
  ArrowUpRight,
  BarChart3,
  Copy,
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
import { copyText } from '../lib';

export default function Settings() {
  const { api, me, isPresident, notify, refresh } = useApp();
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
  const inbox = api.mode === 'demo' ? `${me.club.id}@forward.clubops.example` : '';
  const cost = usage.value;
  return (
    <>
      <PageHeading
        eyebrow="A WORKSPACE THAT WORKS FOR YOUR CLUB"
        title="Settings"
        description="Your cabinet, connections, source documents, and a clear view of AI spend."
      />
      {!isPresident && (
        <div className="notice warning">
          Settings are read only. Ask your president to change members, documents or connections.
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
          <a href="#inbox">
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
                {isPresident && (
                  <button
                    className="button small"
                    disabled={action.pending}
                    onClick={async () => {
                      const result = await action.run(() => api.google(!calendar.value?.connected));
                      if (result.ok) {
                        calendar.reload();
                        notify(
                          api.mode === 'demo'
                            ? 'Demo connection updated. No Google account was changed.'
                            : 'Calendar connection updated.',
                        );
                      }
                    }}
                  >
                    {calendar.value?.connected
                      ? 'Disconnect'
                      : api.mode === 'demo'
                        ? 'Enable demo connection'
                        : 'Connect Google Calendar'}
                  </button>
                )}
              </div>
              <Link className="text-button" to="/calendar">
                View club calendar <ArrowUpRight size={12} />
              </Link>
            </Resource>
          </section>
          <section className="panel" id="inbox">
            <div className="panel-header">
              <div>
                <h2>OSA email inbox</h2>
                <p>Choose what to forward. Extracted facts always enter Review first.</p>
              </div>
              <Mail size={20} className="section-line-icon" />
            </div>
            {inbox ? (
              <div className="inbox-address">
                <code>{inbox}</code>
                {isPresident && (
                  <button
                    className="icon-button"
                    aria-label="Copy forwarding address"
                    onClick={async () => {
                      const result = await action.run(() => copyText(inbox));
                      if (result.ok)
                        notify('Example address copied. This demo inbox cannot receive email.');
                    }}
                  >
                    <Copy size={13} />
                  </button>
                )}
              </div>
            ) : (
              <p className="inline-note">No forwarding inbox is connected yet.</p>
            )}
            {api.mode === 'demo' && (
              <p className="inline-note">Example address only. It cannot receive email.</p>
            )}
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
                    accept=".pdf,.txt"
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
                  description="Upload an authorized PDF or text file to begin."
                />
              )}
            </Resource>
            <p className="inline-note upload-note">
              PDF or text · up to 10 MB · uploaded content stays unverified until reviewed.
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
                      <span>AI calls</span>
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
                          <small>{feature.calls} calls</small>
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
