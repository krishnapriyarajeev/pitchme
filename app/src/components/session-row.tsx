import { Pressable, StyleSheet, View } from 'react-native';

import { BandPill } from '@/components/ui/band-pill';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { bandFor } from '@/constants/bands';
import { Radius } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { SessionSummary } from '@/lib/api';
import { rehearsalState, sessionMeta, sessionTitle, STATE_LABEL } from '@/lib/sessions';

/**
 * One rehearsal in a list, on Home and on the full list. A reviewed one
 * shows its band, not its number: in a list a number reads as a grade on a
 * conversation. The number is on the debrief and on Progress.
 */
export function SessionRow({ session, onPress }: { session: SessionSummary; onPress: () => void }) {
  const theme = useTheme();
  const state = rehearsalState(session);
  const title = sessionTitle(session);
  const meta = sessionMeta(session);
  const band =
    state === 'debrief' && session.overall_score !== null ? bandFor(session.overall_score) : null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${meta}. ${STATE_LABEL[state]}.`}
      style={({ pressed }) => [
        styles.row,
        { backgroundColor: theme.surface, borderColor: theme.border, opacity: pressed ? 0.8 : 1 },
      ]}>
      <View style={[styles.thumb, { backgroundColor: theme.surfaceAlt }]}>
        <Icon name="video" size={18} color={theme.textSubtle} strokeWidth={1.4} />
      </View>
      <View style={styles.body}>
        <Text variant="rowTitle" numberOfLines={1}>
          {title}
        </Text>
        <Text variant="secondary" color="textSecondary" numberOfLines={1}>
          {meta}
        </Text>
      </View>
      {band ? (
        <BandPill band={band} />
      ) : (
        <Text variant="secondary" color="textSubtle">
          {STATE_LABEL[state]}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderWidth: 1,
    borderRadius: Radius.card,
    paddingHorizontal: 15,
    paddingVertical: 13,
  },
  thumb: {
    width: 40,
    height: 40,
    borderRadius: Radius.nested,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1, minWidth: 0, gap: 2 },
});
