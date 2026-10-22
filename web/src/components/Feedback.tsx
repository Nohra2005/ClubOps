import { useState } from 'react';
import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { useApp } from '../AppContext';
import { useAction } from '../hooks';
import { ErrorNotice, Modal } from './ui';

export function Feedback({ id }: { id: string }) { const { api, canEdit, notify } = useApp(); const action = useAction(); const [value, setValue] = useState(''); const [open, setOpen] = useState(false); const [reason, setReason] = useState(''); if (!canEdit) return null;
  async function submit(value: string) { const result = await action.run(() => api.feedback(id, value, reason)); if (result.ok) { setValue(value); setOpen(false); notify('Thanks. Your feedback was recorded.'); } }
  return <><div className="feedback"><span>Was this useful?</span><button aria-label="Helpful" aria-pressed={value === 'up'} disabled={action.pending} onClick={() => submit('up')}><ThumbsUp size={13} /></button><button aria-label="Not helpful" aria-pressed={value === 'down'} disabled={action.pending} onClick={() => setOpen(true)}><ThumbsDown size={13} /></button></div><ErrorNotice message={action.error} /><Modal open={open} title="What was wrong?" onClose={() => setOpen(false)}><form onSubmit={e => { e.preventDefault(); submit('down'); }}><label className="field"><span>Help us understand</span><textarea rows={4} value={reason} onChange={e => setReason(e.target.value)} maxLength={2000} placeholder="Wrong source, missing detail, or something else…" /></label><div className="form-actions"><button className="button primary" disabled={action.pending}>Send feedback</button><button className="button" type="button" onClick={() => setOpen(false)}>Cancel</button></div><ErrorNotice message={action.error} /></form></Modal></>;
}
