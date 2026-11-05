import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Icon, type IconName } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';

type Props = {
  icon: IconName;
  title: string;
  body?: string;
  /** One next step, for example "Try again" after a failed load. */
  action?: { label: string; onPress: () => void };
};

/** What a screen shows when it has nothing to list, or could not load. */
export function EmptyState({ icon, title, body, action }: Props) {
  const theme = useTheme();

  return (
    <View style={styles.wrap}>
      <View style={[styles.badge, { backgroundColor: theme.surfaceAlt }]}>
        <Icon name={icon} size={22} color={theme.textSubtle} />
      </View>
      <Text variant="rowTitle" style={styles.centred} accessibilityRole="header">
        {title}
      </Text>
      {body ? (
        <Text variant="secondary" color="textSecondary" style={styles.centred}>
          {body}
        </Text>
      ) : null}
      {action ? (
        <Button
          label={action.label}
          variant="quiet"
          onPress={action.onPress}
          style={styles.action}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: 6, paddingVertical: 32, paddingHorizontal: 12 },
  badge: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  centred: { textAlign: 'center' },
  action: { marginTop: 12, alignSelf: 'stretch' },
});
