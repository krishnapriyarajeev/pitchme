import { Pressable, StyleSheet, View } from 'react-native';

import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { ScoreRing } from '@/components/ui/score-ring';
import { Text } from '@/components/ui/text';
import { useBands } from '@/hooks/use-bands';
import { useTheme } from '@/hooks/use-theme';
import { changeText, type Progress } from '@/lib/progress';

/** The latest score with its band, and a way into Progress. */
export function ReadinessCard({ progress, onPress }: { progress: Progress; onPress: () => void }) {
  const theme = useTheme();
  const bands = useBands();
  const latest = progress.latest;
  if (!latest) return null;
  const change = changeText(progress.sinceLast, 'last time');

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`Your latest score, ${latest.score}. ${change}. See your progress.`}
      style={({ pressed }) => ({ opacity: pressed ? 0.85 : 1 })}>
      <Card style={styles.card}>
        <ScoreRing
          score={latest.score}
          color={bands[latest.band].bar}
          trackColor={theme.accentSoft}
          size={44}
          strokeWidth={4}>
          <Text variant="pill">{latest.score}</Text>
        </ScoreRing>
        <View style={styles.text}>
          <Text variant="rowTitle">Your latest score</Text>
          <Text variant="secondary" color="textSecondary">
            {[bands[latest.band].label, change].filter(Boolean).join(' · ')}
          </Text>
        </View>
        <Icon name="chevron-right" size={18} color={theme.textSubtle} />
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 13 },
  text: { flex: 1, minWidth: 0 },
});
