import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { VideoCard } from '@/components/session/video-card';
import { Button } from '@/components/ui/button';

type Props = { recordingUrl: string | null; annotatedUrl: string | null };

/**
 * The call as recorded, or with the posture and voice notes drawn on it.
 * Both addresses are presigned on every load; neither is ever stored.
 */
export function Media({ recordingUrl, annotatedUrl }: Props) {
  const [annotated, setAnnotated] = useState(annotatedUrl !== null);
  const uri = annotated ? annotatedUrl : recordingUrl;

  return (
    <View style={styles.wrap}>
      {recordingUrl && annotatedUrl ? (
        <View style={styles.switch} accessibilityRole="tablist">
          <Button
            label="With notes"
            variant={annotated ? 'quiet' : 'text'}
            onPress={() => setAnnotated(true)}
            style={styles.tab}
          />
          <Button
            label="As recorded"
            variant={annotated ? 'text' : 'quiet'}
            onPress={() => setAnnotated(false)}
            style={styles.tab}
          />
        </View>
      ) : null}
      {uri ? (
        <VideoCard
          key={uri}
          uri={uri}
          label={annotated ? 'Your call with notes drawn on it' : 'Recording of your call'}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 10 },
  switch: { flexDirection: 'row', gap: 8 },
  tab: { flex: 1, height: 40 },
});
