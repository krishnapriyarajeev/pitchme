import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { VoicePrivacy } from '@/components/voice-privacy';
import { VoiceRecorder } from '@/components/voice-recorder';
import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { Screen, ScreenHeader } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { useGoBack } from '@/hooks/use-go-back';
import { useRequest } from '@/hooks/use-request';
import { useVoiceUpload } from '@/hooks/use-voice-upload';
import { getProfile } from '@/lib/api';
import { voicePassage } from '@/lib/voice';

/** A new voice sample, from Profile. It replaces the old sample and clone. */
export default function VoiceSample() {
  const goBack = useGoBack('/profile');
  const profile = useRequest('profile', getProfile);
  const upload = useVoiceUpload();
  const [take, setTake] = useState<{ uri: string } | null>(null);

  async function save() {
    if (take && (await upload.save(take.uri))) goBack();
  }

  return (
    <Screen
      scroll
      footer={
        <Button label="Save sample" disabled={!take} loading={upload.saving} onPress={save} />
      }>
      <ScreenHeader title="Your voice sample" />
      <Text variant="body" color="textSecondary" style={styles.block}>
        A new sample replaces the one you have, and PitchMe makes a new voice clone from it.
      </Text>

      <View style={styles.block}>
        <VoiceRecorder
          passage={voicePassage(profile.data)}
          onTake={setTake}
          disabled={upload.saving}
        />
      </View>

      {upload.error ? (
        <View style={styles.block}>
          <Callout tone="attention" icon="info">
            <Text variant="secondary" accessibilityLiveRegion="polite">
              {upload.error} Your take is still here.
            </Text>
          </Callout>
        </View>
      ) : null}

      <View style={styles.block}>
        <VoicePrivacy />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  block: { marginTop: 18 },
});
