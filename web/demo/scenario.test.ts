import { describe, expect, it } from 'vitest';
import {
  ANSWER,
  CARD_ID,
  DENIED_ID,
  DESCRIPTION,
  DOCUMENT,
  EVENT_ID,
  FILE_NAME,
  RehearsalScenario,
  RUN_ID,
  SETUP_ANSWER,
  SETUP_CARD_ID,
  validateLocalOrigin,
} from './scenario';

describe('local-only rehearsal configuration', () => {
  it.each(['http://127.0.0.1:5174', 'http://127.0.0.1:5176/'])(
    'accepts dedicated Vite origin %s',
    (url) => {
      expect(validateLocalOrigin(url)).toMatch(/^http:\/\/127\.0\.0\.1:517[46]$/);
    },
  );
  it.each([
    'https://club.example.invalid',
    'http://127.0.0.1:9000',
    'http://localhost:5176',
    'http://127.0.0.1:5176/events',
    'http://secret@127.0.0.1:5176',
    'http://127.0.0.1:5176?secret=value',
    'not a URL',
  ])('rejects non-rehearsal target %s', (url) => {
    expect(() => validateLocalOrigin(url)).toThrow('dedicated loopback');
  });
});

describe('strict synthetic screenplay', () => {
  it('keeps an explicit interview answer pending Review and resumes without resubmitting it', () => {
    const scene = new RehearsalScenario();
    scene.beginOnboarding();
    expect(scene.respond('GET', '/me').json).toMatchObject({ club: { setup_complete: false } });
    expect(scene.setupCounts).toEqual({ resumes: 0, answers: 0, rejections: 0 });
    expect(scene.respond('POST', '/setup/next', {}, 'ClubOps').json).toMatchObject({
      index: 1,
      done: false,
    });
    expect(
      scene.respond('POST', '/setup/next', { answer: SETUP_ANSWER }, 'ClubOps').json,
    ).toMatchObject({ index: 2, done: false });
    expect(scene.respond('GET', '/review').json).toMatchObject([
      { id: SETUP_CARD_ID, status: 'pending' },
    ]);
    expect(scene.counts.approvals).toBe(0);
    expect(scene.respond('POST', '/setup/next', {}, 'ClubOps').json).toMatchObject({ index: 2 });
    expect(scene.setupCounts.answers).toBe(1);
    expect(scene.respond('POST', '/setup/next', { answer: SETUP_ANSWER }, 'ClubOps').status).toBe(
      501,
    );
    scene.respond('POST', `/review/${SETUP_CARD_ID}`, { decision: 'reject' }, 'ClubOps');
    expect(scene.respond('GET', '/review').json).toEqual([]);
    expect(scene.setupCounts).toEqual({ resumes: 2, answers: 1, rejections: 1 });
    expect(scene.respond('GET', '/me').json).toMatchObject({ club: { setup_complete: false } });
  });
  it('makes no state change before a matching explicit action', () => {
    const scene = new RehearsalScenario();
    expect(scene.respond('GET', '/me').status).toBe(200);
    expect(scene.respond('GET', '/review').json).toEqual([]);
    expect(scene.counts).toEqual({
      plans: 0,
      answers: 0,
      approvals: 0,
      uploads: 0,
      rejections: 0,
      denied: 0,
    });
    expect(
      scene.respond('POST', `/events/${EVENT_ID}/approve-plan`, { revision: 1 }, 'ClubOps').status,
    ).toBe(501);
    expect(scene.counts.approvals).toBe(0);
  });
  it('requires the declared description/answer and a separate approval', () => {
    const scene = new RehearsalScenario();
    expect(
      scene.respond('POST', '/events/plan', { description: DESCRIPTION }, 'ClubOps').status,
    ).toBe(202);
    expect(scene.respond('GET', `/runs/${RUN_ID}`).json).toMatchObject({
      status: 'waiting_for_user',
    });
    expect(
      scene.respond('POST', `/runs/${RUN_ID}/answer`, { text: ANSWER }, 'ClubOps').json,
    ).toMatchObject({ status: 'done' });
    expect(scene.counts.approvals).toBe(0);
    expect(
      scene.respond('POST', `/events/${EVENT_ID}/approve-plan`, { revision: 1 }, 'ClubOps').json,
    ).toMatchObject({ status: 'approved' });
  });
  it('rejects unknown routes and missing write headers without falling through', () => {
    const scene = new RehearsalScenario();
    expect(scene.respond('GET', '/unregistered').status).toBe(501);
    expect(scene.respond('POST', '/events/plan', { description: DESCRIPTION }).status).toBe(403);
    expect(scene.counts.plans).toBe(0);
  });
  it('only queues the supplied synthetic document and keeps the warning until rejected', () => {
    const scene = new RehearsalScenario();
    expect(scene.respond('POST', '/documents', 'other bytes', 'ClubOps').status).toBe(501);
    expect(scene.respond('POST', '/documents', FILE_NAME + DOCUMENT, 'ClubOps').status).toBe(200);
    expect(scene.respond('GET', '/review').json).toMatchObject([
      { warning: expect.stringContaining('hidden instructions') },
    ]);
    expect(
      scene.respond('POST', `/review/${CARD_ID}`, { decision: 'approve' }, 'ClubOps').status,
    ).toBe(501);
    scene.respond('POST', `/review/${CARD_ID}`, { decision: 'reject' }, 'ClubOps');
    expect(scene.respond('GET', '/review').json).toEqual([]);
    expect(scene.counts.rejections).toBe(1);
  });
  it('returns scripted 403 for the read-only role and leaves the target unapproved', () => {
    const scene = new RehearsalScenario();
    scene.setAdviser();
    expect(scene.respond('GET', '/me').json).toMatchObject({ role: 'adviser' });
    expect(
      scene.respond('POST', `/events/${DENIED_ID}/approve-plan`, { revision: 1 }, 'ClubOps').status,
    ).toBe(403);
    expect(scene.respond('GET', `/events/${DENIED_ID}`).json).toMatchObject({ status: 'planned' });
    expect(scene.counts.approvals).toBe(0);
  });
  it('returns independent snapshots so UI clients cannot change the fixture silently', () => {
    const scene = new RehearsalScenario();
    const first = scene.respond('GET', `/events/${EVENT_ID}`).json as { title: string };
    first.title = 'unexpected';
    expect(scene.respond('GET', `/events/${EVENT_ID}`).json).toMatchObject({
      title: 'Synthetic club workshop',
    });
  });
});
