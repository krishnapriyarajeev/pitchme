import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { PlaybookUpload } from '@/components/playbook-upload';
import { Button } from '@/components/ui/button';
import { Screen } from '@/components/ui/screen';
import { StepPills } from '@/components/ui/step-pills';
import { Text } from '@/components/ui/text';
import { useAuth } from '@/hooks/use-auth';

/** Step 3 of 3: the company playbook. The last step ends onboarding. */
export default function PlaybookStep() {
  const { finishOnboarding } = useAuth();
  const [uploaded, setUploaded] = useState(false);

  return (
    <Screen scroll contentStyle={styles.content}>
      <Rise>
        <StepPills step={3} total={3} />
      </Rise>
      <Rise index={1} style={styles.intro}>
        <Text variant="title" accessibilityRole="header">
          Your company&apos;s playbook
        </Text>
        <Text variant="body" color="textSecondary" style={styles.subhead}>
          The debrief checks your answers against it: prices, claims and how you position against
          competitors. Without it, PitchMe can only judge how you answered, not whether it was
          right.
        </Text>
      </Rise>

      <Rise index={2} style={styles.block}>
        <PlaybookUpload onUploaded={() => setUploaded(true)} />
      </Rise>

      <Rise index={3} style={[styles.block, styles.actions]}>
        <Button label="Start rehearsing" disabled={!uploaded} onPress={finishOnboarding} />
        {uploaded ? null : (
          <Button label="Skip for now" variant="text" onPress={finishOnboarding} />
        )}
      </Rise>
      <View style={styles.after}>
        <Text variant="secondary" color="textSubtle" style={styles.centred}>
          You can add or replace it later on the Playbook tab.
        </Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 12, paddingBottom: 28 },
  intro: { marginTop: 18 },
  subhead: { marginTop: 8 },
  block: { marginTop: 20 },
  actions: { gap: 2 },
  after: { marginTop: 6 },
  centred: { textAlign: 'center' },
});
