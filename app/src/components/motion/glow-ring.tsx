import { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { EaseOut, Motion } from '@/constants/motion';
import { useReducedMotion } from '@/hooks/use-reduced-motion';

type Props = {
  size: number;
  color: string;
  /** How far the ring grows past `size` before it fades out. */
  scaleTo?: number;
  duration?: number;
  borderWidth?: number;
};

/**
 * Ambient: a ring grows out of a round control and fades, to say "this is
 * live" or "press this". Put it first inside a parent of the same size.
 */
export function GlowRing({
  size,
  color,
  scaleTo = 1.5,
  duration = Motion.ambient.glowRing,
  borderWidth = 2,
}: Props) {
  const reduced = useReducedMotion();
  const t = useSharedValue(0);

  useEffect(() => {
    t.set(reduced ? 0 : withRepeat(withTiming(1, { duration, easing: EaseOut }), -1, false));
  }, [reduced, duration, t]);

  const animated = useAnimatedStyle(() => ({
    opacity: 0.25 * (1 - t.get()),
    transform: [{ scale: 1 + t.get() * (scaleTo - 1) }],
  }));

  if (reduced) return null;

  return (
    <Animated.View
      style={[
        StyleSheet.absoluteFill,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          borderWidth,
          borderColor: color,
          pointerEvents: 'none',
        },
        animated,
      ]}
    />
  );
}
