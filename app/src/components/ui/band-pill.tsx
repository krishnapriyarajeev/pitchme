import { StyleSheet, View } from 'react-native';

import { Text } from '@/components/ui/text';
import type { Band } from '@/constants/bands';
import { Radius } from '@/constants/theme';
import { useBands } from '@/hooks/use-bands';

type Props = {
  band: Band;
  /** Capitals, for the one main pill on a debrief. */
  emphasis?: boolean;
};

/** A band always shows its label, so it never depends on colour alone. */
export function BandPill({ band, emphasis = false }: Props) {
  const style = useBands()[band];

  return (
    <View style={[styles.pill, emphasis && styles.emphasis, { backgroundColor: style.tint }]}>
      <Text variant="pill" color={style.text}>
        {emphasis ? style.label.toUpperCase() : style.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: 'flex-start',
    borderRadius: Radius.pill,
    paddingHorizontal: 9,
    paddingVertical: 3,
  },
  emphasis: { paddingHorizontal: 10, paddingVertical: 4 },
});
