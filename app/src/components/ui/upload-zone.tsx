import { Pressable, StyleSheet, View } from 'react-native';

import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { Radius } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type Props = {
  title: string;
  /** What belongs here, in the user's words. */
  detail?: string;
  /** The file types it takes, smaller and fainter. */
  formats?: string;
  onPress: () => void;
  disabled?: boolean;
  compact?: boolean;
};

/** A dashed box that opens the file picker. A phone has no drag and drop. */
export function UploadZone({ title, detail, formats, onPress, disabled, compact }: Props) {
  const theme = useTheme();

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityHint={detail}
      accessibilityState={{ disabled: !!disabled }}
      style={({ pressed }) => [
        styles.zone,
        compact && styles.compact,
        {
          borderColor: theme.border,
          backgroundColor: pressed ? theme.surfaceAlt : 'transparent',
          opacity: disabled ? 0.5 : 1,
        },
      ]}>
      <View style={[styles.badge, { backgroundColor: theme.accentSoft }]}>
        <Icon name="upload" size={16} color={theme.accent} strokeWidth={2} />
      </View>
      <Text variant="rowTitle" style={styles.title}>
        {title}
      </Text>
      {detail ? (
        <Text variant="secondary" color="textSecondary" style={styles.centred}>
          {detail}
        </Text>
      ) : null}
      {formats ? (
        <Text variant="secondary" color="textSubtle" style={[styles.centred, styles.formats]}>
          {formats}
        </Text>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  zone: {
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderRadius: Radius.card,
    paddingVertical: 22,
    paddingHorizontal: 18,
    alignItems: 'center',
    gap: 4,
  },
  compact: { paddingVertical: 16 },
  badge: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: { marginTop: 6 },
  centred: { textAlign: 'center' },
  formats: { fontSize: 12 },
});
