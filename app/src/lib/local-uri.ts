import { Paths } from 'expo-file-system';

/**
 * Repair a local file URI that is encoded one level too little.
 *
 * Some native modules (expo-camera's recordAsync, for one) return a URI
 * whose app folder name is decoded once too often. The file is there, but
 * reading or uploading it fails with ENOENT. If the URI starts with the
 * decoded form of the cache or document folder, this puts the folder's
 * correct spelling back. Any other URI comes back unchanged.
 */
export function normalizeLocalUri(uri: string): string {
  if (!uri.startsWith('file://')) return uri;

  for (const folder of [Paths.cache, Paths.document]) {
    const correct = folder.uri;
    if (uri.startsWith(correct)) return uri;
    let decoded: string;
    try {
      decoded = decodeURIComponent(correct);
    } catch {
      continue;
    }
    if (decoded !== correct && uri.startsWith(decoded)) {
      return correct + uri.slice(decoded.length);
    }
  }
  return uri;
}
