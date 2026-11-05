import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { GlowRing } from '@/components/motion/glow-ring';
import { Rise } from '@/components/motion/rise';
import { ServerStatus } from '@/components/server-status';
import { AmbientBackdrop } from '@/components/ui/ambient-backdrop';
import { Button } from '@/components/ui/button';
import { Icon, type IconName } from '@/components/ui/icon';
import { Logo } from '@/components/ui/logo';
import { Screen } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';

const LOGO_SIZE = 96;

const GLOWS = [
  { cx: 60, cy: 40, r: 190, color: 'accent' },
  { cx: 360, cy: 420, r: 180, color: 'sage' },
] as const;

/** The outcome first, then the part of the app that gives it. */
const PROMISES: { icon: IconName; title: string; detail: string }[] = [
  {
    icon: 'user',
    title: 'Meet the buyer before the real call',
    detail: 'An AI buyer set up for your deal',
  },
  {
    icon: 'shield-check',
    title: 'Find a wrong claim before the prospect does',
    detail: 'Answers checked against your playbook',
  },
  {
    icon: 'message',
    title: 'Practise the hard questions first',
    detail: 'Objections, with stronger answers in your own voice',
  },
];

/** The first screen when signed out. A saved sign-in skips it. */
export default function Landing() {
  const theme = useTheme();
  const router = useRouter();

  return (
    <Screen scroll backdrop={<AmbientBackdrop glows={GLOWS} />} contentStyle={styles.content}>
      <View style={styles.logo}>
        <GlowRing size={LOGO_SIZE} color={theme.accent} duration={3400} />
        <Logo size={LOGO_SIZE} animated />
      </View>

      <Rise index={5}>
        <Text variant="display" style={styles.headline} accessibilityRole="header">
          Have the meeting{'\n'}before the meeting
        </Text>
      </Rise>
      <Rise index={6}>
        <Text variant="body" color="textSecondary" style={styles.subhead}>
          Practise your next sales call with a buyer who knows your deal, your product and your
          competitor. Then see what to change before the real one.
        </Text>
      </Rise>

      <View style={styles.spacer} />

      <Rise index={7} style={styles.promises}>
        {PROMISES.map((promise) => (
          <View key={promise.title} style={styles.promise}>
            <View style={[styles.promiseIcon, { backgroundColor: theme.accentSoft }]}>
              <Icon name={promise.icon} size={17} color={theme.accent} strokeWidth={1.5} />
            </View>
            <View style={styles.promiseText}>
              <Text variant="rowTitle">{promise.title}</Text>
              <Text variant="secondary" color="textSecondary">
                {promise.detail}
              </Text>
            </View>
          </View>
        ))}
      </Rise>

      <Rise index={9} style={styles.actions}>
        <ServerStatus />
        <Button
          label="Get started"
          icon="chevron-right"
          iconTrailing
          onPress={() => router.push('/onboard')}
        />
        <Button
          label="I already have an account"
          variant="text"
          onPress={() => router.push('/login')}
        />
      </Rise>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, paddingTop: 30, paddingBottom: 12 },
  logo: { width: LOGO_SIZE, height: LOGO_SIZE, alignItems: 'center', justifyContent: 'center' },
  headline: { marginTop: 28 },
  subhead: { marginTop: 14, fontSize: 16, lineHeight: 24 },
  spacer: { flex: 1, minHeight: 20 },
  promises: { gap: 14 },
  promise: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  promiseIcon: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  promiseText: { flex: 1, gap: 1 },
  actions: { marginTop: 24, gap: 8 },
});
