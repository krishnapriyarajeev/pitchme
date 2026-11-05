import { useCallback, useEffect, useRef, useState } from 'react';

type Snapshot<T> = { key: string; data?: T; error?: unknown };

type Options<T> = {
  /** Fetch again every `pollMs` while `keepPolling` says yes. */
  pollMs?: number;
  /** For example: poll an analysis until it is complete or failed. */
  keepPolling?: (data: T | undefined) => boolean;
};

export type RequestState<T> = {
  data: T | undefined;
  /** The last error. Data from an earlier success stays in `data`. */
  error: unknown;
  /** True until the first answer for this key. */
  loading: boolean;
  /** True while a reload asked for by the user runs. */
  refreshing: boolean;
  reload: () => Promise<void>;
};

/**
 * Load data for a screen. `key` names what is loaded (for example
 * "session:123"): a new key loads again, and null loads nothing. An answer
 * for an old key is dropped, so a slow reply never shows on the wrong
 * screen.
 */
export function useRequest<T>(
  key: string | null,
  fetcher: () => Promise<T>,
  { pollMs, keepPolling }: Options<T> = {},
): RequestState<T> {
  const [snapshot, setSnapshot] = useState<Snapshot<T> | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const latestFetcher = useRef(fetcher);
  const currentKey = useRef(key);

  useEffect(() => {
    latestFetcher.current = fetcher;
    currentKey.current = key;
  });

  const fetchFor = useCallback(async (forKey: string) => {
    try {
      const data = await latestFetcher.current();
      if (currentKey.current === forKey) setSnapshot({ key: forKey, data });
    } catch (error) {
      if (currentKey.current !== forKey) return;
      setSnapshot((last) => ({
        key: forKey,
        data: last?.key === forKey ? last.data : undefined,
        error,
      }));
    }
  }, []);

  useEffect(() => {
    if (key !== null) void fetchFor(key);
  }, [key, fetchFor]);

  const current = snapshot?.key === key ? snapshot : undefined;
  const polling =
    key !== null && !!pollMs && current !== undefined && (keepPolling?.(current.data) ?? true);

  useEffect(() => {
    if (!polling || key === null) return;
    const timer = setInterval(() => void fetchFor(key), pollMs);
    return () => clearInterval(timer);
  }, [polling, key, pollMs, fetchFor]);

  const reload = useCallback(async () => {
    if (key === null) return;
    setRefreshing(true);
    try {
      await fetchFor(key);
    } finally {
      setRefreshing(false);
    }
  }, [key, fetchFor]);

  return {
    data: current?.data,
    error: current?.error,
    loading: key !== null && current === undefined,
    refreshing,
    reload,
  };
}
