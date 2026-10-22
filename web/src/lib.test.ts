import { expect, it } from 'vitest';
import { eventFor } from './api/fixtures';
import { formatTime, todayInBeirut } from './lib';

it('keeps the event time consistent with its confirmed fields across Beirut winter time', () => {
  for (const date of ['2026-10-22', '2026-11-05']) {
    const event = eventFor('ev-time-check', 'Synthetic event', date, 'draft');
    expect(formatTime(event.start)).toBe(event.fields.time);
    expect(formatTime(event.end)).toBe(event.fields.end_time);
  }
});

it('uses the Beirut date near the UTC day boundary', () => {
  expect(todayInBeirut(new Date('2026-10-22T22:30:00Z'))).toBe('2026-10-23');
});
