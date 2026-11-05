import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { Text } from '@/components/ui/text';
import { useRequest } from '@/hooks/use-request';
import { getHealth, messageOf } from '@/lib/api';
import { API_URL } from '@/lib/config';

/**
 * A note when the app cannot reach the API, with the address it tried.
 * Shows nothing while the API answers.
 */
export function ServerStatus() {
  const health = useRequest('health', getHealth);

  if (health.loading || health.data) return null;

  return (
    <Callout tone="attention" icon="info">
      <View style={styles.body}>
        <Text variant="secondary">{messageOf(health.error)}</Text>
        {API_URL ? (
          <Text variant="secondary" color="textSecondary">
            Address: {API_URL}
          </Text>
        ) : null}
        <Button
          label="Try again"
          variant="text"
          loading={health.refreshing}
          onPress={health.reload}
          style={styles.retry}
        />
      </View>
    </Callout>
  );
}

const styles = StyleSheet.create({
  body: { gap: 4 },
  retry: { alignSelf: 'flex-start', paddingHorizontal: 0, height: 36 },
});
