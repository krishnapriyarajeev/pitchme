import { useState, type Ref } from 'react';
import {
  StyleSheet,
  TextInput,
  View,
  type StyleProp,
  type TextInputProps,
  type ViewStyle,
} from 'react-native';

import { IconButton } from '@/components/ui/icon-button';
import { Text } from '@/components/ui/text';
import { Fonts } from '@/constants/fonts';
import { Radius } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type Props = Omit<TextInputProps, 'style'> & {
  ref?: Ref<TextInput>;
  label?: string;
  optional?: boolean;
  helper?: string;
  /** What to change, shown under the field in place of the helper. */
  error?: string | null;
  /** A password field: dots, and a button to show the text. */
  secure?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function TextField({
  ref,
  label,
  optional,
  helper,
  error,
  secure,
  multiline,
  style,
  ...input
}: Props) {
  const theme = useTheme();
  const [focused, setFocused] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const outline = error ? theme.terra : focused ? theme.accent : theme.border;

  return (
    <View style={[styles.wrap, style]}>
      {label ? (
        <View style={styles.labelRow}>
          <Text variant="label">{label}</Text>
          {optional ? (
            <Text variant="secondary" color="textSubtle">
              Optional
            </Text>
          ) : null}
        </View>
      ) : null}

      <View
        style={[
          styles.field,
          multiline && styles.multiline,
          {
            backgroundColor: theme.surface,
            borderColor: outline,
            borderWidth: focused || error ? 1.5 : 1,
          },
        ]}>
        <TextInput
          ref={ref}
          accessibilityLabel={label}
          {...input}
          multiline={multiline}
          secureTextEntry={secure && !revealed}
          placeholderTextColor={theme.placeholder}
          onFocus={(event) => {
            setFocused(true);
            input.onFocus?.(event);
          }}
          onBlur={(event) => {
            setFocused(false);
            input.onBlur?.(event);
          }}
          style={[styles.input, multiline && styles.inputMultiline, { color: theme.text }]}
        />
        {secure ? (
          <IconButton
            name={revealed ? 'eye-off' : 'eye'}
            size={20}
            color={theme.textSubtle}
            onPress={() => setRevealed((value) => !value)}
            accessibilityLabel={revealed ? 'Hide password' : 'Show password'}
          />
        ) : null}
      </View>

      {error ? (
        <Text variant="secondary" color="terraText" accessibilityLiveRegion="polite">
          {error}
        </Text>
      ) : helper ? (
        <Text variant="secondary" color="textSubtle">
          {helper}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 7 },
  labelRow: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' },
  field: {
    height: 52,
    borderRadius: Radius.control,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  multiline: { height: undefined, minHeight: 76, alignItems: 'flex-start', paddingVertical: 14 },
  input: { flex: 1, fontFamily: Fonts.sans, fontSize: 16, padding: 0 },
  inputMultiline: { lineHeight: 22, textAlignVertical: 'top' },
});
