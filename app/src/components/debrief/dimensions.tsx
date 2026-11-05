import { StyleSheet, View } from 'react-native';

import { GrowBar } from '@/components/motion/grow-bar';
import { Card, CardDivider } from '@/components/ui/card';
import { Text } from '@/components/ui/text';
import { bandFor } from '@/constants/bands';
import { useBands } from '@/hooks/use-bands';
import { useTheme } from '@/hooks/use-theme';
import type { Dimension } from '@/lib/api';

/**
 * Content, speech, voice and body language. A part that could not be scored
 * says why, in place of a bar. The first version used other band edges here
 * than on the rest of the app.
 */
export function Dimensions({ dimensions }: { dimensions: Dimension[] }) {
  const theme = useTheme();
  const bands = useBands();

  return (
    <Card>
      {dimensions.map((dimension, i) => (
        <View key={dimension.name}>
          {i > 0 ? <CardDivider /> : null}
          <View style={styles.head}>
            <Text variant="rowTitle">{dimension.label}</Text>
            <Text variant="rowTitle" color={dimension.score === null ? 'textSubtle' : 'text'}>
              {dimension.score === null ? 'Not scored' : Math.round(dimension.score)}
            </Text>
          </View>
          {dimension.score !== null ? (
            <GrowBar
              value={dimension.score}
              color={bands[bandFor(dimension.score)].bar}
              trackColor={theme.accentSoft}
              delay={i * 80}
              style={styles.bar}
            />
          ) : null}
          <Text variant="secondary" color="textSecondary" style={styles.summary}>
            {dimension.skipped ?? dimension.summary}
          </Text>
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  bar: { marginTop: 8 },
  summary: { marginTop: 6 },
});
