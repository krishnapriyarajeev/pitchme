import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { Breathe } from '@/components/motion/breathe';
import { Rise } from '@/components/motion/rise';
import { ReadinessCard } from '@/components/readiness-card';
import { SessionRow } from '@/components/session-row';
import { EmptyState } from '@/components/ui/empty-state';
import { Icon } from '@/components/ui/icon';
import { Screen } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { Radius } from '@/constants/theme';
import { useRefreshOnFocus } from '@/hooks/use-refresh-on-focus';
import { useRequest } from '@/hooks/use-request';
import { useTheme } from '@/hooks/use-theme';
import { listSessions, messageOf } from '@/lib/api';
import { progressFrom } from '@/lib/progress';
import { isSettling, rehearsalState } from '@/lib/sessions';

const RECENT = 5;
const POLL_MS = 5000;

export default function HomeTab() {
  const theme = useTheme();
  const router = useRouter();
  // One more than shown, to know whether "See all" has more to show.
  const recent = useRequest('sessions:recent', () => listSessions(RECENT + 1), {
    pollMs: POLL_MS,
    // A call or a review in progress updates on its own.
    keepPolling: (items) => !!items?.some((s) => isSettling(rehearsalState(s))),
  });
  useRefreshOnFocus(recent.reload);
  const items = recent.data ?? [];
  // The latest score; Progress reads the full history.
  const progress = progressFrom(items);

  return (
    <Screen scroll edges={['top']} contentStyle={styles.content}>
      <Rise>
        <Text variant="title" accessibilityRole="header">
          Ready when you are
        </Text>
      </Rise>

      <Rise index={1} style={styles.cta}>
        <Breathe>
          <Pressable
            onPress={() => router.push('/prepare')}
            accessibilityRole="button"
            accessibilityLabel="Prepare for your next call"
            style={({ pressed }) => [
              styles.ctaCard,
              { backgroundColor: theme.accent, opacity: pressed ? 0.9 : 1 },
            ]}>
            <View style={[styles.ctaGlow, { backgroundColor: theme.sage }]} />
            <View style={[styles.ctaIcon, { backgroundColor: theme.onAccent }]}>
              <Icon name="mic" size={19} color={theme.accent} strokeWidth={1.8} />
            </View>
            <View style={styles.ctaText}>
              <Text variant="cardTitle" color="onAccent" style={styles.ctaTitle}>
                Prepare for your next call
              </Text>
              <Text variant="secondary" color="onAccent" style={styles.ctaDetail}>
                Set up the deal, then talk it through with the buyer
              </Text>
            </View>
          </Pressable>
        </Breathe>
      </Rise>

      {progress.latest ? (
        <Rise index={2} style={styles.readiness}>
          <ReadinessCard progress={progress} onPress={() => router.push('/progress')} />
        </Rise>
      ) : null}

      <Rise index={2} style={styles.sectionHead}>
        <Text variant="rowTitle" accessibilityRole="header">
          Recent rehearsals
        </Text>
        {items.length > RECENT ? (
          <Pressable
            onPress={() => router.push('/sessions')}
            accessibilityRole="button"
            accessibilityLabel="See all rehearsals"
            hitSlop={12}>
            <Text variant="label" color="accent">
              See all
            </Text>
          </Pressable>
        ) : null}
      </Rise>

      {recent.loading ? null : recent.error && !recent.data ? (
        <EmptyState
          icon="info"
          title="Your rehearsals did not load"
          body={messageOf(recent.error)}
          action={{ label: 'Try again', onPress: recent.reload }}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon="video"
          title="Nothing here yet"
          body="The first one always feels stiff. That is why it belongs here, not on the real call."
        />
      ) : (
        <View style={styles.list}>
          {items.slice(0, RECENT).map((session, i) => (
            <Rise key={session.session_id} index={3 + i}>
              <SessionRow
                session={session}
                onPress={() => router.push(`/session/${session.session_id}`)}
              />
            </Rise>
          ))}
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 12 },
  cta: { marginTop: 18 },
  ctaCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 13,
    borderRadius: Radius.card,
    padding: 17,
    overflow: 'hidden',
  },
  ctaGlow: {
    position: 'absolute',
    right: -30,
    top: -30,
    width: 110,
    height: 110,
    borderRadius: 55,
    opacity: 0.25,
  },
  ctaIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaText: { flex: 1, minWidth: 0 },
  ctaTitle: { fontSize: 19, lineHeight: 24 },
  ctaDetail: { marginTop: 2, opacity: 0.75 },
  readiness: { marginTop: 12 },
  sectionHead: {
    marginTop: 26,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  list: { marginTop: 12, gap: 10 },
});
