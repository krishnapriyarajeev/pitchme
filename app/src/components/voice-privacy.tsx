import { StyleSheet, View } from 'react-native';

import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';

export function VoicePrivacy() {
  const theme = useTheme();
  return (
    <View style={styles.row}>
      <Icon name="shield-check" size={16} color={theme.sage} strokeWidth={1.4} />
      <Text variant="secondary" color="textSecondary" style={styles.text}>
        Your sample is stored in your own folder and used only to speak stronger answers back to
        you. Record a new one at any time from Profile.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 9, alignItems: 'flex-start' },
  text: { flex: 1 },
});
