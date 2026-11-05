import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { Spinner } from '@/components/motion/spinner';
import { ReviewChoice } from '@/components/session/review-choice';
import { ReviewProgress } from '@/components/session/review-progress';
import { Transcript } from '@/components/session/transcript';
import { VideoCard } from '@/components/session/video-card';
import { BandPill } from '@/components/ui/band-pill';
import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { ScoreRing } from '@/components/ui/score-ring';
import { Screen, ScreenHeader } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { bandFor } from '@/constants/bands';
import { useBands } from '@/hooks/use-bands';
import { useRefreshOnFocus } from '@/hooks/use-refresh-on-focus';
import { useRequest } from '@/hooks/use-request';
import { useTheme } from '@/hooks/use-theme';
import { getAnalysis, getSession, messageOf } from '@/lib/api';
import { isSettling, rehearsalState, sessionMeta, sessionTitle, STATE_TEXT } from '@/lib/sessions';

const POLL_MS = 3000;

/**
 * One rehearsal: where it stands, the next step, the recording and the
 * transcript. Everything here comes from the API and updates on its own
 * while the call closes or the review runs.
 */
export default function Rehearsal() {
  const router = useRouter();
  const theme = useTheme();
  const bands = useBands();
  const { id } = useLocalSearchParams<{ id: string }>();

  const session = useRequest(`session:${id}`, () => getSession(id), {
    pollMs: POLL_MS,
    keepPolling: (data) => !data || isSettling(rehearsalState(data)),
  });
  useRefreshOnFocus(session.reload);
  const data = session.data;
  const state = data ? rehearsalState(data) : null;
  // The review's stage and result live on the analysis, not the session.
  const reviewing = state === 'analysing' || state === 'analysis_failed' || state === 'debrief';
  const analysis = useRequest(reviewing ? `analysis:${id}` : null, () => getAnalysis(id), {
    pollMs: POLL_MS,
    keepPolling: (data) => !data || data.status === 'queued' || data.status === 'running',
  });

  if (session.loading) return <Screen>{null}</Screen>;
  if (!data) {
    return (
      <Screen>
        <ScreenHeader title="Rehearsal" />
        <EmptyState
          icon="info"
          title="This rehearsal did not load"
          body={messageOf(session.error)}
          action={{ label: 'Try again', onPress: session.reload }}
        />
      </Screen>
    );
  }

  const score = data.overall_score;
  const band = state === 'debrief' && score !== null ? bandFor(score) : null;

  return (
    <Screen
      scroll
      footer={
        <Button
          label="Rehearse again"
          variant="secondary"
          onPress={() => router.push('/prepare')}
        />
      }>
      <ScreenHeader title={sessionTitle(data)} subtitle={sessionMeta(data)} />

      <Rise style={styles.section}>
        {state === 'debrief' && score !== null && band ? (
          <Card style={styles.score}>
            <ScoreRing
              score={score}
              color={bands[band].bar}
              trackColor={theme.accentSoft}
              size={64}
              strokeWidth={6}>
              <Text variant="numeralSmall">{Math.round(score)}</Text>
            </ScoreRing>
            <View style={styles.scoreText}>
              <BandPill band={band} />
              <Text variant="body" numberOfLines={3}>
                {analysis.data?.result?.summary || STATE_TEXT.debrief}
              </Text>
            </View>
          </Card>
        ) : state === 'waiting' || state === 'live' ? (
          <Card style={styles.row}>
            <Spinner size={22} color={theme.accent} trackColor={theme.accentSoft} />
            <Text variant="body" style={styles.flex}>
              {state === 'live'
                ? 'Saving your call. This takes a few seconds after it ends.'
                : STATE_TEXT.waiting}
            </Text>
          </Card>
        ) : state === 'analysing' ? (
          <ReviewProgress status={analysis.data ?? { status: data.analysis_status, stage: null }} />
        ) : (
          <Callout icon="info" tone={state === 'ready' ? 'positive' : 'quiet'}>
            <Text variant="body">{state ? STATE_TEXT[state] : ''}</Text>
            {state === 'analysis_failed' && analysis.data?.error ? (
              <Text variant="secondary" color="textSecondary" style={styles.reason}>
                {analysis.data.error}
              </Text>
            ) : null}
          </Callout>
        )}
      </Rise>

      {state === 'debrief' ? (
        <Rise index={1} style={styles.section}>
          <Button
            label="See the full debrief"
            icon="chevron-right"
            iconTrailing
            onPress={() => router.push(`/debrief/${id}`)}
          />
        </Rise>
      ) : null}

      {state === 'ready' || state === 'analysis_failed' ? (
        <Rise index={1} style={styles.section}>
          <Text variant="rowTitle" style={styles.heading} accessibilityRole="header">
            {state === 'ready' ? 'How should PitchMe review it?' : 'Run the review again'}
          </Text>
          <ReviewChoice
            sessionId={id}
            onStarted={() => {
              void session.reload();
              void analysis.reload();
            }}
          />
        </Rise>
      ) : null}

      {data.recording_url ? (
        <Rise index={2} style={styles.section}>
          <Text variant="rowTitle" style={styles.heading} accessibilityRole="header">
            Your recording
          </Text>
          <VideoCard uri={data.recording_url} label="Recording of your rehearsal" />
        </Rise>
      ) : null}

      {data.transcript.length > 0 ? (
        <Rise index={3} style={styles.section}>
          <Text variant="rowTitle" style={styles.heading} accessibilityRole="header">
            Transcript
          </Text>
          <Transcript turns={data.transcript} buyer={data.prospect_name} />
        </Rise>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  section: { marginTop: 18 },
  heading: { marginBottom: 10 },
  score: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  scoreText: { flex: 1, gap: 6 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  flex: { flex: 1 },
  reason: { marginTop: 6 },
});
