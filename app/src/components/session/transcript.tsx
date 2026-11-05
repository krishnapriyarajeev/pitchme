import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Text } from '@/components/ui/text';
import type { TranscriptTurn } from '@/lib/api';
import { formatMoment } from '@/lib/format';

const FIRST = 6;

/** What was said, turn by turn, from the call worker's transcript. */
export function Transcript({ turns, buyer }: { turns: TranscriptTurn[]; buyer: string }) {
  const [all, setAll] = useState(false);
  const shown = all ? turns : turns.slice(0, FIRST);

  return (
    <Card>
      <View style={styles.list}>
        {shown.map((turn, i) => (
          <View key={`${turn.start_ms}-${i}`} style={styles.turn}>
            <Text variant="pill" color={turn.role === 'seller' ? 'accent' : 'sageText'}>
              {(turn.role === 'seller' ? 'You' : buyer).toUpperCase()} ·{' '}
              {formatMoment(turn.start_ms)}
            </Text>
            <Text variant="body">
              {turn.text}
              {turn.interrupted ? ' …' : ''}
            </Text>
          </View>
        ))}
      </View>
      {turns.length > FIRST ? (
        <Button
          label={all ? 'Show less' : `Show all ${turns.length} turns`}
          variant="text"
          onPress={() => setAll((current) => !current)}
        />
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  list: { gap: 14 },
  turn: { gap: 3 },
});
