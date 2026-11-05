import { useEffect } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';

import { EaseOut, Motion } from '@/constants/motion';
import { Radius } from '@/constants/theme';
import { useReducedMotion } from '@/hooks/use-reduced-motion';

type Props = {
  /** 0 to 100. */
  value: number;
  color: string;
  trackColor: string;
  height?: number;
  delay?: number;
  style?: StyleProp<ViewStyle>;
};

/** Data: the fill grows from zero to `value` the first time it shows. */
export function GrowBar({ value, color, trackColor, height = 5, delay = 0, style }: Props) {
  const reduced = useReducedMotion();
  const target = clamp(value);
  const pct = useSharedValue(0);

  useEffect(() => {
    pct.set(
      reduced
        ? target
        : withDelay(delay, withTiming(target, { duration: Motion.data.duration, easing: EaseOut })),
    );
  }, [reduced, target, delay, pct]);

  const fill = useAnimatedStyle(() => ({ width: `${pct.get()}%` }));

  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: Math.round(target) }}
      style={[styles.track, { height, backgroundColor: trackColor }, style]}>
      <Animated.View style={[StyleSheet.absoluteFill, styles.fill, { backgroundColor: color }, fill]} />
    </View>
  );
}

function clamp(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
}

const styles = StyleSheet.create({
  track: { borderRadius: Radius.pill, overflow: 'hidden' },
  fill: { borderRadius: Radius.pill },
});
