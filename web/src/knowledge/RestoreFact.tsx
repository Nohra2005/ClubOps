import { useState } from 'react';
import { useApp } from '../AppContext';
import { ApiError } from '../api/errors';
import type { KnowledgeItem } from '../api/types';
import { validRestoreDate } from '../api/action-responses';
import { ErrorNotice, Modal } from '../components/ui';
import { useAction } from '../hooks';
import { todayInBeirut } from '../lib';

export default function RestoreFact({
  item,
  onReload,
}: {
  item: KnowledgeItem;
  onReload: () => void;
}) {
  const { api, isPresident, notify } = useApp();
  const action = useAction();
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState('');
  const [noEnd, setNoEnd] = useState(false);
  const [reloadRequired, setReloadRequired] = useState(false);
  const today = todayInBeirut();
  if (
    api.mode !== 'http' ||
    !isPresident ||
    item.scope !== 'club' ||
    item.status !== 'may_be_outdated'
  )
    return null;
  const valid = noEnd || (validRestoreDate(date) && date >= today);
  async function confirm() {
    if (!valid || reloadRequired) return;
    const result = await action.run(async () => {
      try {
        return await api.restoreFact(item.item_id, noEnd ? null : date);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status === 0 || error.status >= 500)
          setReloadRequired(true);
        throw error;
      }
    });
    if (!result.ok) return;
    setOpen(false);
    notify('Fact restored. Loading its current version.');
    onReload();
  }
  return (
    <>
      <button
        className="button"
        onClick={() => {
          action.clearError();
          setOpen(true);
        }}
      >
        Restore expired fact
      </button>
      <Modal
        open={open}
        title="Restore this expired club fact?"
        onClose={() => {
          if (!action.pending) setOpen(false);
        }}
      >
        <p>{item.statement}</p>
        <p>
          This approves a new current version of the existing club fact. Its sources and history
          stay available. Choose a new end date or explicitly remove the end date. No AI call.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            confirm();
          }}
        >
          <label className="field">
            <span>New end date</span>
            <input
              type="date"
              value={date}
              min={today}
              disabled={noEnd || action.pending}
              onChange={(event) => setDate(event.target.value)}
              required={!noEnd}
            />
          </label>
          <label className="checkbox-line">
            <input
              type="checkbox"
              checked={noEnd}
              disabled={action.pending}
              onChange={(event) => setNoEnd(event.target.checked)}
            />{' '}
            No end date
          </label>
          <ErrorNotice message={action.error} />
          {reloadRequired && (
            <p>Restore was not confirmed. Reload the fact before another attempt.</p>
          )}
          <div className="form-actions">
            <button
              className="button primary"
              disabled={action.pending || !valid || reloadRequired}
            >
              {action.pending ? 'Restoring…' : 'Confirm Restore'}
            </button>
            {reloadRequired && (
              <button
                className="button"
                type="button"
                onClick={() => {
                  setOpen(false);
                  onReload();
                }}
              >
                Reload fact
              </button>
            )}
            <button
              className="button"
              type="button"
              disabled={action.pending}
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
