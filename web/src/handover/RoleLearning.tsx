import { createContext, useContext, useState, type ReactNode } from 'react';
import { storage } from '../api';
import { useApp } from '../AppContext';
import { progressKey, readProgress, type Progress } from './progress';

const Context = createContext<{
  progress: Progress;
  update: (change: Partial<Progress>) => void;
} | null>(null);
export function RoleLearningProvider({ children }: { children: ReactNode }) {
  const { api, me } = useApp();
  const key = progressKey(api.mode, me.club.id, me.user.member_id, me.role);
  // The parent keys this provider by session identity, preventing cross-member state reuse.
  const [progress, setProgress] = useState(() => readProgress(storage.getItem(key)));
  function update(change: Partial<Progress>) {
    const next = readProgress(JSON.stringify({ ...progress, ...change, version: 1 }));
    setProgress(next);
    storage.setItem(key, JSON.stringify(next));
  }
  return <Context value={{ progress, update }}>{children}</Context>;
}
export function useRoleLearning() {
  const value = useContext(Context);
  if (!value) throw new Error('Role introduction context is missing');
  return value;
}
