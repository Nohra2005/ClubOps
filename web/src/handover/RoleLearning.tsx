import { createContext, useContext, useState, type ReactNode } from 'react';
import { storage } from '../api';
import { useApp } from '../AppContext';
import { initialProgress, progressKey, readProgress, type Progress } from './progress';

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
    setProgress((current) => {
      const next = readProgress(JSON.stringify({ ...current, ...change, version: 1 }));
      storage.setItem(key, JSON.stringify(next));
      return next;
    });
  }
  return <Context value={{ progress: progress ?? initialProgress(), update }}>{children}</Context>;
}
export function useRoleLearning() {
  const value = useContext(Context);
  if (!value) throw new Error('Role introduction context is missing');
  return value;
}
