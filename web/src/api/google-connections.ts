import { ApiError } from './errors';
export type GoogleService = 'calendar' | 'gmail';
export interface GoogleConnection {
  state: 'not_set_up' | 'not_connected' | 'connected' | 'reconnect';
  source: 'app' | 'host' | null;
  can_connect: boolean;
  can_manage?: boolean;
  access_changes_waiting?: number;
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new ApiError('Connection status could not be confirmed. Refresh status.', 502);
  return value as Record<string, unknown>;
}
export function readGoogleConnection(value: unknown, service: GoogleService): GoogleConnection {
  const row = record(value);
  if (
    !['not_set_up', 'not_connected', 'connected', 'reconnect'].includes(String(row.state)) ||
    ![null, 'app', 'host'].includes(row.source as null | string) ||
    typeof row.can_connect !== 'boolean' ||
    (service === 'gmail'
      ? typeof row.can_manage !== 'boolean'
      : !Number.isSafeInteger(row.access_changes_waiting) || Number(row.access_changes_waiting) < 0)
  )
    throw new ApiError('Connection status could not be confirmed. Refresh status.', 502);
  return {
    state: row.state as GoogleConnection['state'],
    source: row.source as GoogleConnection['source'],
    can_connect: row.can_connect,
    ...(service === 'gmail'
      ? { can_manage: row.can_manage as boolean }
      : { access_changes_waiting: row.access_changes_waiting as number }),
  };
}
export function readGoogleAuthorization(value: unknown): string {
  const row = record(value);
  try {
    if (typeof row.url !== 'string') throw new Error();
    const url = new URL(row.url);
    if (
      url.protocol !== 'https:' ||
      url.hostname !== 'accounts.google.com' ||
      url.port ||
      url.username ||
      url.password ||
      !['/o/oauth2/v2/auth', '/o/oauth2/auth'].includes(url.pathname)
    )
      throw new Error();
    return url.href;
  } catch {
    throw new ApiError(
      'The Google connection address could not be confirmed. Try connecting again.',
      502,
    );
  }
}
export function readInboxFetch(value: unknown) {
  const row = record(value);
  const count = (key: string) => {
    if (!Number.isSafeInteger(row[key]) || Number(row[key]) < 0)
      throw new ApiError('Fetch result could not be confirmed. Refresh Inbox.', 502);
    return row[key] as number;
  };
  // Only these documented counts are displayed. No mail bodies or addresses are accepted as UI results.
  return {
    queued: count('queued'),
    skipped: count('skipped'),
    not_for_a_club: count('not_for_a_club'),
  };
}
