import { StyleSheet, View } from 'react-native';

import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';

/** What to do before the real call, as a short list. */
export function BulletList({ items, icon }: { items: string[]; icon: 'check' | 'check-circle' }) {
  const theme = useTheme();
  return (
    <Card style={styles.card}>
      {items.map((item, i) => (
        <View key={`${i}-${item}`} style={styles.row}>
          <Icon name={icon} size={16} color={theme.sageDeep} />
          <Text variant="body" style={styles.text}>
            {item}
          </Text>
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { gap: 10 },
  row: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  text: { flex: 1 },
});
