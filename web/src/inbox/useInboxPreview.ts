import { useSyncExternalStore } from 'react';
import { useApp } from '../AppContext';
import type { ApiClient } from '../api/client';
import { initialPreview, reducePreview, type PreviewAction, type PreviewState } from './preview';

function createStore() {
  let state = initialPreview();
  const listeners = new Set<() => void>();
  return {
    snapshot: () => state,
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    update: (next: PreviewState) => {
      state = next;
      listeners.forEach((listener) => listener());
    },
  };
}
// Ephemeral per API/session identity. No addresses, codes or message bodies go to browser storage.
const stores = new WeakMap<ApiClient, ReturnType<typeof createStore>>();
export function useInboxPreview() {
  const { api, canEdit, isPresident } = useApp();
  if (api.mode !== 'demo')
    throw new Error('Inbox preview is available only in the demo workspace.');
  let store = stores.get(api);
  if (!store) {
    store = createStore();
    stores.set(api, store);
  }
  const state = useSyncExternalStore(store.subscribe, store.snapshot);
  const dispatch = (action: PreviewAction) =>
    store.update(reducePreview(store.snapshot(), action, { canEdit, isPresident }));
  return { state, dispatch, canEdit, isPresident };
}
