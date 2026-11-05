import { StyleSheet, View } from 'react-native';

import { BandPill } from '@/components/ui/band-pill';
import { Card } from '@/components/ui/card';
import { ScoreRing } from '@/components/ui/score-ring';
import { Text } from '@/components/ui/text';
import { bandFor } from '@/constants/bands';
import { useBands } from '@/hooks/use-bands';
import { useTheme } from '@/hooks/use-theme';
import type { AnalysisResult } from '@/lib/api';

/**
 * The overall score, its band and the one-paragraph summary. The first
 * version scaled this score by 10 in some places and not others.
 */
export function ScoreHeader({ result }: { result: AnalysisResult }) {
  const theme = useTheme();
  const bands = useBands();
  const score = result.overall_score;
  const band = score === null ? null : bandFor(score);

  return (
    <Card tone="hero">
      {score !== null && band ? (
        <View style={styles.row}>
          <ScoreRing
            score={score}
            color={bands[band].bar}
            trackColor={theme.accentSoft}
            size={84}
            strokeWidth={7}>
            <Text variant="numeral" style={styles.number}>
              {Math.round(score)}
            </Text>
          </ScoreRing>
          <View style={styles.side}>
            <BandPill band={band} emphasis />
            <Text variant="secondary" color="textSecondary">
              {result.questions > 0
                ? `${result.handled} of ${result.questions} questions handled`
                : 'The buyer asked no questions'}
            </Text>
          </View>
        </View>
      ) : (
        <Text variant="secondary" color="textSecondary">
          No overall score: nothing in this call could be scored.
        </Text>
      )}
      <Text variant="body" style={styles.summary}>
        {result.summary}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 18 },
  number: { fontSize: 30, lineHeight: 34 },
  side: { flex: 1, gap: 8 },
  summary: { marginTop: 16 },
});
