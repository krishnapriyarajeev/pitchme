import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { BulletList } from '@/components/debrief/bullet-list';
import { DeliveryCharts } from '@/components/debrief/delivery-charts';
import { DeliveryFindings } from '@/components/debrief/delivery-findings';
import { Dimensions } from '@/components/debrief/dimensions';
import { Integrity } from '@/components/debrief/integrity';
import { Media } from '@/components/debrief/media';
import { ObjectionCard } from '@/components/debrief/objection-card';
import { ScoreHeader } from '@/components/debrief/score-header';
import { Section } from '@/components/debrief/section';
import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { EmptyState } from '@/components/ui/empty-state';
import { Screen, ScreenHeader } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { useRequest } from '@/hooks/use-request';
import { getAnalysis, getProfile, getSession, messageOf, readMetrics } from '@/lib/api';
import { deliveryFindings, integrityIssues, objections } from '@/lib/debrief';
import { sessionMeta, sessionTitle } from '@/lib/sessions';

/**
 * The debrief, in sections, from the API's result only. When the result
 * does not load, it says what went wrong and offers to try again.
 */
export default function Debrief() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const session = useRequest(`session:${id}`, () => getSession(id));
  const analysis = useRequest(`analysis:${id}`, () => getAnalysis(id));
  const profile = useRequest('profile', getProfile);

  if (session.loading || analysis.loading) return <Screen>{null}</Screen>;

  const result = analysis.data?.result;
  if (!session.data || !result) {
    const loadError = session.error ?? analysis.error;
    return (
      <Screen>
        <ScreenHeader title="Debrief" />
        {loadError ? (
          <EmptyState
            icon="info"
            title="Your debrief did not load"
            body={messageOf(loadError)}
            action={{
              label: 'Try again',
              onPress: () => {
                void session.reload();
                void analysis.reload();
              },
            }}
          />
        ) : (
          <EmptyState
            icon="clock"
            title="This debrief is not ready"
            body="The review has not finished. The rehearsal's page shows where it stands."
            action={{
              label: 'Open the rehearsal',
              onPress: () => router.replace(`/session/${id}`),
            }}
          />
        )}
      </Screen>
    );
  }

  const items = objections(result);
  const issues = integrityIssues(items);
  const delivery = deliveryFindings(result.findings);
  const metrics = readMetrics(result.metrics);
  const hasVoice = profile.data?.voice_clone_status === 'ready';

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
      <ScreenHeader
        eyebrow="Debrief"
        title={sessionTitle(session.data)}
        subtitle={sessionMeta(session.data)}
      />

      <Rise style={styles.top}>
        <ScoreHeader result={result} />
      </Rise>

      {result.notes.length > 0 ? (
        <Rise index={1} style={styles.top}>
          <Callout icon="info">
            {result.notes.map((note) => (
              <Text key={note} variant="secondary">
                {note}
              </Text>
            ))}
          </Callout>
        </Rise>
      ) : null}

      <Section label="Where you stand" index={2}>
        <Dimensions dimensions={result.dimensions} />
      </Section>

      {issues.length > 0 ? (
        <Section
          label={`Pitch integrity · ${issues.length} to fix`}
          title="Check these before the real call"
          tone="terra"
          index={3}>
          <Integrity items={issues} />
        </Section>
      ) : null}

      {result.strengths.length > 0 ? (
        <Section label="What went well" tone="sageText" index={4}>
          <BulletList items={result.strengths} icon="check-circle" />
        </Section>
      ) : null}

      {items.length > 0 ? (
        <Section label="Questions and objections" title="How you answered" index={5}>
          {items.map((item, i) => (
            <ObjectionCard
              key={`${item.question}-${i}`}
              item={item}
              startOpen={i === 0 && item.verdict !== 'handled'}
              hasVoice={hasVoice}
            />
          ))}
        </Section>
      ) : null}

      {session.data.recording_url || result.annotated_video_url ? (
        <Section label="Your call" title="Watch it back" index={6}>
          <Media
            recordingUrl={session.data.recording_url}
            annotatedUrl={result.annotated_video_url}
          />
        </Section>
      ) : null}

      {delivery.length > 0 ? (
        <Section label="Delivery" title="How you came across" index={7}>
          <DeliveryFindings findings={delivery} />
        </Section>
      ) : null}

      <Section label="The numbers" index={8}>
        <DeliveryCharts metrics={metrics} />
      </Section>

      {result.prep_list.length > 0 ? (
        <Section label="Your prep list" title="Before the real call" index={9}>
          <BulletList items={result.prep_list} icon="check" />
        </Section>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  top: { marginTop: 18 },
});
