import { useState } from 'react';
import { LayoutAnimation, Pressable, StyleSheet, View } from 'react-native';

import { AnswerAudio } from '@/components/debrief/answer-audio';
import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useBands } from '@/hooks/use-bands';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { useTheme } from '@/hooks/use-theme';
import { VERDICTS, type Objection } from '@/lib/debrief';
import { formatMoment } from '@/lib/format';

type Props = { item: Objection; startOpen?: boolean; hasVoice: boolean };

/** One buyer question: what the user said, why, and a stronger answer. */
export function ObjectionCard({ item, startOpen = false, hasVoice }: Props) {
  const theme = useTheme();
  const bands = useBands();
  const reduced = useReducedMotion();
  const [open, setOpen] = useState(startOpen);
  const verdict = VERDICTS[item.verdict];
  const tone = bands[verdict.band];

  function toggle() {
    if (!reduced) LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setOpen((current) => !current);
  }

  return (
    <Card padded={false} style={styles.card}>
      <Pressable
        onPress={toggle}
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={`${item.question || 'A buyer question'}. ${verdict.label}.`}
        style={[styles.head, { backgroundColor: theme.surfaceAlt }]}>
        <Text variant="rowTitle" style={styles.question}>
          {item.question ? `“${item.question}”` : 'A buyer question'}
        </Text>
        <View style={[styles.pill, { backgroundColor: tone.tint }]}>
          <Text variant="pill" color={tone.text}>
            {verdict.label}
          </Text>
        </View>
        <Icon name={open ? 'chevron-up' : 'chevron-down'} size={15} color={theme.textSubtle} />
      </Pressable>

      {open ? (
        <View style={styles.body}>
          <Text variant="pill" color="textSubtle">
            YOU SAID{item.atMs !== null ? ` · ${formatMoment(item.atMs)}` : ''}
          </Text>
          <Text variant="body" color="textSecondary">
            {item.said ? `“${item.said}”` : 'This one went unanswered.'}
          </Text>
          <Text variant="secondary" color="textSecondary">
            {item.why}
          </Text>
          {item.evidence ? (
            <Text variant="secondary" color="textSubtle">
              Your playbook: {item.evidence}
            </Text>
          ) : null}

          {item.stronger ? (
            <View style={[styles.stronger, { backgroundColor: theme.sageSoft }]}>
              <Text variant="pill" color="sageText">
                A STRONGER ANSWER
              </Text>
              <Text variant="body">“{item.stronger.stronger}”</Text>
              {item.stronger.change ? (
                <Text variant="secondary" color="textSecondary">
                  {item.stronger.change}
                </Text>
              ) : null}
              {item.stronger.unsupported_numbers.length > 0 ? (
                <Text variant="secondary" color="goldText">
                  Check before you use it: {item.stronger.unsupported_numbers.join(', ')} is not in
                  your playbook.
                </Text>
              ) : null}
              {item.stronger.audio_url ? (
                <AnswerAudio uri={item.stronger.audio_url} />
              ) : (
                <Text variant="secondary" color="textSubtle">
                  {hasVoice
                    ? 'The spoken version was not made this time.'
                    : 'Record a voice sample in Profile to hear this in your own voice.'}
                </Text>
              )}
            </View>
          ) : null}
        </View>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { overflow: 'hidden' },
  head: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14 },
  question: { flex: 1 },
  pill: { borderRadius: 999, paddingHorizontal: 9, paddingVertical: 3 },
  body: { padding: 14, gap: 8 },
  stronger: { marginTop: 4, borderRadius: 12, padding: 12, gap: 8 },
});
