import { useState } from 'react';
import { Link } from 'react-router';
import { ArrowRight, Check, Download, GraduationCap, Printer } from 'lucide-react';
import { useApp } from '../AppContext';
import { roleLabels, roles, type Role } from '../api/types';
import { ErrorNotice, Modal, NotSure, Resource, SourceChip } from '../components/ui';
import { useAction, useResource } from '../hooks';
import { downloadText, formatDate } from '../lib';
import RoleIntroduction from '../handover/RoleIntroduction';

export default function Handover() {
  const { api, me, isPresident, notify } = useApp();
  const [role, setRole] = useState<Role>(me.role === 'adviser' ? 'president' : me.role);
  const guide = useResource(() => api.handover(role), [api, role]);
  const action = useAction();
  const [confirm, setConfirm] = useState(false);
  const exportGuide = () => {
    if (!guide.value) return;
    const text = [
      `${me.club.name} · ${roleLabels[role]} handover`,
      ...guide.value.sections.flatMap((section) => [
        `\n${section.title.toUpperCase()}`,
        ...section.entries.map(
          (entry) =>
            `${entry.text}\n${(entry.sources ?? [entry.source]).map((source) => `Source: ${source.label}${source.quote ? `\nExcerpt: ${source.quote}` : ''}`).join('\n')}`,
        ),
      ]),
      '\nOPEN QUESTIONS',
      ...guide.value.gaps.map(
        (gap) =>
          `${gap.topic}${gap.question ? `\n${gap.question}` : ''}\nAsk: ${gap.ask}\nLook in: ${gap.look_in}`,
      ),
    ].join('\n\n');
    downloadText(`${me.club.id}-${role}-handover.txt`, text);
  };
  return (
    <>
      <RoleIntroduction />
      {guide.value?.role === me.role && guide.value.sections[0]?.entries[0] && (
        <section className="panel role-first-fact" aria-label="A first thing to know">
          <h2>A first thing to know</h2>
          <p>{guide.value.sections[0].entries[0].text}</p>
          {(
            guide.value.sections[0].entries[0].sources ?? [
              guide.value.sections[0].entries[0].source,
            ]
          ).map((source) => (
            <SourceChip key={source.item_id} source={source} />
          ))}
          <p className="inline-note">
            Open the reference below for the rest of this role's sources and unanswered questions.
          </p>
        </section>
      )}

      <details className="handover-reference">
        <summary>Reference guide, sources and outgoing questions</summary>
        <header className="page-heading">
          <div>
            <h2>Handover</h2>
            <p>Keep the sources and open questions behind this role.</p>
          </div>
          <div className="compact-actions">
            <button className="button" onClick={exportGuide} disabled={!guide.value}>
              <Download size={13} /> Download text
            </button>
            <button className="button" onClick={() => window.print()} disabled={!guide.value}>
              <Printer size={13} /> Print / save PDF
            </button>
          </div>
        </header>
        <div className="handover-banner">
          <span className="handover-banner-icon">
            <GraduationCap size={32} />
          </span>
          <div>
            <h2>
              A cabinet changes.
              <br />
              The know-how shouldn't.
            </h2>
            <p>This guide is assembled from approved knowledge. No AI call, no extra cost.</p>
          </div>
          <label className="field">
            <span>Guide for</span>
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {roles
                .filter((r) => r !== 'adviser')
                .map((role) => (
                  <option key={role} value={role}>
                    {roleLabels[role]}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <Resource loading={guide.loading} error={guide.error} retry={guide.reload}>
          {guide.value && (
            <>
              <div className="handover-guide">
                <div>
                  {guide.value.sections.map((section, i) => (
                    <section className="panel guide-section" key={section.title}>
                      <div className="guide-section-heading">
                        <span>{String(i + 1).padStart(2, '0')}</span>
                        <h2>{section.title}</h2>
                      </div>
                      {section.entries.length ? (
                        section.entries.map((entry, j) => (
                          <div className="guide-entry" key={j}>
                            <p>{entry.text}</p>
                            {(entry.sources ?? [entry.source]).map((source) => (
                              <SourceChip key={source.item_id} source={source} />
                            ))}
                          </div>
                        ))
                      ) : (
                        <p className="inline-note">
                          No approved information recorded for this part yet.
                        </p>
                      )}
                    </section>
                  ))}
                </div>
                <aside>
                  <section className="panel guide-gaps">
                    <h2>Questions for the outgoing cabinet</h2>
                    <p>These are gaps to ask the outgoing cabinet about.</p>
                    {guide.value.gaps.map((gap) => (
                      <div key={gap.topic}>
                        <h3>{gap.topic}</h3>
                        <NotSure
                          ask={{ who: gap.ask }}
                          lookIn={gap.look_in}
                          explanation={gap.question}
                        />
                      </div>
                    ))}
                    {me.role !== 'adviser' && (
                      <Link className="button" to="/chat?prepare=1">
                        Prepare an outgoing note
                      </Link>
                    )}
                    <Link className="button" to={`/chat?role=${role}`}>
                      Ask about this role <ArrowRight size={13} />
                    </Link>
                  </section>
                </aside>
              </div>
              {guide.value.signed_off_at ? (
                <div className="signed-guide">
                  <Check size={18} />
                  <div>
                    <strong>Signed off by {guide.value.signed_off_by}</strong>
                    <p>
                      {formatDate(guide.value.signed_off_at, true)} · This version is confirmed by
                      the outgoing cabinet.
                    </p>
                  </div>
                </div>
              ) : (
                isPresident &&
                api.mode === 'demo' && (
                  <div className="handover-signoff">
                    <div>
                      <strong>Ready to pass it on?</strong>
                      <p>Check the guide and its open questions before signing off this version.</p>
                    </div>
                    <button className="button primary" onClick={() => setConfirm(true)}>
                      Sign off handover
                    </button>
                  </div>
                )
              )}
            </>
          )}
        </Resource>
        {isPresident && api.mode === 'http' && (
          <p className="inline-note">
            Handover sign-off is not available here yet. You can still read and download the sourced
            guide.
          </p>
        )}
      </details>
      <Modal open={confirm} title="Sign off this handover?" onClose={() => setConfirm(false)}>
        <p>
          You are confirming the current {roleLabels[role].toLowerCase()} guide, including its
          sources and open gaps. Changed knowledge will need a fresh sign-off.
        </p>
        <ErrorNotice message={action.error} />
        <div className="form-actions">
          <button
            className="button primary"
            disabled={action.pending}
            onClick={async () => {
              const result = await action.run(() => api.signOff(role));
              if (result.ok) {
                setConfirm(false);
                guide.reload();
                notify('This handover version is signed off.');
              }
            }}
          >
            {action.pending ? 'Signing…' : 'Confirm sign-off'}
          </button>
          <button className="button" onClick={() => setConfirm(false)}>
            Cancel
          </button>
        </div>
      </Modal>
    </>
  );
}
