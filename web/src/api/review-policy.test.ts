import { describe, expect, it } from 'vitest';
import { createWorkspace } from './fixtures';
import { canBatchApprove, canReview, isShared, reviewGroups } from './review-policy';
import type { ReviewCard } from './types';

const fact = createWorkspace('running-club').review.find((card) => card.type === 'fact')!;

describe('review scope and individual approval boundaries', () => {
  it('does not batch a shared fact disguised as an ordinary fact', () => {
    expect(canBatchApprove(fact)).toBe(true);
    for (const update of [
      { shared: true },
      { type: 'rule' },
      { type: 'disagreement' },
      { type: 'merge' },
      { warning: 'Check the source' },
      { outdated: true },
      { status: 'approved' },
    ] satisfies Partial<ReviewCard>[])
      expect(canBatchApprove({ ...fact, ...update })).toBe(false);
  });

  it('requires a president for every shared card type, including disagreements and merges', () => {
    for (const type of ['fact', 'merge', 'disagreement', 'rule'] as const) {
      const shared = { ...fact, type, shared: true };
      expect(canReview(shared, true, false)).toBe(false);
      expect(canReview(shared, true, true)).toBe(true);
      expect(canReview(shared, false, true)).toBe(false);
      expect(canReview({ ...shared, status: 'approved' }, true, true)).toBe(false);
    }
    expect(canReview({ ...fact, shared: false }, true, false)).toBe(true);
    expect(isShared({ ...fact, type: 'rule' })).toBe(true);
  });

  it('places all disagreements ahead of every source group without losing source order', () => {
    const card = (id: string, group: string, type: ReviewCard['type'] = 'fact') => ({
      ...fact,
      id,
      group,
      type,
    });
    const groups = reviewGroups([
      card('fact-a', 'First'),
      card('conflict-a', 'Second', 'disagreement'),
      card('fact-b', 'Second'),
      card('conflict-b', 'Third', 'disagreement'),
      card('fact-c', 'Disagreements to resolve'),
    ]);
    expect(groups.flatMap((group) => group.cards.map((card) => card.id))).toEqual([
      'conflict-a',
      'conflict-b',
      'fact-a',
      'fact-b',
      'fact-c',
    ]);
    expect(new Set(groups.map((group) => group.key)).size).toBe(groups.length);
  });
});
