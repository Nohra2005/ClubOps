import type { EventFields, Provenance } from '../api/types';
import { OriginTag, SourceChip } from './ui';

export const fieldLabels: Record<keyof EventFields, string> = {
  title: 'Event title',
  date: 'Date',
  time: 'Starting time',
  end_time: 'Ending time',
  venue: 'Place',
  audience: 'Audience',
  expected_attendance: 'Expected people',
  budget: 'Budget (USD)',
  sponsors: 'Sponsors',
  has_prizes: 'Will there be prizes?',
  catering: 'Catering',
  partner_clubs: 'Partner clubs',
  description: 'Description',
};
export function validateEventFields(fields: EventFields): string | undefined {
  if (new Date(`${fields.date}T${fields.end_time}`) <= new Date(`${fields.date}T${fields.time}`))
    return 'The ending time must be after the starting time.';
  const range = fields.expected_attendance.match(/^(\d+)(?:[-–](\d+))?$/);
  if (!range || Number(range[1]) < 1 || (range[2] && Number(range[2]) < Number(range[1])))
    return 'Enter a positive head count or an ordered range, such as 30–40.';
  if (Number(fields.budget) < 0 || !Number.isFinite(Number(fields.budget)))
    return 'Enter a budget of zero or more.';
}
export function EventFieldsForm({
  fields,
  origins = {},
  onChange,
  readOnly = false,
}: {
  fields: EventFields;
  origins?: Record<string, Provenance>;
  onChange: (fields: EventFields) => void;
  readOnly?: boolean;
}) {
  return (
    <div className="form-grid event-fields">
      {(Object.keys(fieldLabels) as (keyof EventFields)[]).map((key) => {
        const required = [
          'title',
          'date',
          'time',
          'end_time',
          'venue',
          'audience',
          'expected_attendance',
          'budget',
          'description',
        ].includes(key);
        const options =
          key === 'audience'
            ? ['Club members', 'AUB students only', 'AUB students and non-AUB students']
            : ['has_prizes', 'catering'].includes(key)
              ? ['Yes', 'No']
              : null;
        return (
          <label
            className={`field${['title', 'description'].includes(key) ? ' wide' : ''}`}
            key={key}
          >
            <span className="field-title">
              {fieldLabels[key]}
              <OriginTag origin={origins[key]?.origin ?? (fields[key] ? 'stated' : 'missing')} />
            </span>
            {key === 'description' ? (
              <textarea
                value={fields[key]}
                onChange={(e) => onChange({ ...fields, [key]: e.target.value })}
                rows={4}
                required={required}
                maxLength={2000}
                readOnly={readOnly}
              />
            ) : options ? (
              <select
                value={fields[key]}
                onChange={(e) => onChange({ ...fields, [key]: e.target.value })}
                required={required}
                disabled={readOnly}
              >
                <option value="">Not confirmed yet</option>
                {options.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            ) : (
              <input
                type={
                  key === 'date'
                    ? 'date'
                    : ['time', 'end_time'].includes(key)
                      ? 'time'
                      : key === 'budget'
                        ? 'number'
                        : 'text'
                }
                min={key === 'budget' ? '0' : undefined}
                step={key === 'budget' ? '0.01' : undefined}
                value={fields[key]}
                required={required}
                maxLength={500}
                onChange={(e) => onChange({ ...fields, [key]: e.target.value })}
                readOnly={readOnly}
              />
            )}
            {origins[key]?.source && <SourceChip source={origins[key].source!} />}
          </label>
        );
      })}
    </div>
  );
}
