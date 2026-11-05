import { Pressable, StyleSheet, type StyleProp, type ViewStyle } from 'react-native';

import { Icon, type IconName } from '@/components/ui/icon';
import { HitTarget } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type Props = {
  name: IconName;
  onPress?: () => void;
  /** The drawn size. The tap area is always at least HitTarget. */
  size?: number;
  color?: string;
  accessibilityLabel: string;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
};

/**
 * Pads a small icon out to a full tap area. A negative margin keeps the
 * layout at the icon's own size.
 */
export function IconButton({
  name,
  onPress,
  size = 24,
  color,
  accessibilityLabel,
  disabled,
  style,
}: Props) {
  const theme = useTheme();
  const pad = Math.max(0, (HitTarget - size) / 2);

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ disabled: !!disabled }}
      style={({ pressed }) => [
        styles.base,
        { padding: pad, margin: -pad, opacity: disabled ? 0.4 : pressed ? 0.55 : 1 },
        style,
      ]}>
      <Icon name={name} size={size} color={color ?? theme.text} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: { alignItems: 'center', justifyContent: 'center' },
});
