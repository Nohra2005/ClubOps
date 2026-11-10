import { describe, expect, it } from 'vitest';
import {
  checkStarterFile,
  checkStarterUpload,
  emptyStarter,
  readStarter,
  saveStarter,
  starterKey,
} from './starter-progress';

describe('starter checklist metadata and upload boundaries', () => {
  it('isolates progress by club, account and transport mode without retaining private evidence', () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => {
        values.set(key, value);
      },
    };
    const key = starterKey('http', 'asme', 'm-synthetic');
    saveStarter(storage, key, {
      ...emptyStarter(),
      rules: true,
      filename: 'PRIVATE FILE',
      source: 'PRIVATE SOURCE',
    } as ReturnType<typeof emptyStarter>);
    expect(readStarter(storage, key).rules).toBe(true);
    for (const other of [
      starterKey('http', 'other', 'm-synthetic'),
      starterKey('http', 'asme', 'm-other'),
      starterKey('demo', 'asme', 'm-synthetic'),
    ])
      expect(readStarter(storage, other)).toEqual(emptyStarter());
    expect(values.get(key)).not.toContain('PRIVATE');
    expect(Object.keys(JSON.parse(values.get(key)!))).toEqual([
      'version',
      'cabinet',
      'rules',
      'proposal',
      'context',
    ]);
  });

  it('does not turn malformed, old-version or string progress into completed steps', () => {
    for (const value of [
      '{broken',
      '{"version":2,"rules":true}',
      '{"version":1,"rules":"true"}',
      'null',
    ]) {
      expect(readStarter({ getItem: () => value, setItem() {} }, 'example')).toEqual(
        emptyStarter(),
      );
    }
  });

  it('refuses empty, unsupported and oversized files before any transport call', () => {
    for (const file of [
      new File(['pdf'], 'sample.pdf'),
      new File([], 'empty.txt'),
      new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'big.txt'),
    ])
      expect(() => checkStarterFile(file)).toThrow();
    expect(() => checkStarterFile(new File(['Synthetic rules'], 'sample.MD'))).not.toThrow();
  });

  it('does not treat a successful HTTP status or an error envelope as upload acceptance', () => {
    for (const value of [
      null,
      {},
      { detail: 'private diagnostic' },
      { item_id: '', tab: 'documents' },
      { item_id: 'kh-other', tab: 'tips' },
    ])
      expect(() => checkStarterUpload(value)).toThrow('server did not confirm');
    expect(() =>
      checkStarterUpload({ item_id: 'kh-synthetic-document', tab: 'documents' }),
    ).not.toThrow();
  });
});
