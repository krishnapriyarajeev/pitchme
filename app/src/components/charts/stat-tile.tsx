import { StyleSheet, View } from 'react-native';

import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';

type Props = { label: string; value: string; detail?: string };

/** One number that needs no chart: the number is the message. */
export function StatTile({ label, value, detail }: Props) {
  const theme = useTheme();
  return (
    <View
      style={[styles.tile, { backgroundColor: theme.surfaceAlt }]}
      accessible
      accessibilityLabel={`${label}: ${value}${detail ? `, ${detail}` : ''}`}>
      <Text variant="pill" color="textSubtle">
        {label.toUpperCase()}
      </Text>
      <Text variant="numeralSmall">{value}</Text>
      {detail ? (
        <Text variant="secondary" color="textSecondary">
          {detail}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  tile: { flex: 1, minWidth: 120, borderRadius: 10, padding: 12, gap: 2 },
});
