import type { StorageLike } from './mock';

export const starterSteps = ['cabinet', 'rules', 'proposal', 'context'] as const;
export type StarterStep = (typeof starterSteps)[number];
export type StarterProgress = Record<StarterStep, boolean>;
export const emptyStarter = (): StarterProgress => ({
  cabinet: false,
  rules: false,
  proposal: false,
  context: false,
});

export function starterKey(mode: 'demo' | 'http', club: string, member: string) {
  return `clubops.starter.v1.${JSON.stringify([mode, club, member])}`;
}

export function readStarter(storage: StorageLike, key: string): StarterProgress {
  try {
    const value = JSON.parse(storage.getItem(key) ?? 'null');
    if (!value || value.version !== 1) return emptyStarter();
    return Object.fromEntries(
      starterSteps.map((step) => [step, value[step] === true]),
    ) as StarterProgress;
  } catch {
    return emptyStarter();
  }
}

export function saveStarter(storage: StorageLike, key: string, progress: StarterProgress) {
  storage.setItem(
    key,
    JSON.stringify({
      version: 1,
      ...Object.fromEntries(starterSteps.map((step) => [step, progress[step] === true])),
    }),
  );
}

export function checkStarterFile(file: File) {
  if (!/\.(txt|md|csv|eml|xlsx)$/i.test(file.name))
    throw new Error('Choose TXT, MD, CSV, EML or XLSX. Export a text version of a PDF first.');
  if (!file.size || file.size > 2 * 1024 * 1024)
    throw new Error('Choose a nonempty document no larger than 2 MB.');
}

export function checkStarterUpload(value: unknown) {
  if (
    !value ||
    typeof value !== 'object' ||
    !('item_id' in value) ||
    typeof value.item_id !== 'string' ||
    !value.item_id.trim() ||
    !('tab' in value) ||
    value.tab !== 'documents'
  ) {
    throw new Error(
      'The server did not confirm this document upload. Keep the file and retry explicitly.',
    );
  }
}
