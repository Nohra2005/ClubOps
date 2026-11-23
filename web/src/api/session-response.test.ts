import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from './client';
import { roles, type Me } from './types';
import { readMe } from './session-response';

const session = (): Me => ({
  user: {
    member_id: 'synthetic-member',
    name: 'Synthetic President',
    email: 'president@example.com',
    role: 'president',
  },
  role: 'president',
  club: { id: 'synthetic-club', name: 'Synthetic Club', initials: 'SC', setup_complete: false },
  counts: { overdue_events: 0, review: 1, reminders: 0 },
});

describe('HTTP workspace session view', () => {
  it('rejects an unknown role before it can enter frontend permission checks', async () => {
    const transport = vi
      .fn()
      .mockResolvedValue({ ...session(), role: 'PRIVATE_UNKNOWN_ROLE_CANARY' });
    await expect(new ApiClient(transport, 'http').me()).rejects.toMatchObject({ status: 502 });
    expect(transport.mock.calls).toEqual([['/me', undefined]]);
  });

  it.each(roles)(
    'preserves the published %s role and an incomplete setup without inventing defaults',
    async (role) => {
      const view = { ...session(), role };
      const transport = vi.fn().mockResolvedValue(view);
      await expect(new ApiClient(transport, 'http').me()).resolves.toEqual(view);
    },
  );

  it.each([
    null,
    { data: session() },
    { ...session(), user: null },
    { ...session(), club: [] },
    { ...session(), counts: null },
    { ...session(), user: { ...session().user, member_id: '' } },
    { ...session(), user: { ...session().user, name: { PRIVATE_SOURCE_CANARY: 'synthetic' } } },
    { ...session(), user: { ...session().user, role: 'member' } },
    { ...session(), club: { ...session().club, id: ' ' } },
    { ...session(), club: { ...session().club, setup_complete: 'false' } },
    { ...session(), demo: 'true' },
  ])('rejects malformed workspace data without a successful partial session (%j)', (value) => {
    expect(() => readMe(value)).toThrow('ClubOps could not confirm your workspace.');
  });

  it.each([-1, 0.5, '1', null, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1])(
    'rejects invalid badge counts without coercion (%s)',
    (review) => {
      expect(() => readMe({ ...session(), counts: { ...session().counts, review } })).toThrow();
    },
  );

  it('projects only the view fields and preserves valid independent role fields', () => {
    const value = session();
    value.role = 'adviser';
    // The published view has no equality constraint between member and active roles.
    expect(
      readMe({
        ...value,
        credential: 'PRIVATE_CREDENTIAL_CANARY',
        user: { ...value.user, private: 'canary' },
      }),
    ).toEqual(value);
    expect(readMe({ ...value, demo: false }).demo).toBe(false);
  });

  it('does not echo malformed identity data in error messages or make another request', async () => {
    const transport = vi.fn().mockResolvedValue({ ...session(), role: 'PRIVATE_ROLE_CANARY' });
    try {
      await new ApiClient(transport, 'http').me();
      expect.fail('Malformed session should reject');
    } catch (error) {
      expect(error).toMatchObject({ status: 502 });
      expect((error as Error).message).not.toContain('PRIVATE_ROLE_CANARY');
    }
    expect(transport.mock.calls).toEqual([['/me', undefined]]);
  });
});
