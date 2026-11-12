import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Spinner } from '@/components/motion/spinner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';
import { messageOf, retryVoiceClone, type Profile } from '@/lib/api';

type Props = {
  profile: Profile;
  /** Load the profile again, for example after a retry. */
  reload: () => unknown;
};

/**
 * The voice sample and its clone, as the API reports them. A sample alone
 * is not "ready": only a finished clone is.
 */
export function VoiceStatus({ profile, reload }: Props) {
  const theme = useTheme();
  const router = useRouter();
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = profile.has_voice_sample ? profile.voice_clone_status : null;

  async function retry() {
    setRetrying(true);
    setError(null);
    try {
      await retryVoiceClone();
      await reload();
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      setRetrying(false);
    }
  }

  const record = (
    <Button
      label={status ? 'Record again' : 'Record a sample'}
      variant={status ? 'text' : 'quiet'}
      icon="mic"
      onPress={() => router.push('/profile/voice')}
      style={styles.action}
    />
  );

  return (
    <Card>
      <Text variant="pill" color="textSubtle">
        YOUR VOICE
      </Text>
      <View style={styles.row}>
        {status === 'pending' ? (
          <Spinner size={20} color={theme.accent} trackColor={theme.border} />
        ) : status === 'ready' ? (
          <Icon name="check-circle" size={20} color={theme.sageDeep} />
        ) : (
          <Icon name="mic" size={20} color={status === 'failed' ? theme.terra : theme.textSubtle} />
        )}
        <Text variant="body" style={styles.text}>
          {status === 'pending'
            ? 'Making your voice clone. This takes about a minute.'
            : status === 'ready'
              ? 'Ready. Stronger answers play back in your voice.'
              : status === 'failed'
                ? (profile.voice_clone_error ?? 'The voice clone did not work.')
                : 'No sample yet. Without one, stronger answers show as text only.'}
        </Text>
      </View>
      {error ? (
        <Text variant="secondary" color="terraText" style={styles.error}>
          {error}
        </Text>
      ) : null}
      <View style={styles.actions}>
        {status === 'failed' ? (
          <Button
            label="Try again"
            variant="quiet"
            icon="refresh"
            loading={retrying}
            onPress={retry}
            style={styles.action}
          />
        ) : null}
        {status === 'pending' ? null : record}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { marginTop: 8, flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  text: { flex: 1 },
  error: { marginTop: 8 },
  actions: { marginTop: 10, gap: 4 },
  action: { height: 44 },
});
