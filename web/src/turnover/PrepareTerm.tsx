import { useState, type FormEvent } from 'react';
import { roleLabels, roles, type Role } from '../api/types';
import type { TurnoverInput } from './model';
const cabinetRoles = roles.filter((role) => role !== 'adviser');
const blankOfficer = (role: Role) => ({ name: '', email: '', role });

export default function PrepareTerm({
  initial,
  pending,
  save,
}: {
  initial?: TurnoverInput;
  pending: boolean;
  save: (input: TurnoverInput) => void;
}) {
  const [input, setInput] = useState<TurnoverInput>(
    () =>
      initial ?? {
        label: '',
        start_date: '',
        end_date: '',
        officers: [blankOfficer('president')],
      },
  );
  const changeOfficer = (index: number, field: 'name' | 'email' | 'role', value: string) =>
    setInput({
      ...input,
      officers: input.officers.map((officer, i) =>
        i === index ? { ...officer, [field]: value } : officer,
      ),
    });
  function submit(event: FormEvent) {
    event.preventDefault();
    save(input);
  }
  return (
    <form className="panel turnover-form" onSubmit={submit}>
      <h2>Prepare the next term</h2>
      <div className="turnover-dates">
        <label className="field">
          <span>Term name</span>
          <input
            required
            maxLength={80}
            value={input.label}
            onChange={(event) => setInput({ ...input, label: event.target.value })}
            placeholder="e.g. Spring 2027"
          />
        </label>
        <label className="field">
          <span>Starts</span>
          <input
            required
            type="date"
            value={input.start_date}
            onChange={(event) => setInput({ ...input, start_date: event.target.value })}
          />
        </label>
        <label className="field">
          <span>Ends</span>
          <input
            required
            type="date"
            min={input.start_date}
            value={input.end_date}
            onChange={(event) => setInput({ ...input, end_date: event.target.value })}
          />
        </label>
      </div>
      <h3>Incoming officers</h3>
      {input.officers.map((officer, index) => (
        <fieldset className="turnover-officer" key={index} disabled={pending}>
          <legend>Officer {index + 1}</legend>
          <label className="field">
            <span>Name</span>
            <input
              required
              maxLength={120}
              value={officer.name}
              onChange={(event) => changeOfficer(index, 'name', event.target.value)}
            />
          </label>
          <label className="field">
            <span>Google email</span>
            <input
              required
              type="email"
              maxLength={254}
              value={officer.email}
              onChange={(event) => changeOfficer(index, 'email', event.target.value)}
            />
          </label>
          <label className="field">
            <span>Role</span>
            <select
              value={officer.role}
              onChange={(event) => changeOfficer(index, 'role', event.target.value)}
            >
              {cabinetRoles.map((role) => (
                <option key={role} value={role}>
                  {roleLabels[role]}
                </option>
              ))}
            </select>
          </label>
          {input.officers.length > 1 && (
            <button
              type="button"
              className="text-button"
              onClick={() =>
                setInput({ ...input, officers: input.officers.filter((_, i) => i !== index) })
              }
            >
              Remove officer {index + 1}
            </button>
          )}
        </fieldset>
      ))}
      <div className="form-actions">
        <button
          type="button"
          className="button"
          disabled={pending || input.officers.length >= 20}
          onClick={() =>
            setInput({ ...input, officers: [...input.officers, blankOfficer('events')] })
          }
        >
          Add officer
        </button>
        <button className="button primary" disabled={pending}>
          Save and review
        </button>
      </div>
      <p className="inline-note">The current cabinet stays active until activation.</p>
    </form>
  );
}
