import type { ReviewCard } from './types';

/** Older demo/API cards used type=rule before the shared field existed. */
export function isShared(card: ReviewCard) {
  return card.shared ?? card.type === 'rule';
}

export function canReview(card: ReviewCard, canEdit: boolean, isPresident: boolean) {
  return (
    canEdit &&
    card.status === 'pending' &&
    (!(isShared(card) || card.type === 'rule') || isPresident)
  );
}

/** Shared, disputed and flagged proposals always need an individual review. */
export function canBatchApprove(card: ReviewCard) {
  return (
    card.type === 'fact' &&
    card.status === 'pending' &&
    !isShared(card) &&
    !card.warning &&
    !card.outdated &&
    !card.unlisted &&
    card.op !== 'retire'
  );
}

export function reviewGroups(cards: ReviewCard[]) {
  const disagreements = cards.filter((card) => card.type === 'disagreement');
  const groups = new Map<string, ReviewCard[]>();
  for (const card of cards)
    if (card.type !== 'disagreement')
      groups.set(card.group, [...(groups.get(card.group) ?? []), card]);
  return [
    ...(disagreements.length
      ? [{ key: 'disagreements', title: 'Disagreements to resolve', cards: disagreements }]
      : []),
    ...[...groups].map(([title, cards]) => ({ key: `source:${title}`, title, cards })),
  ];
}
