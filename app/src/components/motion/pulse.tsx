import { useEffect, type ReactNode } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { EaseInOut, Motion } from '@/constants/motion';
import { useReducedMotion } from '@/hooks/use-reduced-motion';

type Props = {
  style?: StyleProp<ViewStyle>;
  children?: ReactNode;
  /** One full cycle, in ms. */
  duration?: number;
  /** Opacity and scale at the low point of the cycle. */
  minOpacity?: number;
  minScale?: number;
};

/**
 * Ambient: fades and shrinks a little, forever. Only for something that is
 * live now, such as the dot while a call runs. Used as decoration, it would
 * tell the user something is happening when nothing is.
 */
export function Pulse({
  style,
  children,
  duration = Motion.ambient.pulse,
  minOpacity = 0.42,
  minScale = 0.86,
}: Props) {
  const reduced = useReducedMotion();
  const t = useSharedValue(0);

  useEffect(() => {
    t.set(
      reduced
        ? 0
        : withRepeat(withTiming(1, { duration: duration / 2, easing: EaseInOut }), -1, true),
    );
  }, [reduced, duration, t]);

  const animated = useAnimatedStyle(() => ({
    opacity: 1 - t.get() * (1 - minOpacity),
    transform: [{ scale: 1 - t.get() * (1 - minScale) }],
  }));

  return <Animated.View style={[style, animated]}>{children}</Animated.View>;
}
