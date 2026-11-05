import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { Icon, type IconName } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { Radius } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type Variant = 'primary' | 'secondary' | 'quiet' | 'text';

type Props = {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  icon?: IconName;
  /** Put the icon after the label. */
  iconTrailing?: boolean;
  disabled?: boolean;
  /** Shows a spinner and blocks presses, for example while a request runs. */
  loading?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function Button({
  label,
  onPress,
  variant = 'primary',
  icon,
  iconTrailing = false,
  disabled = false,
  loading = false,
  style,
}: Props) {
  const theme = useTheme();
  const look = {
    primary: { surface: { backgroundColor: theme.accent }, ink: theme.onAccent },
    secondary: {
      surface: { backgroundColor: theme.surface, borderWidth: 1.5, borderColor: theme.borderStrong },
      ink: theme.text,
    },
    quiet: { surface: { backgroundColor: theme.surfaceAlt }, ink: theme.accent },
    text: { surface: { backgroundColor: 'transparent' }, ink: theme.textSecondary },
  }[variant];
  const glyph = icon ? <Icon name={icon} size={19} color={look.ink} /> : null;

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled, busy: loading }}
      style={({ pressed }) => [
        styles.base,
        variant === 'text' && styles.textVariant,
        look.surface,
        { opacity: disabled ? 0.45 : pressed ? 0.8 : 1 },
        style,
      ]}>
      {loading ? (
        <ActivityIndicator color={look.ink} />
      ) : (
        <View style={styles.row}>
          {iconTrailing ? null : glyph}
          <Text variant="control" color={look.ink}>
            {label}
          </Text>
          {iconTrailing ? glyph : null}
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 54,
    borderRadius: Radius.control,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 18,
  },
  textVariant: { height: 48 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 9 },
});
