import { describe, expect, it } from 'vitest';
import { initialProgress, learningQuestion, progressKey, readProgress, steps } from './progress';

describe('role introduction metadata', () => {
  it('isolates mode, club, member and role, including separator-containing IDs', () => {
    const values = [
      progressKey('http', 'a', 'b', 'president'),
      progressKey('demo', 'a', 'b', 'president'),
      progressKey('http', 'other', 'b', 'president'),
      progressKey('http', 'a', 'other', 'president'),
      progressKey('http', 'a', 'b', 'events'),
      progressKey('http', 'a.b', 'c', 'events'),
      progressKey('http', 'a', 'b.c', 'events'),
    ];
    expect(new Set(values).size).toBe(values.length);
  });
  it('refuses malformed, future-version and out-of-range saved progress', () => {
    for (const value of [
      '{',
      'null',
      '[]',
      '{"version":2}',
      ...[-1, 4, 0.5, '1'].map((step) =>
        JSON.stringify({ version: 1, step, status: 'active', learning: true }),
      ),
    ]) {
      expect(readProgress(value)).toEqual(initialProgress());
    }
    expect(
      readProgress(
        JSON.stringify({
          version: 1,
          step: 2,
          status: 'paused',
          learning: true,
          secret: 'discard',
        }),
      ),
    ).toEqual({ version: 1, step: 2, status: 'paused', learning: true });
  });
  it('adds only selected learning context, keeping the original question and known role', () => {
    const question = 'What is still unknown?';
    const text = learningQuestion('treasurer', 2, question);
    expect(text).toContain('Treasurer');
    expect(text).toContain(steps[2].title);
    expect(text.endsWith(question)).toBe(true);
    expect(text).toContain('approved club knowledge with sources');
  });
});
