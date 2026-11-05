import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { VoicePrivacy } from '@/components/voice-privacy';
import { VoiceRecorder } from '@/components/voice-recorder';
import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { Screen } from '@/components/ui/screen';
import { StepPills } from '@/components/ui/step-pills';
import { Text } from '@/components/ui/text';
import { useAuth } from '@/hooks/use-auth';
import { useRequest } from '@/hooks/use-request';
import { useVoiceUpload } from '@/hooks/use-voice-upload';
import { getProfile } from '@/lib/api';
import { TARGET_SECONDS, voicePassage } from '@/lib/voice';

/** Step 2 of 3: a short voice sample, for answers in the user's own voice. */
export default function VoiceStep() {
  const { notice, clearNotice, finishOnboarding } = useAuth();
  const profile = useRequest('profile', getProfile);
  const upload = useVoiceUpload();
  const [take, setTake] = useState<{ uri: string } | null>(null);

  function next() {
    clearNotice();
    finishOnboarding();
  }

  async function save() {
    if (!take) return;
    if (await upload.save(take.uri)) next();
  }

  return (
    <Screen
      scroll
      contentStyle={styles.content}
      footer={
        <View style={styles.footer}>
          <Button
            label="Save and continue"
            disabled={!take}
            loading={upload.saving}
            onPress={save}
          />
          <Button label="Skip for now" variant="text" disabled={upload.saving} onPress={next} />
        </View>
      }>
      <Rise>
        <StepPills step={2} total={3} />
      </Rise>
      <Rise index={1} style={styles.intro}>
        <Text variant="title" accessibilityRole="header">
          Record your voice
        </Text>
        <Text variant="body" color="textSecondary" style={styles.subhead}>
          Read the text below in your normal voice, for about {TARGET_SECONDS} seconds. After the
          call, PitchMe plays stronger answers back to you in this voice.
        </Text>
      </Rise>

      {notice ? (
        <View style={styles.block}>
          <Callout icon="info">
            <Text variant="secondary">{notice}</Text>
          </Callout>
        </View>
      ) : null}

      <Rise index={2} style={styles.block}>
        <VoiceRecorder
          passage={voicePassage(profile.data)}
          onTake={setTake}
          disabled={upload.saving}
        />
      </Rise>

      {upload.error ? (
        <View style={styles.block}>
          <Callout tone="attention" icon="info">
            <Text variant="secondary" accessibilityLiveRegion="polite">
              {upload.error} Your take is still here.
            </Text>
          </Callout>
        </View>
      ) : null}

      <Rise index={3} style={styles.block}>
        <VoicePrivacy />
      </Rise>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 12, paddingBottom: 20 },
  intro: { marginTop: 18 },
  subhead: { marginTop: 8 },
  block: { marginTop: 18 },
  footer: { gap: 2 },
});
