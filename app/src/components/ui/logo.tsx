import { useEffect } from 'react';
import Animated, {
  useAnimatedProps,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Path } from 'react-native-svg';

import { EaseOut } from '@/constants/motion';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { useTheme } from '@/hooks/use-theme';

const AnimatedPath = Animated.createAnimatedComponent(Path);
const AnimatedCircle = Animated.createAnimatedComponent(Circle);

const DOT_RADIUS = 4.2;

/** Arc lengths on the 44-unit grid, so each stroke draws in cleanly. */
const ARCS = [
  { d: 'M22 15.5a9 9 0 0 1 0 13', length: 15, delay: 250, tone: 'accent', opacity: 1 },
  { d: 'M28.5 10.5a17 17 0 0 1 0 23', length: 26, delay: 450, tone: 'sage', opacity: 1 },
  { d: 'M35 5.5a25 25 0 0 1 0 33', length: 37, delay: 650, tone: 'sage', opacity: 0.38 },
] as const;

type Props = {
  size?: number;
  /** Draws the mark in once, on mount. It never loops. */
  animated?: boolean;
};

/**
 * The mark: a voice that reaches the room. A dot and three arcs that get
 * fainter as they go out. scripts/make_icons.py draws the same shape.
 */
export function Logo({ size = 44, animated = false }: Props) {
  const theme = useTheme();
  const reduced = useReducedMotion();
  const play = animated && !reduced;

  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 44 44"
      fill="none"
      accessible
      accessibilityRole="image"
      accessibilityLabel="PitchMe">
      <Dot color={theme.accent} play={play} />
      {ARCS.map((arc) => (
        <Arc
          key={arc.d}
          d={arc.d}
          length={arc.length}
          delay={arc.delay}
          opacity={arc.opacity}
          color={arc.tone === 'accent' ? theme.accent : theme.sage}
          play={play}
        />
      ))}
    </Svg>
  );
}

function Dot({ color, play }: { color: string; play: boolean }) {
  const r = useSharedValue(play ? 0 : DOT_RADIUS);

  useEffect(() => {
    if (play) r.set(withTiming(DOT_RADIUS, { duration: 500, easing: EaseOut }));
  }, [play, r]);

  const props = useAnimatedProps(() => ({ r: r.get() }));
  return <AnimatedCircle cx={13} cy={22} fill={color} animatedProps={props} />;
}

type ArcProps = {
  d: string;
  length: number;
  delay: number;
  color: string;
  opacity: number;
  play: boolean;
};

function Arc({ d, length, delay, color, opacity, play }: ArcProps) {
  const offset = useSharedValue(play ? length : 0);

  useEffect(() => {
    if (play) offset.set(withDelay(delay, withTiming(0, { duration: 700, easing: EaseOut })));
  }, [play, delay, offset]);

  const props = useAnimatedProps(() => ({ strokeDashoffset: offset.get() }));

  return (
    <AnimatedPath
      d={d}
      stroke={color}
      strokeWidth={2.2}
      strokeLinecap="round"
      opacity={opacity}
      strokeDasharray={length}
      animatedProps={props}
    />
  );
}
