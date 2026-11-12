import { StyleSheet, View } from 'react-native';

import { Text } from '@/components/ui/text';
import { useCorrectionStyle } from '@/hooks/use-bands';
import type { Objection } from '@/lib/debrief';
import { formatMoment } from '@/lib/format';

/**
 * A wrong price or a claim the playbook does not back. These are the
 * things to fix before the real call, so they get the strongest card in
 * the app, in terra (the app has no red).
 */
export function Integrity({ items }: { items: Objection[] }) {
  const look = useCorrectionStyle();

  return (
    <>
      {items.map((item, i) => (
        <View
          key={`${item.question}-${i}`}
          style={[styles.card, { backgroundColor: look.background, borderColor: look.border }]}>
          <Text variant="rowTitle" color={look.text}>
            {item.said ? `“${item.said}”` : item.question}
          </Text>
          <Text variant="secondary" color={look.text}>
            {item.why}
          </Text>
          {item.evidence ? (
            <Text variant="secondary" color={look.text}>
              Your playbook says: {item.evidence}
            </Text>
          ) : null}
          {item.atMs !== null ? (
            <Text variant="pill" color={look.text}>
              AT {formatMoment(item.atMs)}
            </Text>
          ) : null}
        </View>
      ))}
    </>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 14, padding: 14, gap: 6 },
});
