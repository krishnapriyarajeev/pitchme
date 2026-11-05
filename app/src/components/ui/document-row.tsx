import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';

type Props = {
  name: string;
  /** "PDF · 1.8 MB" */
  meta?: string;
  /** A status or an action at the end of the row. */
  trailing?: ReactNode;
  /** A line under the row, for example what to do after a failed upload. */
  note?: ReactNode;
};

/** One document: the playbook in onboarding and on the Playbook tab. */
export function DocumentRow({ name, meta, trailing, note }: Props) {
  const theme = useTheme();

  return (
    <Card style={styles.card}>
      <View style={styles.row}>
        <View style={[styles.icon, { backgroundColor: theme.sageSoft }]}>
          <Icon name="file" size={16} color={theme.sageDeep} strokeWidth={1.6} />
        </View>
        <View style={styles.body}>
          <Text variant="rowTitle" numberOfLines={1}>
            {name}
          </Text>
          {meta ? (
            <Text variant="secondary" color="textSubtle">
              {meta}
            </Text>
          ) : null}
        </View>
        {trailing}
      </View>
      {note ? <View style={styles.note}>{note}</View> : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { paddingVertical: 14 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  icon: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  body: { flex: 1, minWidth: 0, gap: 1 },
  note: { marginTop: 10 },
});
