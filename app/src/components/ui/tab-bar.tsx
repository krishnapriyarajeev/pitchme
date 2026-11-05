import { Pressable, StyleSheet, View } from 'react-native';
import type { BottomTabBarProps } from 'expo-router/tabs';

import { Icon, type IconName } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';

const ICONS: Record<string, IconName> = {
  home: 'home',
  playbook: 'book',
  profile: 'user',
};

/**
 * The bar under the three tabs. The current tab sits on a tinted disc, so it
 * is marked by shape as well as by colour.
 */
export function TabBar({ state, descriptors, navigation, insets }: BottomTabBarProps) {
  const theme = useTheme();

  return (
    <View
      accessibilityRole="tablist"
      style={[
        styles.bar,
        {
          backgroundColor: theme.background,
          borderTopColor: theme.border,
          paddingBottom: Math.max(insets.bottom, 12),
        },
      ]}>
      {state.routes.map((route, index) => {
        const options = descriptors[route.key]?.options;
        const label = options?.title ?? route.name;
        const active = state.index === index;
        const color = active ? theme.accent : theme.textSubtle;

        function onPress() {
          const event = navigation.emit({
            type: 'tabPress',
            target: route.key,
            canPreventDefault: true,
          });
          if (!active && !event.defaultPrevented) navigation.navigate(route.name, route.params);
        }

        return (
          <Pressable
            key={route.key}
            onPress={onPress}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={label}
            style={({ pressed }) => [styles.tab, { opacity: pressed ? 0.6 : 1 }]}>
            <View style={[styles.disc, active && { backgroundColor: theme.accentSoft }]}>
              <Icon name={ICONS[route.name] ?? 'more'} size={20} color={color} />
            </View>
            <Text variant="pill" color={color}>
              {label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 26,
    paddingTop: 8,
    borderTopWidth: 1,
  },
  tab: { alignItems: 'center', gap: 4, paddingHorizontal: 12, paddingVertical: 4, minWidth: 64 },
  disc: {
    width: 34,
    height: 26,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
