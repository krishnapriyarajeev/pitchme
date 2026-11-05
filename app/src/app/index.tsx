import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { AmbientBackdrop } from '@/components/ui/ambient-backdrop';
import { Button } from '@/components/ui/button';
import { Logo } from '@/components/ui/logo';
import { Screen } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';

const GLOWS = [
  { cx: 40, cy: 120, r: 220, color: 'accent' },
  { cx: 360, cy: 620, r: 260, color: 'sage' },
] as const;

/** The first screen. Sign in and auto login come with onboarding. */
export default function Start() {
  const router = useRouter();

  return (
    <Screen backdrop={<AmbientBackdrop glows={GLOWS} />}>
      <View style={styles.centre}>
        <Logo size={72} animated />
        <Rise index={3}>
          <Text variant="display" style={styles.title}>
            PitchMe
          </Text>
        </Rise>
        <Rise index={4}>
          <Text variant="body" color="textSecondary" style={styles.tagline}>
            Have the meeting before the meeting.
          </Text>
        </Rise>
      </View>
      <Rise index={6} style={styles.footer}>
        <Button label="Start" onPress={() => router.replace('/home')} />
      </Rise>
    </Screen>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  title: { textAlign: 'center' },
  tagline: { textAlign: 'center' },
  footer: { paddingBottom: 12 },
});
