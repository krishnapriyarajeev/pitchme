import { useEffect, type ReactNode } from 'react';
import type { StyleProp, ViewProps, ViewStyle } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';

import { EaseOut, Motion, stagger } from '@/constants/motion';
import { useReducedMotion } from '@/hooks/use-reduced-motion';

type Props = ViewProps & {
  /** Place in a group; 0 comes first. */
  index?: number;
  /** A delay in ms, in place of the one from `index`. */
  delay?: number;
  style?: StyleProp<ViewStyle>;
  children?: ReactNode;
};

/**
 * Entrance: rises and fades in once, on mount. Shared values, not the
 * `entering` prop, so it acts the same on the web.
 */
export function Rise({ index = 0, delay, style, children, ...rest }: Props) {
  const reduced = useReducedMotion();
  const progress = useSharedValue(0);

  useEffect(() => {
    if (reduced) {
      progress.set(1);
      return;
    }
    progress.set(
      withDelay(
        delay ?? stagger(index),
        withTiming(1, { duration: Motion.entrance.duration, easing: EaseOut }),
      ),
    );
  }, [reduced, delay, index, progress]);

  const animated = useAnimatedStyle(() => ({
    opacity: progress.get(),
    transform: [{ translateY: (1 - progress.get()) * Motion.entrance.offset }],
  }));

  return (
    <Animated.View style={[style, animated]} {...rest}>
      {children}
    </Animated.View>
  );
}
