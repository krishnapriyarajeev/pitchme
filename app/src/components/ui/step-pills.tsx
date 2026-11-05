import { StyleSheet, View } from 'react-native';

import { Text } from '@/components/ui/text';
import { Radius } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

/**
 * Where the user is in a short flow: equal segments across the page, with
 * the count under them. Equal segments do not make step 1 look almost done.
 */
export function StepPills({ step, total }: { step: number; total: number }) {
  const theme = useTheme();

  return (
    <View
      style={styles.wrap}
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={`Step ${step} of ${total}`}
      accessibilityValue={{ min: 0, max: total, now: step }}>
      <View style={styles.bar}>
        {Array.from({ length: total }, (_, i) => (
          <View
            key={i}
            style={[styles.segment, { backgroundColor: i < step ? theme.accent : theme.border }]}
          />
        ))}
      </View>
      <Text variant="secondary" color="textSubtle">
        Step {step} of {total}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 10 },
  bar: { flexDirection: 'row', gap: 5 },
  segment: { flex: 1, height: 4, borderRadius: Radius.pill },
});
