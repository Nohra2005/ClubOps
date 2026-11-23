/** Narrow acknowledgements from the exact API examples published in #95/#96. */
import { ApiError } from './errors';

function object(value: unknown, message: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new ApiError(message, 502);
  return value as Record<string, unknown>;
}

export function readInboxCapture(value: unknown): { proposals: string[]; skipped: string[] } {
  const message =
    'The read result was not confirmed. Refresh Inbox and check Review before trying again.';
  const result = object(value, message);
  if (
    !Array.isArray(result.proposals) ||
    !Array.isArray(result.skipped) ||
    result.proposals.some((id) => typeof id !== 'string' || !id.trim()) ||
    result.skipped.some((reason) => typeof reason !== 'string')
  )
    throw new ApiError(message, 502);
  // The contract does not forbid repeated IDs or a mix of proposed and skipped material.
  return { proposals: [...result.proposals], skipped: [...result.skipped] };
}

export function validRestoreDate(value: unknown): value is string | null {
  if (value === null) return true;
  if (
    typeof value !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}$/.test(value) ||
    Number(value.slice(0, 4)) < 1
  )
    return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function readRestoreAcknowledgement(value: unknown, itemId: string) {
  const message = 'Restore was not confirmed. Reload the fact before trying again.';
  const result = object(value, message);
  if (result.item_id !== itemId || result.scope !== 'club' || result.status !== 'current')
    throw new ApiError(message, 502);
  // Do not render an unvalidated POST projection; reload the existing fact resource.
  return { item_id: itemId, scope: 'club' as const, status: 'current' as const };
}
