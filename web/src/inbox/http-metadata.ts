/** Read-only projections of #95's documented Inbox arrays; no body or paid-read payload. */
import { ApiError } from '../api/errors';

export interface WaitingEmail {
  id: string;
  subject: string;
  date: string | null;
  forwarded_by: string | null;
}

export interface SkippedEmail {
  id: string;
  subject: string;
  reason: string;
  why: string;
}

function incompatible(): never {
  throw new ApiError(
    'Inbox metadata could not be understood. No email was read. Try refreshing.',
    502,
  );
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : incompatible();
}

function descriptiveText(value: unknown): string | null {
  // Dates and forwarder labels are descriptive only; absent/null means unavailable.
  return value === undefined || value === null ? null : text(value);
}

function rows(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return incompatible();
  const seen = new Set<string>();
  return value.map((row: unknown) => {
    if (!row || typeof row !== 'object' || Array.isArray(row)) return incompatible();
    const fields = row as Record<string, unknown>;
    const id = text(fields.id);
    if (!id.trim() || seen.has(id)) return incompatible();
    seen.add(id);
    return fields;
  });
}

export function readWaitingEmail(value: unknown): WaitingEmail[] {
  return rows(value).map((row) => ({
    id: text(row.id),
    subject: text(row.subject),
    date: descriptiveText(row.date),
    forwarded_by: descriptiveText(row.forwarded_by),
  }));
}

export function readSkippedEmail(value: unknown): SkippedEmail[] {
  return rows(value).map((row) => ({
    id: text(row.id),
    subject: text(row.subject),
    reason: text(row.reason),
    why: text(row.why),
  }));
}
