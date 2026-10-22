import { ApiClient, httpTransport } from './client';
import { createMockTransport, readSession, sessionKey, type DemoSession, type StorageLike } from './mock';

const memory = new Map<string, string>();
export const storage: StorageLike = {
  getItem(key) { try { return localStorage.getItem(key) ?? memory.get(key) ?? null; } catch { return memory.get(key) ?? null; } },
  setItem(key, value) { memory.set(key, value); try { localStorage.setItem(key, value); } catch { window.dispatchEvent(new Event('clubops-storage-unavailable')); } },
};
export const apiMode = import.meta.env.VITE_API_MODE === 'http' ? 'http' : 'demo';
export const getDemoSession = () => readSession(storage);
export function setDemoSession(session: DemoSession) { storage.setItem(sessionKey, JSON.stringify(session)); }
export function createApi(session = getDemoSession()) { return new ApiClient(apiMode === 'http' ? httpTransport(import.meta.env.VITE_API_BASE ?? '/api') : createMockTransport(storage, session, { scenario: new URLSearchParams(location.search).get('scenario') ?? undefined }), apiMode); }
