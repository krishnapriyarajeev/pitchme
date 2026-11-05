import { useSyncExternalStore } from 'react';
import { useColorScheme as useSystemScheme } from 'react-native';

const noSubscription = () => () => {};

/**
 * On the web the first render has no window to ask, so it is light until
 * the page hydrates. This avoids a mismatch between the two renders.
 */
export function useColorScheme() {
  const scheme = useSystemScheme();
  const hydrated = useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
  return hydrated ? scheme : 'light';
}
