import type { ReactNode } from 'react';
import { Modal, Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button } from '@/components/ui/button';
import { Text } from '@/components/ui/text';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type Props = {
  visible: boolean;
  title: string;
  body: string;
  confirmLabel: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  /** Busy state for the confirm button while its action runs. */
  confirming?: boolean;
  children?: ReactNode;
};

/**
 * A confirmation in our own style, in place of Alert.alert, which does
 * nothing on the web.
 */
export function ConfirmSheet({
  visible,
  title,
  body,
  confirmLabel,
  cancelLabel = 'Not now',
  onConfirm,
  onCancel,
  confirming = false,
  children,
}: Props) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();

  // Unmounted, not hidden: on the web a Modal with visible={false} can stay
  // on screen.
  if (!visible) return null;

  return (
    <Modal visible transparent animationType="fade" onRequestClose={onCancel}>
      <View style={styles.root}>
        <Pressable
          style={styles.scrim}
          onPress={onCancel}
          accessibilityRole="button"
          accessibilityLabel="Close"
        />
        <View
          accessibilityViewIsModal
          style={[
            styles.sheet,
            {
              backgroundColor: theme.background,
              borderColor: theme.border,
              paddingBottom: Math.max(insets.bottom, 20),
            },
          ]}>
          <View style={[styles.grabber, { backgroundColor: theme.border }]} />
          <Text variant="cardTitle" accessibilityRole="header">
            {title}
          </Text>
          <Text variant="body" color="textSecondary" style={styles.body}>
            {body}
          </Text>
          {children}
          <View style={styles.actions}>
            <Button label={confirmLabel} onPress={onConfirm} loading={confirming} />
            <Button label={cancelLabel} variant="text" onPress={onCancel} disabled={confirming} />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, justifyContent: 'flex-end' },
  scrim: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'rgba(26,20,26,0.45)',
  },
  sheet: {
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    borderTopWidth: 1,
    paddingHorizontal: Spacing.gutter,
    paddingTop: 12,
  },
  grabber: {
    width: 40,
    height: 4,
    borderRadius: Radius.pill,
    alignSelf: 'center',
    marginBottom: 20,
  },
  body: { marginTop: 10 },
  actions: { marginTop: 22, gap: 6 },
});
