import { useCallback, useEffect, useRef, useState } from 'react';

import { listSessions, type SessionSummary } from '@/lib/api';

export const PAGE_SIZE = 20;

type State = {
  items: SessionSummary[];
  loading: boolean;
  loadingMore: boolean;
  error: unknown;
  hasMore: boolean;
};

/** The user's rehearsals, newest first, a page at a time. */
export function useSessionList(pageSize = PAGE_SIZE) {
  const [state, setState] = useState<State>({
    items: [],
    loading: true,
    loadingMore: false,
    error: null,
    hasMore: false,
  });
  // Bumped on reload, so a page that arrives after a reload is dropped.
  const generation = useRef(0);

  const load = useCallback(
    async (offset: number) => {
      const mine = generation.current;
      try {
        const page = await listSessions(pageSize, offset);
        if (mine !== generation.current) return;
        setState((current) => ({
          items: offset === 0 ? page : [...current.items, ...page],
          loading: false,
          loadingMore: false,
          error: null,
          hasMore: page.length === pageSize,
        }));
      } catch (error) {
        if (mine !== generation.current) return;
        setState((current) => ({ ...current, loading: false, loadingMore: false, error }));
      }
    },
    [pageSize],
  );

  useEffect(() => {
    void load(0);
  }, [load]);

  const reload = useCallback(() => {
    generation.current += 1;
    return load(0);
  }, [load]);

  const loadMore = useCallback(() => {
    if (state.loading || state.loadingMore || !state.hasMore) return;
    setState((current) => ({ ...current, loadingMore: true }));
    void load(state.items.length);
  }, [load, state.loading, state.loadingMore, state.hasMore, state.items.length]);

  return { ...state, reload, loadMore };
}
