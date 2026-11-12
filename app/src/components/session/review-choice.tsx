import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';
import { messageOf, startAnalysis, type AnalysisMode } from '@/lib/api';
import { REVIEW_MODES } from '@/lib/review';

type Props = {
  sessionId: string;
  onStarted: () => void;
};

/**
 * How deep to review. No price on either card: practising must never feel
 * like it costs.
 */
export function ReviewChoice({ sessionId, onStarted }: Props) {
  const theme = useTheme();
  const [busy, setBusy] = useState<AnalysisMode | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function choose(mode: AnalysisMode) {
    if (busy) return;
    setBusy(mode);
    setError(null);
    try {
      await startAnalysis(sessionId, mode);
      onStarted();
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <View style={styles.wrap}>
      {REVIEW_MODES.map((option, i) => {
        const featured = i === 0;
        return (
          <Pressable
            key={option.mode}
            onPress={() => choose(option.mode)}
            disabled={busy !== null}
            accessibilityRole="button"
            accessibilityLabel={`${option.title}. ${option.detail}`}
            accessibilityState={{ busy: busy === option.mode }}
            style={({ pressed }) => [{ opacity: pressed || busy === option.mode ? 0.7 : 1 }]}>
            <Card style={styles.card}>
              <View
                style={[
                  styles.icon,
                  { backgroundColor: featured ? theme.accentSoft : theme.surfaceAlt },
                ]}>
                <Icon
                  name={option.icon}
                  size={17}
                  color={featured ? theme.accent : theme.textSecondary}
                />
              </View>
              <View style={styles.text}>
                <Text variant="rowTitle">{option.title}</Text>
                <Text variant="secondary" color="textSecondary">
                  {option.detail}
                </Text>
              </View>
              <Icon name="chevron-right" size={17} color={theme.textSubtle} />
            </Card>
          </Pressable>
        );
      })}
      {error ? (
        <Text variant="secondary" color="terraText" accessibilityLiveRegion="polite">
          {error}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 10 },
  card: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 14 },
  icon: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center' },
  text: { flex: 1, minWidth: 0, gap: 1 },
});
