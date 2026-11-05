import { useLocalSearchParams, useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { CallRoom } from '@/components/call/call-room';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { Camera } from '@/constants/theme';
import { forgetCall, pendingCall } from '@/lib/call-store';

/** The rehearsal call. The join token comes from memory, never the route. */
export default function Call() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  // Read once: the screen keeps the call even if its join window ends mid-call.
  const [call] = useState(() => pendingCall(id));

  // Ending runs twice: from the end button, then from the room's disconnect.
  const ended = useRef(false);

  function end() {
    if (ended.current) return;
    ended.current = true;
    forgetCall(id);
    router.replace(`/session/${id}`);
  }

  if (call) return <CallRoom call={call} onEnd={end} />;

  return (
    <View style={styles.root}>
      <Icon name="clock" size={26} color={Camera.textMuted} strokeWidth={1.5} />
      <Text variant="rowTitle" color={Camera.text} style={styles.centred}>
        This call can no longer be joined
      </Text>
      <Text variant="secondary" color={Camera.textMuted} style={styles.centred}>
        The buyer waits about two minutes for you to join. Start a new rehearsal when you are ready.
      </Text>
      <View style={styles.actions}>
        <Button label="Start a new rehearsal" onPress={() => router.replace('/prepare')} />
        <Button label="Go to Home" variant="text" onPress={() => router.replace('/home')} />
      </View>
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
  actions: { marginTop: 14, alignSelf: 'stretch', gap: 4 },
});
