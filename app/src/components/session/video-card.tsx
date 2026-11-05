import { useVideoPlayer, VideoView } from 'expo-video';
import { StyleSheet, View } from 'react-native';

import { Card } from '@/components/ui/card';
import { Radius } from '@/constants/theme';

/**
 * A recording with the system's own controls. The address is presigned and
 * short-lived, so the parent passes the one it just loaded.
 */
export function VideoCard({ uri, label }: { uri: string; label: string }) {
  const player = useVideoPlayer(uri);

  return (
    <Card padded={false} style={styles.card}>
      <View style={styles.frame} accessible accessibilityLabel={label}>
        <VideoView
          player={player}
          style={StyleSheet.absoluteFill}
          contentFit="contain"
          nativeControls
          allowsPictureInPicture={false}
        />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { overflow: 'hidden', borderRadius: Radius.card },
  // The recording is portrait, 720 by 1280.
  frame: { width: '100%', aspectRatio: 9 / 16, maxHeight: 520, backgroundColor: '#000' },
});
