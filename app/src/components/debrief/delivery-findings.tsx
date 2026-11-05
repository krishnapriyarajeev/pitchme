import { StyleSheet, View } from 'react-native';

import { Card, CardDivider } from '@/components/ui/card';
import { Text } from '@/components/ui/text';
import type { Finding } from '@/lib/api';
import { formatMoment } from '@/lib/format';

const PART: Record<string, string> = {
  speech: 'Speech',
  voice: 'Voice',
  vision: 'Body language',
};

/** What to change in how the user spoke and looked, with the moment. */
export function DeliveryFindings({ findings }: { findings: Finding[] }) {
  return (
    <Card>
      {findings.map((finding, i) => (
        <View key={`${finding.pipeline}-${finding.category}-${i}`} style={styles.item}>
          {i > 0 ? <CardDivider /> : null}
          <Text variant="pill" color="textSubtle">
            {(PART[finding.pipeline] ?? finding.pipeline).toUpperCase()}
            {finding.note ? ` · ${formatMoment(finding.note.t_start_ms)}` : ''}
          </Text>
          <Text variant="body">{finding.summary}</Text>
          {finding.note?.quote ? (
            <Text variant="secondary" color="textSecondary" numberOfLines={2}>
              “{finding.note.quote}”
            </Text>
          ) : null}
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  item: { gap: 4 },
});
