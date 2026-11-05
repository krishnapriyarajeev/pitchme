import { useEffect, type ReactNode } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { EaseInOut, Motion } from '@/constants/motion';
import { useReducedMotion } from '@/hooks/use-reduced-motion';

type Props = {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  scaleTo?: number;
  duration?: number;
  delay?: number;
};

/**
 * Ambient: a very slow scale, just enough to look alive. Only the main
 * action on Home breathes. If two things do, neither one stands out.
 */
export function Breathe({
  children,
  style,
  scaleTo = 1.014,
  duration = Motion.ambient.breathe,
  delay = 1000,
}: Props) {
  const reduced = useReducedMotion();
  const t = useSharedValue(0);

  useEffect(() => {
    t.set(
      reduced
        ? 0
        : withDelay(
            delay,
            withRepeat(withTiming(1, { duration: duration / 2, easing: EaseInOut }), -1, true),
          ),
    );
  }, [reduced, duration, delay, t]);

  const animated = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + t.get() * (scaleTo - 1) }],
  }));

  return <Animated.View style={[style, animated]}>{children}</Animated.View>;
}
