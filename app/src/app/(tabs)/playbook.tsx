import { Linking, StyleSheet, View } from 'react-native';

import { Rise } from '@/components/motion/rise';
import { PlaybookUpload } from '@/components/playbook-upload';
import { Button } from '@/components/ui/button';
import { Callout } from '@/components/ui/callout';
import { DocumentRow } from '@/components/ui/document-row';
import { EmptyState } from '@/components/ui/empty-state';
import { Screen } from '@/components/ui/screen';
import { Text } from '@/components/ui/text';
import { useRefreshOnFocus } from '@/hooks/use-refresh-on-focus';
import { useRequest } from '@/hooks/use-request';
import { getProfile, messageOf } from '@/lib/api';
import { playbookKind } from '@/lib/playbook';

/**
 * The playbook the debrief reads. The API keeps one per user; a new upload
 * replaces it. The first version showed a list of sample files here that
 * were never sent anywhere.
 */
export default function PlaybookTab() {
  const profile = useRequest('profile', getProfile);
  useRefreshOnFocus(profile.reload);
  const data = profile.data;

  return (
    <Screen scroll edges={['top']} contentStyle={styles.content}>
      <Rise>
        <Text variant="title" accessibilityRole="header">
          Your playbook
        </Text>
        <Text variant="body" color="textSecondary" style={styles.subhead}>
          The debrief checks your prices, claims and positioning against this document.
        </Text>
      </Rise>

      {profile.loading ? null : !data ? (
        <EmptyState
          icon="info"
          title="Your playbook did not load"
          body={messageOf(profile.error)}
          action={{ label: 'Try again', onPress: profile.reload }}
        />
      ) : (
        <>
          {data.has_playbook && data.playbook_url ? (
            <Rise index={1} style={styles.block}>
              <DocumentRow
                name="Current playbook"
                meta={`${playbookKind(data.playbook_url)} · used in every debrief`}
                trailing={
                  <Button
                    label="Open"
                    variant="text"
                    style={styles.open}
                    // The link is presigned and short-lived; this one came
                    // with the profile that was just loaded.
                    onPress={() => Linking.openURL(data.playbook_url!)}
                  />
                }
              />
            </Rise>
          ) : (
            <Rise index={1} style={styles.block}>
              <Callout icon="info">
                <Text variant="secondary">
                  No playbook yet. Until you add one, the debrief judges how you answered, not
                  whether the facts were right.
                </Text>
              </Callout>
            </Rise>
          )}

          <Rise index={2} style={styles.block}>
            <PlaybookUpload
              title={data.has_playbook ? 'Replace your playbook' : 'Upload your playbook'}
              onUploaded={profile.reload}
              compact
            />
          </Rise>
        </>
      )}
      <View style={styles.bottom} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 12 },
  subhead: { marginTop: 4 },
  block: { marginTop: 18 },
  open: { height: 40, paddingHorizontal: 8 },
  bottom: { height: 12 },
});
