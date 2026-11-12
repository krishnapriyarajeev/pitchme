import { useState } from 'react';

import { messageOf, uploadProfileFile, type UploadConfirm } from '@/lib/api';
import { voiceFile } from '@/lib/voice';

/**
 * Saves a voice sample. The API then makes the voice clone in the background;
 * Profile shows when it is ready or if it failed. A failed upload shows its
 * error, so the user knows to try again.
 */
export function useVoiceUpload() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(uri: string): Promise<UploadConfirm | null> {
    setSaving(true);
    setError(null);
    try {
      return await uploadProfileFile('voice', voiceFile(uri));
    } catch (caught) {
      setError(messageOf(caught));
      return null;
    } finally {
      setSaving(false);
    }
  }

  return { save, saving, error };
}
