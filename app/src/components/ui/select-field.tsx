import { useState } from 'react';
import { LayoutAnimation, Pressable, StyleSheet, View } from 'react-native';

import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import type { Choice } from '@/constants/deal';
import { Radius } from '@/constants/theme';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { useTheme } from '@/hooks/use-theme';

type Props<K extends string> = {
  label: string;
  placeholder: string;
  options: readonly Choice<K>[];
  value: K | null;
  onChange: (value: K) => void;
  optional?: boolean;
};

/**
 * A picker that opens under the field, not in a sheet. The prepare screen
 * asks several of these in a row; in place, the answers already given stay
 * on screen.
 */
export function SelectField<K extends string>({
  label,
  placeholder,
  options,
  value,
  onChange,
  optional,
}: Props<K>) {
  const theme = useTheme();
  const reduced = useReducedMotion();
  const [open, setOpen] = useState(false);
  const selected = options.find((option) => option.key === value);

  function animate() {
    if (!reduced) LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
  }

  function pick(key: K) {
    animate();
    onChange(key);
    setOpen(false);
  }

  return (
    <View>
      <View style={styles.labelRow}>
        <Text variant="label">{label}</Text>
        {optional ? (
          <Text variant="secondary" color="textSubtle">
            Optional
          </Text>
        ) : null}
      </View>

      <Pressable
        onPress={() => {
          animate();
          setOpen((current) => !current);
        }}
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={`${label}: ${selected?.label ?? placeholder}`}
        style={[
          styles.field,
          {
            // A warm ground, not white: this is a place to choose, not to type.
            backgroundColor: theme.surfaceAlt,
            borderColor: open ? theme.accent : theme.border,
            borderWidth: open ? 1.5 : 1,
          },
        ]}>
        <Text variant="body" color={selected ? 'text' : 'placeholder'} style={styles.value}>
          {selected?.label ?? placeholder}
        </Text>
        <Icon name={open ? 'chevron-up' : 'chevron-down'} size={16} color={theme.textSubtle} />
      </Pressable>

      {open ? (
        <View
          accessibilityRole="radiogroup"
          style={[styles.list, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          {options.map((option) => {
            const active = option.key === value;
            return (
              <Pressable
                key={option.key}
                onPress={() => pick(option.key)}
                accessibilityRole="radio"
                accessibilityState={{ selected: active }}
                style={({ pressed }) => [
                  styles.item,
                  pressed && { backgroundColor: theme.surfaceAlt },
                ]}>
                <View
                  style={[
                    styles.radio,
                    { borderColor: active ? theme.accent : theme.borderStrong },
                    active && styles.radioOn,
                  ]}
                />
                <View style={styles.itemText}>
                  <Text variant="body">{option.label}</Text>
                  {option.hint ? (
                    <Text variant="secondary" color="textSubtle">
                      {option.hint}
                    </Text>
                  ) : null}
                </View>
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 7,
  },
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderRadius: Radius.control,
    paddingHorizontal: 14,
    minHeight: 48,
  },
  value: { flex: 1 },
  list: { marginTop: 6, borderWidth: 1, borderRadius: Radius.control, overflow: 'hidden' },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
    paddingHorizontal: 14,
    paddingVertical: 10,
    minHeight: 46,
  },
  radio: { width: 18, height: 18, borderRadius: 9, borderWidth: 1.5 },
  radioOn: { borderWidth: 6 },
  itemText: { flex: 1 },
});
