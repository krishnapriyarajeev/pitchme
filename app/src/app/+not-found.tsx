import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Screen } from '@/components/ui/screen';

export default function NotFound() {
  const router = useRouter();

  return (
    <Screen>
      <View style={styles.centre}>
        <EmptyState
          icon="info"
          title="This page is not here"
          body="The link may be old. Go back to Home to continue."
        />
        <Button label="Go to Home" onPress={() => router.replace('/home')} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, justifyContent: 'center', gap: 8 },
});
