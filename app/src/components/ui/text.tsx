import { StyleSheet, Text as NativeText, type TextProps } from 'react-native';

import { Fonts } from '@/constants/fonts';
import type { ThemeColor } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * The type scale. Headings and numbers are serif, so a score reads as a
 * coach's note rather than a grade.
 */
export type TextVariant =
  | 'display'
  | 'title'
  | 'cardTitle'
  | 'numeral'
  | 'numeralSmall'
  | 'control'
  | 'rowTitle'
  | 'body'
  | 'secondary'
  | 'label'
  | 'pill';

type Props = TextProps & {
  variant?: TextVariant;
  /** A palette name such as "textSecondary", or any colour value. */
  color?: ThemeColor | (string & {});
};

export function Text({ style, variant = 'body', color, ...rest }: Props) {
  const theme = useTheme();
  const resolved = color ? (theme[color as ThemeColor] ?? color) : theme.text;
  return <NativeText style={[styles[variant], { color: resolved }, style]} {...rest} />;
}

const styles = StyleSheet.create({
  display: { fontFamily: Fonts.serif, fontSize: 42, lineHeight: 46, letterSpacing: -0.6 },
  title: { fontFamily: Fonts.serif, fontSize: 30, lineHeight: 35, letterSpacing: -0.3 },
  cardTitle: { fontFamily: Fonts.serif, fontSize: 25, lineHeight: 30 },
  numeral: { fontFamily: Fonts.serifMedium, fontSize: 46, lineHeight: 50, letterSpacing: -1 },
  numeralSmall: { fontFamily: Fonts.serifMedium, fontSize: 20, lineHeight: 24 },
  control: { fontFamily: Fonts.sansSemiBold, fontSize: 16, lineHeight: 20 },
  rowTitle: { fontFamily: Fonts.sansMedium, fontSize: 15, lineHeight: 20 },
  body: { fontFamily: Fonts.sans, fontSize: 15, lineHeight: 23 },
  secondary: { fontFamily: Fonts.sans, fontSize: 13, lineHeight: 19 },
  label: { fontFamily: Fonts.sansMedium, fontSize: 13, lineHeight: 18, letterSpacing: 0.2 },
  pill: { fontFamily: Fonts.sansSemiBold, fontSize: 11, lineHeight: 14, letterSpacing: 0.3 },
});
