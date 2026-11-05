import { useEffect } from 'react';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Path } from 'react-native-svg';

import { Motion } from '@/constants/motion';
import { useReducedMotion } from '@/hooks/use-reduced-motion';

type Props = {
  size?: number;
  color: string;
  trackColor: string;
  strokeWidth?: number;
  duration?: number;
  accessibilityLabel?: string;
};

/** Ambient: shows only while work is in progress. */
export function Spinner({
  size = 24,
  color,
  trackColor,
  strokeWidth = 2.6,
  duration = Motion.ambient.spin,
  accessibilityLabel = 'Loading',
}: Props) {
  const reduced = useReducedMotion();
  const angle = useSharedValue(0);

  useEffect(() => {
    angle.set(
      reduced ? 0 : withRepeat(withTiming(360, { duration, easing: Easing.linear }), -1, false),
    );
  }, [reduced, duration, angle]);

  const animated = useAnimatedStyle(() => ({ transform: [{ rotate: `${angle.get()}deg` }] }));
  const r = 12 - strokeWidth / 2 - 0.4;

  return (
    <Animated.View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={accessibilityLabel}
      style={[{ width: size, height: size }, animated]}>
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="12" cy="12" r={r} stroke={trackColor} strokeWidth={strokeWidth} />
        <Path
          d={`M12 ${12 - r}A${r} ${r} 0 0 1 ${12 + r * 0.87} ${12 - r * 0.5}`}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
      </Svg>
    </Animated.View>
  );
}
