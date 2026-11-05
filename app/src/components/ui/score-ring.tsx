import { useEffect, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  useAnimatedProps,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle } from 'react-native-svg';

import { EaseOut, Motion } from '@/constants/motion';
import { useReducedMotion } from '@/hooks/use-reduced-motion';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

type Props = {
  /** 0 to 100. */
  score: number;
  color: string;
  trackColor: string;
  size?: number;
  strokeWidth?: number;
  delay?: number;
  /** Shown in the middle of the ring, usually the number. */
  children?: ReactNode;
};

/** Data: the arc draws from zero to the score the first time it shows. */
export function ScoreRing({
  score,
  color,
  trackColor,
  size = 72,
  strokeWidth = 7,
  delay = Motion.data.delay,
  children,
}: Props) {
  const reduced = useReducedMotion();
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const clamped = Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0;
  const target = circumference * (1 - clamped / 100);
  const offset = useSharedValue(circumference);

  useEffect(() => {
    offset.set(
      reduced
        ? target
        : withDelay(
            delay,
            withTiming(target, { duration: Motion.data.ringDuration, easing: EaseOut }),
          ),
    );
  }, [reduced, target, delay, offset]);

  const props = useAnimatedProps(() => ({ strokeDashoffset: offset.get() }));
  const centre = size / 2;

  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: Math.round(clamped) }}
      style={{ width: size, height: size }}>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <Circle
          cx={centre}
          cy={centre}
          r={r}
          stroke={trackColor}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <AnimatedCircle
          cx={centre}
          cy={centre}
          r={r}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={circumference}
          animatedProps={props}
          transform={`rotate(-90 ${centre} ${centre})`}
        />
      </Svg>
      {children ? <View style={styles.centre}>{children}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  centre: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
