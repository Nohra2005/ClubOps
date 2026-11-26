import { useState } from 'react';
import { Link } from 'react-router';
import { ArrowRight, Download, Printer } from 'lucide-react';
import { useApp } from '../AppContext';
import { roleLabels, roles, type Role } from '../api/types';
import { NotSure, PageHeading, Resource, SourceChip } from '../components/ui';
import { useResource } from '../hooks';
import { downloadText } from '../lib';

export default function Handover() {
  const { api, me } = useApp();
  const [role, setRole] = useState<Role>(me.role === 'adviser' ? 'president' : me.role);
  const guide = useResource(() => api.handover(role), [api, role]);
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
      <PageHeading title="Role reference" />
      <section className="handover-reference" aria-label="Role reference sources">
        <header className="page-heading">
          <div>
            <h2>Approved knowledge</h2>
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
        <div className="turnover-reference-role">
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
            </>
          )}
        </Resource>
      </section>
    </>
  );
}
