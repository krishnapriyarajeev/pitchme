import { File } from 'expo-file-system';

import { ApiError } from '@/lib/api/client';
import { extensionOf, putFile } from '@/lib/api/upload';

jest.mock('expo-file-system', () => ({
  File: jest.fn(),
  UploadType: { BINARY_CONTENT: 0 },
  Paths: { cache: { uri: 'file:///cache/' }, document: { uri: 'file:///docs/' } },
}));

const upload = jest.fn();
jest.mocked(File).mockImplementation(() => ({ upload }) as never);

beforeEach(() => upload.mockReset());

describe('extensionOf', () => {
  it('reads the extension from the name, then from the URI', () => {
    expect(extensionOf({ uri: 'file:///x/a.bin', name: 'Sample.M4A' })).toBe('m4a');
    expect(extensionOf({ uri: 'file:///x/playbook.pdf?v=2' })).toBe('pdf');
    expect(extensionOf({ uri: 'content://media/42' })).toBe('');
  });
});

describe('putFile', () => {
  const file = { uri: 'file:///cache/voice.m4a', mimeType: 'audio/mp4' };

  it('PUTs the file as raw bytes with its type', async () => {
    upload.mockResolvedValue({ status: 200, body: '' });
    await putFile('https://storage.test/put', file, 'voice sample');
    expect(upload).toHaveBeenCalledWith('https://storage.test/put', {
      httpMethod: 'PUT',
      uploadType: 0,
      mimeType: 'audio/mp4',
    });
  });

  it('names the file when storage refuses it', async () => {
    upload.mockResolvedValue({ status: 403, body: 'denied' });
    await expect(putFile('https://storage.test/put', file, 'voice sample')).rejects.toEqual(
      new ApiError(403, 'upload_failed', 'Storage did not take the voice sample (403). Try again.'),
    );
  });

  it('turns a dropped connection into a network error', async () => {
    upload.mockRejectedValue(new Error('offline'));
    await expect(putFile('https://storage.test/put', file, 'playbook')).rejects.toMatchObject({
      code: 'network',
    });
  });
});
