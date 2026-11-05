import { fileKind, formatBytes } from '@/lib/format';

/** The types the API can read as a playbook (backend/server/storage/keys.py). */
export const PLAYBOOK_EXTENSIONS = ['pdf', 'pptx', 'docx', 'txt'] as const;

export const PLAYBOOK_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
];

/** The API's limit. Checked here first, so a large file is not sent for nothing. */
export const PLAYBOOK_MAX_BYTES = 25 * 1024 * 1024;

export const PLAYBOOK_FORMATS = 'PDF, PPTX, DOCX or TXT, up to 25 MB';

/** Why the file cannot be the playbook, or null when it can. */
export function checkPlaybook(file: { name: string; size?: number | null }): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (!(PLAYBOOK_EXTENSIONS as readonly string[]).includes(extension)) {
    return `PitchMe cannot read ${fileKind(file.name)} files. Use a PDF, PPTX, DOCX or TXT file.`;
  }
  if (file.size && file.size > PLAYBOOK_MAX_BYTES) {
    return `This file is ${formatBytes(file.size)}. Use a file of 25 MB or less.`;
  }
  return null;
}

/** "PDF" from the stored playbook's address. */
export function playbookKind(url: string | null | undefined): string {
  const path = url?.split('?')[0] ?? '';
  return fileKind(path.slice(path.lastIndexOf('/') + 1));
}
