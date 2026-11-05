import { StyleSheet, View } from 'react-native';
import Svg, { Circle, Defs, RadialGradient, Stop } from 'react-native-svg';

import { useScheme, useTheme } from '@/hooks/use-theme';

/**
 * The same opacity looks very different on each ground: a light orchid
 * glows on near-black, a deep plum barely shows on cream. Light needs about
 * twice as much.
 */
const STRENGTH = {
  light: { accent: 0.2, sage: 0.26 },
  dark: { accent: 0.13, sage: 0.16 },
} as const;

export type Glow = { cx: number; cy: number; r: number; color: 'accent' | 'sage' };

/**
 * Soft glows behind a screen. React Native has no CSS blur; radial gradients
 * give the same soft edge at no cost.
 */
export function AmbientBackdrop({ glows }: { glows: readonly Glow[] }) {
  const theme = useTheme();
  const strength = STRENGTH[useScheme()];

  return (
    <View style={[StyleSheet.absoluteFill, styles.passThrough]}>
      <Svg width="100%" height="100%">
        <Defs>
          <RadialGradient id="accentGlow" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={theme.accent} stopOpacity={strength.accent} />
            <Stop offset="100%" stopColor={theme.accent} stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="sageGlow" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={theme.sage} stopOpacity={strength.sage} />
            <Stop offset="100%" stopColor={theme.sage} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        {glows.map((glow, i) => (
          <Circle
            key={i}
            cx={glow.cx}
            cy={glow.cy}
            r={glow.r}
            fill={glow.color === 'accent' ? 'url(#accentGlow)' : 'url(#sageGlow)'}
          />
        ))}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  passThrough: { pointerEvents: 'none' },
});
