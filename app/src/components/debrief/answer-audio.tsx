import { useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';
import { Pressable, StyleSheet, View } from 'react-native';

import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';
import { formatClock } from '@/lib/format';

/**
 * The stronger answer in the user's own voice. The first version printed
 * the player's seconds as if they were milliseconds.
 */
export function AnswerAudio({ uri }: { uri: string }) {
  const theme = useTheme();
  const player = useAudioPlayer(uri);
  const status = useAudioPlayerStatus(player);

  function toggle() {
    if (status.playing) {
      player.pause();
      return;
    }
    if (status.duration > 0 && status.currentTime >= status.duration) player.seekTo(0);
    player.play();
  }

  return (
    <View style={[styles.bar, { backgroundColor: theme.surface }]}>
      <Pressable
        onPress={toggle}
        accessibilityRole="button"
        accessibilityLabel={status.playing ? 'Pause' : 'Play the stronger answer in your voice'}
        style={[styles.play, { backgroundColor: theme.sageDeep }]}>
        <Icon name={status.playing ? 'pause' : 'play'} size={12} color="#FFFFFF" />
      </Pressable>
      <Text variant="secondary" color="textSecondary" style={styles.text}>
        In your voice
      </Text>
      <Text variant="secondary" color="textSecondary">
        {formatClock(status.currentTime)} / {formatClock(status.duration)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 10,
  },
  play: { width: 30, height: 30, borderRadius: 15, alignItems: 'center', justifyContent: 'center' },
  text: { flex: 1 },
});
