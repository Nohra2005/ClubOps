import type { ReviewCard } from './types';

/** Flagged proposals need an individual source review, even when their type is fact. */
export function canBatchApprove(card: ReviewCard) {
  return card.type === 'fact' && card.status === 'pending' && !card.warning && !card.outdated;
}
