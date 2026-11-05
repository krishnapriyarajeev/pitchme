import { File, UploadType } from 'expo-file-system';
import { Platform } from 'react-native';

import { ApiError } from '@/lib/api/client';
import { normalizeLocalUri } from '@/lib/local-uri';

export type LocalFile = { uri: string; name?: string; mimeType?: string };

/**
 * PUT a local file to a presigned storage URL. The file goes straight to
 * storage, not through the API, so a large recording does not tie up an
 * API worker.
 */
export async function putFile(url: string, file: LocalFile, what: string): Promise<void> {
  let status: number;
  try {
    if (Platform.OS === 'web') {
      const blob = await (await fetch(file.uri)).blob();
      status = (
        await fetch(url, {
          method: 'PUT',
          body: blob,
          headers: file.mimeType ? { 'Content-Type': file.mimeType } : undefined,
        })
      ).status;
    } else {
      const result = await new File(normalizeLocalUri(file.uri)).upload(url, {
        httpMethod: 'PUT',
        uploadType: UploadType.BINARY_CONTENT,
        ...(file.mimeType ? { mimeType: file.mimeType } : {}),
      });
      status = result.status;
    }
  } catch {
    throw new ApiError(
      0,
      'network',
      `Could not send the ${what}. Check your connection and try again.`,
    );
  }
  if (status < 200 || status >= 300) {
    throw new ApiError(
      status,
      'upload_failed',
      `Storage did not take the ${what} (${status}). Try again.`,
    );
  }
}

/** "m4a" from "sample.m4a" or "file:///x/sample.M4A". */
export function extensionOf(file: LocalFile): string {
  const source = file.name ?? file.uri.split('?')[0] ?? '';
  const match = /\.([a-z0-9]{1,10})$/i.exec(source);
  return match?.[1]?.toLowerCase() ?? '';
}
