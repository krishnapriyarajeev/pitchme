import { useRouter, type Href } from 'expo-router';
import { useCallback } from 'react';

/**
 * Back, with a place to land. router.back() does nothing when there is no
 * history (a deep link, after a replace, a cold start on an inner screen),
 * and the back button then looks broken. This goes to `fallback` instead.
 */
export function useGoBack(fallback: Href = '/home') {
  const router = useRouter();
  return useCallback(() => {
    if (router.canGoBack()) router.back();
    else router.replace(fallback);
  }, [router, fallback]);
}
