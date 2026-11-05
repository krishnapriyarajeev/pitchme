import type { ReactNode } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { Icon, type IconName } from '@/components/ui/icon';
import { Radius } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type Tone = 'positive' | 'quiet' | 'attention';

type Props = {
  /** 'positive' reassures, 'quiet' gives context, 'attention' asks for a fix. */
  tone?: Tone;
  icon?: IconName;
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
};

export function Callout({ tone = 'quiet', icon, children, style }: Props) {
  const theme = useTheme();
  const look: Record<Tone, { background: string; icon: string }> = {
    positive: { background: theme.sageSoft, icon: theme.sageDeep },
    quiet: { background: theme.surfaceAlt, icon: theme.textSubtle },
    attention: { background: theme.goldSoft, icon: theme.gold },
  };

  return (
    <View style={[styles.base, { backgroundColor: look[tone].background }, style]}>
      {icon ? (
        <View style={styles.icon}>
          <Icon name={icon} size={19} color={look[tone].icon} strokeWidth={1.5} />
        </View>
      ) : null}
      <View style={styles.body}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    gap: 12,
    borderRadius: Radius.control,
    paddingHorizontal: 16,
    paddingVertical: 15,
  },
  icon: { marginTop: 1 },
  body: { flex: 1 },
});
