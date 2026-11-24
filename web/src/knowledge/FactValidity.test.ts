import { describe, expect, it } from 'vitest';
import { needsEndDateCheck } from './FactValidity';

describe('dated fact reminder', () => {
  it('flags dates and explicit terms without inventing an end date', () => {
    for (const text of [
      'Deadline December 4.',
      'Deadline 4 December.',
      'Ends 2026-12-04',
      'For this semester only',
      'Fall semester deadline',
    ])
      expect(needsEndDateCheck(null, text)).toBe(true);
  });
  it('does not claim that missing server metadata means permanent knowledge', () => {
    expect(needsEndDateCheck(undefined, 'Deadline December 4')).toBe(false);
    expect(needsEndDateCheck('2026-12-31', 'Deadline December 4')).toBe(false);
    expect(needsEndDateCheck(null, 'You may contact the office.')).toBe(false);
    expect(needsEndDateCheck(null, 'Allow 10 days for a response.')).toBe(false);
  });
});
