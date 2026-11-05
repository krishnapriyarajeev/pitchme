import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { Camera } from '@/constants/theme';
import type { PendingCall } from '@/lib/call-store';

/**
 * The live call needs native WebRTC, so the web build has no call room.
 * The rehearsal stays on the account; the buyer reports a no-show.
 */
export function CallRoom({ onEnd }: { call: PendingCall; onEnd: () => void }) {
  return (
    <View style={styles.root}>
      <Icon name="video" size={28} color={Camera.textMuted} strokeWidth={1.5} />
      <Text variant="rowTitle" color={Camera.text} style={styles.centred}>
        The call runs in the PitchMe app
      </Text>
      <Text variant="secondary" color={Camera.textMuted} style={styles.centred}>
        Live calls need the phone app. Open PitchMe on your phone and start a rehearsal there.
      </Text>
      <Button label="Back" variant="secondary" onPress={onEnd} style={styles.back} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: 32,
    backgroundColor: Camera.bottom,
  },
  centred: { textAlign: 'center', maxWidth: 320 },
  back: { marginTop: 12, alignSelf: 'stretch' },
});
