import { useRouter } from 'expo-router';
import { FlatList, StyleSheet, View } from 'react-native';

import { SessionRow } from '@/components/session-row';
import { Spinner } from '@/components/motion/spinner';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Screen, ScreenHeader } from '@/components/ui/screen';
import { Spacing } from '@/constants/theme';
import { useRefreshOnFocus } from '@/hooks/use-refresh-on-focus';
import { useSessionList } from '@/hooks/use-session-list';
import { useTheme } from '@/hooks/use-theme';
import { messageOf } from '@/lib/api';

/** Every rehearsal, newest first, loaded a page at a time. */
export default function Sessions() {
  const theme = useTheme();
  const router = useRouter();
  const list = useSessionList();
  useRefreshOnFocus(list.reload);

  return (
    <Screen gutter={false}>
      <View style={styles.header}>
        <ScreenHeader title="All rehearsals" />
      </View>
      <FlatList
        data={list.items}
        keyExtractor={(item) => item.session_id}
        renderItem={({ item }) => (
          <SessionRow session={item} onPress={() => router.push(`/session/${item.session_id}`)} />
        )}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={styles.gap} />}
        onEndReached={list.loadMore}
        onEndReachedThreshold={0.4}
        refreshing={false}
        onRefresh={list.reload}
        ListEmptyComponent={
          list.loading ? null : list.error ? (
            <EmptyState
              icon="info"
              title="Your rehearsals did not load"
              body={messageOf(list.error)}
              action={{ label: 'Try again', onPress: list.reload }}
            />
          ) : (
            <EmptyState
              icon="video"
              title="No rehearsals yet"
              body="Your first one is one tap away on Home."
            />
          )
        }
        ListFooterComponent={
          list.loadingMore ? (
            <View style={styles.footer}>
              <Spinner color={theme.accent} trackColor={theme.border} />
            </View>
          ) : list.error && list.items.length > 0 ? (
            <Button label="Load more" variant="text" onPress={list.loadMore} />
          ) : null
        }
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { paddingHorizontal: Spacing.gutter },
  list: { paddingHorizontal: Spacing.gutter, paddingTop: 14, paddingBottom: Spacing.five },
  gap: { height: 10 },
  footer: { alignItems: 'center', paddingVertical: 16 },
});
