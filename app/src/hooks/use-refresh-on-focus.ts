import { useFocusEffect } from 'expo-router';
import { useCallback, useRef } from 'react';

/**
 * Load again when the user comes back to a screen, but not on its first
 * show. A screen under a pushed one stays mounted, so without this a
 * rehearsal made two screens later would be missing from its list.
 */
export function useRefreshOnFocus(reload: () => unknown) {
  const seen = useRef(false);
  useFocusEffect(
    useCallback(() => {
      if (!seen.current) {
        seen.current = true;
        return;
      }
      void reload();
    }, [reload]),
  );
}
