import type { ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView, type Edge } from 'react-native-safe-area-context';

import { IconButton } from '@/components/ui/icon-button';
import { Text } from '@/components/ui/text';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useGoBack } from '@/hooks/use-go-back';
import { useTheme } from '@/hooks/use-theme';

type ScreenProps = {
  children: ReactNode;
  /** Put the content in a ScrollView. Off for screens fixed to the viewport. */
  scroll?: boolean;
  /** Apply the standard side margin. */
  gutter?: boolean;
  edges?: readonly Edge[];
  background?: string;
  contentStyle?: StyleProp<ViewStyle>;
  /** Drawn edge to edge behind the content, for glows or a camera feed. */
  backdrop?: ReactNode;
  /** Keep inputs above the keyboard. Use it on any screen with a text field. */
  keyboardAvoiding?: boolean;
  /** Fixed under the scroll area, for a main action that must stay in reach. */
  footer?: ReactNode;
};

/** The frame of every screen: safe area, background, margin and width. */
export function Screen({
  children,
  scroll = false,
  gutter = true,
  edges = ['top', 'bottom'],
  background,
  contentStyle,
  backdrop,
  keyboardAvoiding = false,
  footer,
}: ScreenProps) {
  const theme = useTheme();
  const frame = [styles.frame, gutter && styles.gutter];

  const body = scroll ? (
    <ScrollView
      style={styles.flex}
      contentContainerStyle={[frame, styles.scrollContent, contentStyle]}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}>
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.flex, frame, contentStyle]}>{children}</View>
  );

  const content = (
    <>
      {body}
      {footer ? (
        <View style={[styles.footer, frame, { borderTopColor: theme.border }]}>{footer}</View>
      ) : null}
    </>
  );

  return (
    <SafeAreaView
      edges={edges}
      style={[styles.flex, { backgroundColor: background ?? theme.background }]}>
      {backdrop}
      {keyboardAvoiding ? (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          {content}
        </KeyboardAvoidingView>
      ) : (
        content
      )}
    </SafeAreaView>
  );
}

type HeaderProps = {
  title?: string;
  subtitle?: string;
  /** A small line above the title, for example "New rehearsal". */
  eyebrow?: string;
  /** 'back' shows a chevron, 'close' an X. */
  leading?: 'back' | 'close' | 'none';
  onLeadingPress?: () => void;
  right?: ReactNode;
};

export function ScreenHeader({
  title,
  subtitle,
  eyebrow,
  leading = 'back',
  onLeadingPress,
  right,
}: HeaderProps) {
  const goBack = useGoBack();

  return (
    <View style={styles.header}>
      {leading !== 'none' ? (
        <IconButton
          name={leading === 'back' ? 'chevron-left' : 'close'}
          onPress={onLeadingPress ?? goBack}
          accessibilityLabel={leading === 'back' ? 'Go back' : 'Close'}
        />
      ) : null}
      <View style={styles.headerText}>
        {eyebrow ? (
          <Text variant="secondary" color="textSecondary">
            {eyebrow}
          </Text>
        ) : null}
        {title ? (
          <Text variant="rowTitle" numberOfLines={1} accessibilityRole="header">
            {title}
          </Text>
        ) : null}
        {subtitle ? (
          <Text variant="secondary" color="textSecondary">
            {subtitle}
          </Text>
        ) : null}
      </View>
      {right}
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  frame: { width: '100%', maxWidth: MaxContentWidth, alignSelf: 'center' },
  gutter: { paddingHorizontal: Spacing.gutter },
  scrollContent: { paddingBottom: Spacing.five },
  footer: { paddingTop: 16, paddingBottom: 18, borderTopWidth: 1 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 14, minHeight: 44 },
  headerText: { flex: 1, minWidth: 0, gap: 2 },
});
