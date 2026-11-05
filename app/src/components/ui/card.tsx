import { StyleSheet, View, type StyleProp, type ViewProps, type ViewStyle } from 'react-native';

import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type Props = ViewProps & {
  /** 'hero' for the one card a screen is about, 'quiet' for a soft panel. */
  tone?: 'list' | 'hero' | 'quiet';
  padded?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function Card({ tone = 'list', padded = true, style, ...rest }: Props) {
  const theme = useTheme();
  const quiet = tone === 'quiet';

  return (
    <View
      style={[
        {
          borderRadius: tone === 'hero' ? Radius.hero : Radius.card,
          backgroundColor: quiet ? theme.surfaceAlt : theme.surface,
          borderWidth: quiet ? 0 : 1,
          borderColor: theme.border,
          padding: padded ? (tone === 'hero' ? 22 : 18) : 0,
        },
        style,
      ]}
      {...rest}
    />
  );
}

/** A line inside a card, lighter than the card's own border. */
export function CardDivider() {
  const theme = useTheme();
  return <View style={[styles.divider, { backgroundColor: theme.hairline }]} />;
}

const styles = StyleSheet.create({
  divider: { height: 1, marginVertical: Spacing.three - 2 },
});
