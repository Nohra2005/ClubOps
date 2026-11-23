import { describe, expect, it } from 'vitest';
import { initialPreview, PREVIEW_CODE, reducePreview } from './preview';
const president = { canEdit: true, isPresident: true };
const cabinet = { canEdit: true, isPresident: false };
describe('C-35 synthetic preview boundaries', () => {
  it('never verifies a typed address or a wrong/expired code', () => {
    let state = reducePreview(
      initialPreview(),
      { type: 'address', value: 'member@example.com' },
      cabinet,
    );
    expect(state.verification).toBe('pending');
    state = reducePreview(state, { type: 'verify', code: 'wrong' }, cabinet);
    expect(state.verification).toBe('pending');
    state = reducePreview(state, { type: 'expire_verification' }, cabinet);
    expect(reducePreview(state, { type: 'verify', code: PREVIEW_CODE }, cabinet).verification).toBe(
      'expired',
    );
  });
  it('refuses real addresses and resets proof when the sample sender changes', () => {
    expect(
      reducePreview(initialPreview(), { type: 'address', value: 'person@university.edu' }, cabinet)
        .address,
    ).toBe('');
    let state = reducePreview(
      initialPreview(),
      { type: 'address', value: 'one@example.com' },
      cabinet,
    );
    state = reducePreview(state, { type: 'verify', code: PREVIEW_CODE }, cabinet);
    expect(state.verification).toBe('verified');
    state = reducePreview(state, { type: 'address', value: 'two@example.com' }, cabinet);
    expect(state.verification).toBe('pending');
  });
  it('keeps free forwarding tests separate from paid reads', () => {
    let state = reducePreview(initialPreview(), { type: 'test_forwarding' }, cabinet);
    expect(state.forwardingTest).toBe('not_tested');
    state = reducePreview(state, { type: 'address', value: 'one@example.com' }, cabinet);
    state = reducePreview(state, { type: 'verify', code: PREVIEW_CODE }, cabinet);
    state = reducePreview(state, { type: 'connection', value: 'connected' }, president);
    state = reducePreview(state, { type: 'test_forwarding' }, cabinet);
    expect(state.forwardingTest).toBe('waiting');
    expect(state.attempts).toBe(0);
    expect(state.proposed).toBe(0);
  });
  it('preserves partial success, retries only failures and never re-reads skipped/completed samples', () => {
    let state = {
      ...initialPreview(),
      connection: 'connected' as const,
      outcome: 'partial' as const,
    };
    const ids = state.messages.map((m) => m.id);
    let result = reducePreview(state, { type: 'read', ids }, cabinet);
    expect(result.messages.map((m) => m.status)).toEqual(['read', 'failed', 'skipped']);
    expect(result.proposed).toBe(1);
    result = reducePreview({ ...result, outcome: 'success' }, { type: 'read', ids }, cabinet);
    expect(result.proposed).toBe(2);
    expect(result.attempts).toBe(3);
    expect(reducePreview(result, { type: 'read', ids }, cabinet)).toEqual(result);
    state = { ...state, connection: 'connected' };
    expect(
      reducePreview({ ...state, connection: 'expired' }, { type: 'read', ids }, cabinet).attempts,
    ).toBe(0);
  });
  it('blocks role changes and every action in the read-only preview', () => {
    const state = initialPreview();
    expect(
      reducePreview(state, { type: 'connection', value: 'connected' }, cabinet).connection,
    ).toBe('disconnected');
    expect(
      reducePreview(
        state,
        { type: 'read', ids: ['sample-1'] },
        { canEdit: false, isPresident: false },
      ).attempts,
    ).toBe(0);
  });
  it('archives expired dates, rejects invalid restoration and leaves AUB-wide approval to the operator', () => {
    const action = {
      type: 'approve_card' as const,
      id: 'deadline-preview',
      expires: '2026-11-01',
      shared: false,
      addToCalendar: true,
      audience: 'cabinet' as const,
    };
    expect(
      reducePreview(initialPreview(), { ...action, shared: true }, president).cards[0].approved,
    ).toBe(false);
    expect(
      reducePreview(initialPreview(), { ...action, expires: '2026-02-30' }, president).cards[0]
        .approved,
    ).toBe(false);
    const state = reducePreview(initialPreview(), action, president);
    expect(state.cards[0].archived).toBe(true);
    expect(
      reducePreview(state, { type: 'restore', id: action.id, expires: '' }, president).cards[0]
        .archived,
    ).toBe(true);
    expect(
      reducePreview(state, { type: 'restore', id: action.id, expires: '2026-12-01' }, cabinet)
        .cards[0].archived,
    ).toBe(true);
    const restored = reducePreview(
      state,
      { type: 'restore', id: action.id, expires: '2026-12-01' },
      president,
    );
    expect(restored.cards[0].archived).toBe(false);
    expect(restored.cards[0].expires).toBe('2026-12-01');
  });
});
