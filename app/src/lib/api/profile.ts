import { ApiError, request } from '@/lib/api/client';
import type {
  Profile,
  ProfileUpdate,
  UploadConfirm,
  UploadKind,
  UploadUrl,
  VoiceClone,
} from '@/lib/api/types';
import { extensionOf, putFile, type LocalFile } from '@/lib/api/upload';

export function getProfile(): Promise<Profile> {
  return request<Profile>('/api/profile');
}

export function updateProfile(changes: ProfileUpdate): Promise<Profile> {
  return request<Profile>('/api/profile', { method: 'PUT', body: changes });
}

const NAMES: Record<UploadKind, string> = { voice: 'voice sample', playbook: 'playbook' };

/**
 * Upload a voice sample or a playbook in three steps: get a presigned URL,
 * PUT the file to storage, then confirm, so the API checks that the file is
 * there and is the user's. A voice sample starts a voice clone, and the
 * reply carries its status.
 */
export async function uploadProfileFile(kind: UploadKind, file: LocalFile): Promise<UploadConfirm> {
  const extension = extensionOf(file);
  if (!extension) {
    throw new ApiError(0, 'invalid_upload', `The ${NAMES[kind]} has no file type. Pick it again.`);
  }
  const { upload_url, object_key } = await request<UploadUrl>('/api/profile/upload-url', {
    method: 'POST',
    body: { kind, file_extension: extension },
  });
  await putFile(upload_url, file, NAMES[kind]);
  return request<UploadConfirm>('/api/profile/upload-confirm', {
    method: 'POST',
    body: { kind, object_key },
  });
}

/** Clone the voice again from the saved sample, for example after a failure. */
export function retryVoiceClone(): Promise<VoiceClone> {
  return request<VoiceClone>('/api/profile/voice-clone', { method: 'POST' });
}
