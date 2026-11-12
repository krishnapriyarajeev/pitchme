import * as DocumentPicker from 'expo-document-picker';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Spinner } from '@/components/motion/spinner';
import { Button } from '@/components/ui/button';
import { DocumentRow } from '@/components/ui/document-row';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { UploadZone } from '@/components/ui/upload-zone';
import { useTheme } from '@/hooks/use-theme';
import { messageOf, uploadProfileFile } from '@/lib/api';
import { fileKind, formatBytes } from '@/lib/format';
import { checkPlaybook, PLAYBOOK_FORMATS, PLAYBOOK_MIME_TYPES } from '@/lib/playbook';

type Picked = { uri: string; name: string; size?: number; mimeType?: string };
type State = 'uploading' | 'done' | 'failed';

type Props = {
  title?: string;
  detail?: string;
  /** Called after the API confirms the upload. */
  onUploaded?: () => void;
  compact?: boolean;
};

/**
 * Picks a playbook and uploads it at once, so the next debrief can use it.
 */
export function PlaybookUpload({
  title = 'Upload your playbook',
  detail = 'Positioning, pricing, a pitch deck or battle cards',
  onUploaded,
  compact,
}: Props) {
  const theme = useTheme();
  const [file, setFile] = useState<Picked | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function send(picked: Picked) {
    setState('uploading');
    setMessage(null);
    try {
      await uploadProfileFile('playbook', picked);
      setState('done');
      onUploaded?.();
    } catch (error) {
      setState('failed');
      setMessage(messageOf(error));
    }
  }

  async function pick() {
    const result = await DocumentPicker.getDocumentAsync({
      type: PLAYBOOK_MIME_TYPES,
      copyToCacheDirectory: true,
      multiple: false,
    });
    const asset = result.canceled ? undefined : result.assets[0];
    if (!asset) return;
    const picked: Picked = {
      uri: asset.uri,
      name: asset.name,
      size: asset.size ?? undefined,
      mimeType: asset.mimeType ?? undefined,
    };
    setFile(picked);
    const problem = checkPlaybook(picked);
    if (problem) {
      setState('failed');
      setMessage(problem);
      return;
    }
    await send(picked);
  }

  const trailing =
    state === 'uploading' ? (
      <Spinner
        size={20}
        color={theme.accent}
        trackColor={theme.border}
        accessibilityLabel="Uploading"
      />
    ) : state === 'done' ? (
      <Icon name="check-circle" size={20} color={theme.sageDeep} />
    ) : null;

  return (
    <View style={styles.wrap}>
      <UploadZone
        title={file ? 'Choose another file' : title}
        detail={detail}
        formats={PLAYBOOK_FORMATS}
        onPress={pick}
        disabled={state === 'uploading'}
        compact={compact}
      />
      {file ? (
        <DocumentRow
          name={file.name}
          meta={[fileKind(file.name), formatBytes(file.size)].filter(Boolean).join(' · ')}
          trailing={trailing}
          note={
            state === 'failed' ? (
              <View style={styles.failed}>
                <Text variant="secondary" color="terraText" accessibilityLiveRegion="polite">
                  {message}
                </Text>
                {checkPlaybook(file) === null ? (
                  <Button
                    label="Try again"
                    variant="quiet"
                    onPress={() => send(file)}
                    style={styles.retry}
                  />
                ) : null}
              </View>
            ) : state === 'done' ? (
              <Text variant="secondary" color="sageText">
                Saved. The next debrief checks your answers against it.
              </Text>
            ) : null
          }
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 12 },
  failed: { gap: 10 },
  retry: { height: 44 },
});
