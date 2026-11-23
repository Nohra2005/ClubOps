import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { useApp } from '../AppContext';
import { storage } from '../api';
import {
  checkStarterFile,
  checkStarterUpload,
  readStarter,
  saveStarter,
  starterKey,
  starterSteps,
  starterCabinetCount,
  type StarterStep,
} from '../api/starter-progress';
import { useAction, useResource } from '../hooks';
import { ErrorNotice, Resource } from './ui';

function StarterUpload({
  kind,
  title,
  complete,
  accepted,
}: {
  kind: 'rules' | 'proposal';
  title: string;
  complete: boolean;
  accepted: () => void;
}) {
  const { api, refresh } = useApp();
  const [file, setFile] = useState<File>();
  const action = useAction();
  return (
    <li className="starter-step">
      <h3>{title}</h3>
      {complete ? (
        <p className="starter-status">Upload accepted here · contents still need Review.</p>
      ) : (
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (!file) return;
            const result = await action.run(async () => {
              checkStarterFile(file);
              const document = await api.upload(file);
              checkStarterUpload(document);
            });
            if (result.ok) {
              accepted();
              setFile(undefined);
              refresh();
            }
          }}
        >
          <label className="field">
            <span>
              {kind === 'rules' ? 'Club rules or constitution file' : 'Past proposal file'}
            </span>
            <input
              type="file"
              accept=".pdf,.txt,.md,.csv,.eml,.xlsx"
              disabled={action.pending}
              onChange={(event) => {
                setFile(event.target.files?.[0]);
                action.clearError();
              }}
            />
          </label>
          <p className="inline-note">
            TXT, MD, CSV, EML or XLSX · nonempty, up to 2 MB. Export a text version of a PDF first.
          </p>
          <button className="button small" type="submit" disabled={!file || action.pending}>
            {action.pending
              ? 'Uploading…'
              : kind === 'rules'
                ? 'Upload club rules for Review'
                : 'Upload past proposal for Review'}
          </button>
          <ErrorNotice message={action.error} />
        </form>
      )}
    </li>
  );
}

function Checklist() {
  const { api, me } = useApp();
  const key = starterKey(api.mode, me.club.id, me.user.member_id);
  const [progress, setProgress] = useState(() => readStarter(storage, key));
  const current = useRef(progress);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  const members = useResource(async () => starterCabinetCount(await api.cabinet()), [api]);
  const mark = (step: StarterStep, value: boolean) => {
    if (!active.current) return;
    current.current = { ...current.current, [step]: value };
    saveStarter(storage, key, current.current);
    setProgress(current.current);
  };
  const count = starterSteps.filter((step) => progress[step]).length;
  return (
    <section className="panel starter-checklist" aria-labelledby="starter-heading">
      <h2 id="starter-heading">Your club's starter checklist</h2>
      <p>
        ClubOps starts with shared AUB know-how and learns your club as it is used. Add only
        authorized sources; no chat history is required.
      </p>
      <p className="starter-status" aria-live="polite">
        {count} of 4 starter steps recorded on this browser
      </p>
      <p className="inline-note">
        These ticks are private browser-local progress for your club and account. They are not
        server onboarding status or approved knowledge. Recheck them if your cabinet or sources
        change.
      </p>
      <ol className="starter-list">
        <li className="starter-step">
          <h3>1. Check your cabinet</h3>
          <Resource loading={members.loading} error={members.error} retry={members.reload}>
            <p>{members.value ?? 0} cabinet accounts are listed by the server.</p>
            <Link className="button small" to="/settings#cabinet">
              Add or check cabinet members
            </Link>
            <label className="starter-confirm">
              <input
                type="checkbox"
                checked={progress.cabinet}
                onChange={(event) => mark('cabinet', event.target.checked)}
              />{' '}
              I have checked the cabinet list
            </label>
          </Resource>
        </li>
        <StarterUpload
          kind="rules"
          title="2. Add club rules or a constitution"
          complete={progress.rules}
          accepted={() => mark('rules', true)}
        />
        <StarterUpload
          kind="proposal"
          title="3. Add one past proposal"
          complete={progress.proposal}
          accepted={() => mark('proposal', true)}
        />
        <li className="starter-step">
          <h3>4. Check usual places and partners</h3>
          <p>
            The interview asked about venues and partner organizations. Check what went to Review.
            Skipped answers do not create facts; add missing context in Chat when you know it.
          </p>
          <div className="form-actions">
            <Link className="button small" to="/review">
              Check proposed context
            </Link>
            <Link className="button small" to="/chat">
              Add missing context in Chat
            </Link>
          </div>
          <label className="starter-confirm">
            <input
              type="checkbox"
              checked={progress.context}
              onChange={(event) => mark('context', event.target.checked)}
            />{' '}
            I have checked places and partners, including anything still unknown
          </label>
        </li>
      </ol>
      <p className="inline-note">
        Selecting a file does not upload it. Each upload button may use AI to propose facts.
        Uploaded contents stay unverified until a person approves them in Review.
      </p>
      <Link className="button" to="/settings#documents">
        Manage source documents
      </Link>
    </section>
  );
}

export default function StarterChecklist() {
  const { api, me, isPresident } = useApp();
  return isPresident ? (
    <Checklist key={starterKey(api.mode, me.club.id, me.user.member_id)} />
  ) : null;
}
