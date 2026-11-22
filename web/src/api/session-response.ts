/** Published /api/me view validation; server cookies/roles remain the authorization boundary. */
import { ApiError } from './errors';
import { roles, type Me, type Role } from './types';

function incompatible(): never {
  throw new ApiError('ClubOps could not confirm your workspace. Please try again or sign in.', 502);
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return incompatible();
  return value as Record<string, unknown>;
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : incompatible();
}

function identity(value: unknown): string {
  const result = text(value);
  return result.trim() ? result : incompatible();
}

function role(value: unknown): Role {
  if (typeof value !== 'string' || !roles.includes(value as Role)) return incompatible();
  return value as Role;
}

function flag(value: unknown): boolean {
  return typeof value === 'boolean' ? value : incompatible();
}

function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) return incompatible();
  return value;
}

export function readMe(value: unknown): Me {
  const data = object(value);
  const user = object(data.user);
  const club = object(data.club);
  const counts = object(data.counts);
  return {
    user: {
      member_id: identity(user.member_id),
      name: text(user.name),
      email: text(user.email),
      role: role(user.role),
    },
    role: role(data.role),
    club: {
      id: identity(club.id),
      name: text(club.name),
      initials: text(club.initials),
      setup_complete: flag(club.setup_complete),
    },
    counts: {
      overdue_events: count(counts.overdue_events),
      review: count(counts.review),
      reminders: count(counts.reminders),
    },
    ...(data.demo === undefined ? {} : { demo: flag(data.demo) }),
  };
}
