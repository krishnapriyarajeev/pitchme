import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { Text } from '@/components/ui/text';
import type { ThemeColor } from '@/constants/theme';

type Props = {
  label: string;
  title?: string;
  /** The label's colour: terra only for corrections. */
  tone?: ThemeColor;
  index?: number;
  children: ReactNode;
};

/** One part of the debrief: a small label, an optional title, the content. */
export function Section({ label, title, tone = 'accent', index = 0, children }: Props) {
  return (
    <Rise index={index} style={styles.section}>
      <Text variant="pill" color={tone} accessibilityRole="header">
        {label.toUpperCase()}
      </Text>
      {title ? (
        <Text variant="cardTitle" style={styles.title}>
          {title}
        </Text>
      ) : null}
      <View style={styles.body}>{children}</View>
    </Rise>
  );
}

const styles = StyleSheet.create({
  section: { marginTop: 26 },
  title: { marginTop: 4, fontSize: 21, lineHeight: 26 },
  body: { marginTop: 12, gap: 10 },
});
