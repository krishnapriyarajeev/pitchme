import { act, renderHook, waitFor } from '@testing-library/react-native';

import { useRequest } from '@/hooks/use-request';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

describe('useRequest', () => {
  it('loads once, then holds the data', async () => {
    const fetcher = jest.fn().mockResolvedValue('profile');
    const { result } = await renderHook(() => useRequest('profile', fetcher));

    await waitFor(() => expect(result.current.data).toBe('profile'));
    expect(result.current.loading).toBe(false);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('loads nothing for a null key', async () => {
    const fetcher = jest.fn();
    const { result } = await renderHook(() => useRequest(null, fetcher));
    expect(result.current.loading).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('keeps the last data when a reload fails', async () => {
    const fetcher = jest.fn().mockResolvedValueOnce('first').mockRejectedValueOnce(new Error('x'));
    const { result } = await renderHook(() => useRequest('list', fetcher));
    await waitFor(() => expect(result.current.data).toBe('first'));

    await act(() => result.current.reload());

    expect(result.current.data).toBe('first');
    expect(result.current.error).toEqual(new Error('x'));
    expect(result.current.refreshing).toBe(false);
  });

  it('drops a slow answer for a key that is no longer shown', async () => {
    const slow = deferred<string>();
    const fetchers: Record<string, () => Promise<string>> = {
      a: () => slow.promise,
      b: () => Promise.resolve('session b'),
    };
    const { result, rerender } = await renderHook(
      ({ id }: { id: string }) => useRequest(`session:${id}`, () => fetchers[id]!()),
      { initialProps: { id: 'a' } },
    );

    await rerender({ id: 'b' });
    await waitFor(() => expect(result.current.data).toBe('session b'));
    await act(async () => slow.resolve('session a'));

    expect(result.current.data).toBe('session b');
  });

  it('polls until told to stop', async () => {
    let calls = 0;
    const fetcher = jest.fn(async () => (++calls >= 3 ? 'complete' : 'running'));
    const { result } = await renderHook(() =>
      useRequest('analysis', fetcher, {
        pollMs: 10,
        keepPolling: (status) => status !== 'complete',
      }),
    );

    await waitFor(() => expect(result.current.data).toBe('complete'));
    await act(() => new Promise((done) => setTimeout(done, 50)));
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
});
