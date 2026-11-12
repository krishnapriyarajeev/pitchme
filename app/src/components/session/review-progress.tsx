import { StyleSheet, View } from 'react-native';

import { Spinner } from '@/components/motion/spinner';
import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';
import type { AnalysisStatus } from '@/lib/api';
import { REVIEW_STAGES, stageStates } from '@/lib/review';

/**
 * The review's stages as the job reports them. Nothing moves on a timer.
 */
export function ReviewProgress({ status }: { status: Pick<AnalysisStatus, 'status' | 'stage'> }) {
  const theme = useTheme();
  const states = stageStates(status);

  return (
    <Card>
      <View style={styles.head}>
        <Spinner size={22} color={theme.accent} trackColor={theme.accentSoft} />
        <Text variant="rowTitle">
          {status.status === 'queued' ? 'Waiting for a free reviewer' : 'Reviewing your call'}
        </Text>
      </View>
      <View style={styles.stages}>
        {REVIEW_STAGES.map((stage, i) => {
          const state = states[i];
          return (
            <View
              key={stage.key}
              style={styles.stage}
              accessible
              accessibilityLabel={`${stage.label}: ${state === 'done' ? 'done' : state === 'active' ? 'now' : 'next'}`}>
              <View
                style={[
                  styles.mark,
                  state === 'done' && { backgroundColor: theme.sageSoft, borderColor: theme.sage },
                  state === 'active' && {
                    backgroundColor: theme.accentSoft,
                    borderColor: theme.accent,
                  },
                  state === 'pending' && {
                    backgroundColor: theme.surfaceAlt,
                    borderColor: theme.border,
                  },
                ]}>
                {state === 'done' ? (
                  <Icon name="check" size={11} color={theme.sageDeep} strokeWidth={2.4} />
                ) : state === 'active' ? (
                  <View style={[styles.dot, { backgroundColor: theme.accent }]} />
                ) : null}
              </View>
              <Text variant="body" color={state === 'active' ? 'text' : 'textSubtle'}>
                {stage.label}
              </Text>
            </View>
          );
        })}
      </View>
      <Text variant="secondary" color="textSubtle" style={styles.note}>
        This takes a minute or two. You can leave this page; the review goes on.
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  stages: { marginTop: 16, gap: 12 },
  stage: { flexDirection: 'row', alignItems: 'center', gap: 11 },
  mark: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  note: { marginTop: 14 },
});
