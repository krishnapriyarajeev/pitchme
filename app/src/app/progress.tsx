import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { LineChart } from '@/components/charts/line-chart';
import { StatTile } from '@/components/charts/stat-tile';
import { GrowBar } from '@/components/motion/grow-bar';
import { Rise } from '@/components/motion/rise';
import { BandPill } from '@/components/ui/band-pill';
import { Card, CardDivider } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Screen, ScreenHeader } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { bandFor } from '@/constants/bands';
import { useBands } from '@/hooks/use-bands';
import { useRequest } from '@/hooks/use-request';
import { useTheme } from '@/hooks/use-theme';
import { getAnalysis, listSessions, messageOf } from '@/lib/api';
import { formatShortDate } from '@/lib/format';
import { averageDimensions, changeText, progressFrom } from '@/lib/progress';

/** The most rehearsals read for the trend. */
const LIMIT = 100;
/** Dimension averages come from the latest reviews only. */
const RECENT_REVIEWS = 5;
const TREND_POINTS = 10;

export default function ProgressScreen() {
  const router = useRouter();
  const theme = useTheme();
  const bands = useBands();
  const sessions = useRequest('sessions:progress', () => listSessions(LIMIT));
  const progress = sessions.data ? progressFrom(sessions.data) : null;
  const recentIds = progress?.scored.slice(-RECENT_REVIEWS).map((s) => s.id) ?? [];
  const reviews = useRequest(
    recentIds.length > 0 ? `progress:reviews:${recentIds.join(',')}` : null,
    async () => {
      const analyses = await Promise.all(recentIds.map((id) => getAnalysis(id)));
      return analyses.flatMap((a) => (a.result ? [a.result] : []));
    },
  );

  if (sessions.loading) return <Screen>{null}</Screen>;
  if (!progress) {
    return (
      <Screen>
        <ScreenHeader title="Progress" />
        <EmptyState
          icon="info"
          title="Your progress did not load"
          body={messageOf(sessions.error)}
          action={{ label: 'Try again', onPress: sessions.reload }}
        />
      </Screen>
    );
  }
  if (!progress.latest) {
    return (
      <Screen>
        <ScreenHeader title="Progress" />
        <EmptyState
          icon="chart"
          title="Your progress starts with your first review"
          body="Rehearse a call and review it. Each review adds a point here."
          action={{ label: 'Prepare for a call', onPress: () => router.replace('/prepare') }}
        />
      </Screen>
    );
  }

  const trend = progress.scored.slice(-TREND_POINTS);
  const dimensions = averageDimensions(reviews.data ?? []);

  return (
    <Screen scroll>
      <ScreenHeader title="Progress" subtitle="From your reviewed rehearsals" />

      <Rise style={styles.section}>
        <Card tone="hero">
          <View style={styles.headline}>
            <Text variant="numeral">{progress.latest.score}</Text>
            <View style={styles.headlineText}>
              <BandPill band={progress.latest.band} />
              <Text variant="secondary" color="textSecondary">
                Your latest score. {changeText(progress.sinceFirst, 'your first review')}
              </Text>
            </View>
          </View>
          {trend.length > 1 ? (
            <View style={styles.chart}>
              <LineChart
                points={trend.map((s, i) => ({ x: i, y: s.score }))}
                formatX={(i) => formatShortDate(trend[Math.round(i)]?.at ?? '')}
                formatY={(y) => `${Math.round(y)}`}
                summary={`Your last ${trend.length} scores, from ${trend[0]!.score} to ${progress.latest.score}.`}
              />
            </View>
          ) : (
            <Text variant="secondary" color="textSubtle" style={styles.chart}>
              Review one more rehearsal to see a trend.
            </Text>
          )}
          <Text variant="secondary" color="textSubtle" style={styles.note}>
            An audio-only review leaves out body language, so it can score differently from a review
            with video.
          </Text>
        </Card>
      </Rise>

      <Rise index={1} style={[styles.section, styles.tiles]}>
        <StatTile label="Rehearsals" value={String(progress.rehearsals)} detail="in total" />
        <StatTile label="Reviewed" value={String(progress.scored.length)} detail="with a score" />
        <StatTile
          label="Since last time"
          value={
            progress.sinceLast === null
              ? '–'
              : `${progress.sinceLast > 0 ? '+' : progress.sinceLast < 0 ? '−' : ''}${Math.abs(progress.sinceLast)}`
          }
          detail="points"
        />
      </Rise>

      {dimensions.length > 0 ? (
        <Rise index={2} style={styles.section}>
          <Text variant="rowTitle" style={styles.heading} accessibilityRole="header">
            Where you stand
          </Text>
          <Text variant="secondary" color="textSecondary" style={styles.sub}>
            The average of your last {Math.min(RECENT_REVIEWS, progress.scored.length)} reviews.
          </Text>
          <Card>
            {dimensions.map((d, i) => (
              <View key={d.name}>
                {i > 0 ? <CardDivider /> : null}
                <View style={styles.row}>
                  <Text variant="rowTitle">{d.label}</Text>
                  <Text variant="rowTitle">{d.score}</Text>
                </View>
                <GrowBar
                  value={d.score}
                  color={bands[bandFor(d.score)].bar}
                  trackColor={theme.accentSoft}
                  delay={i * 80}
                  style={styles.bar}
                />
              </View>
            ))}
          </Card>
        </Rise>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  section: { marginTop: 18 },
  headline: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  headlineText: { flex: 1, gap: 6 },
  chart: { marginTop: 16 },
  note: { marginTop: 10 },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  heading: { marginBottom: 2 },
  sub: { marginBottom: 10 },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  bar: { marginTop: 8 },
});
