import * as SecureStore from 'expo-secure-store';

import { clearAuth, getAuth, getToken, saveAuth } from '@/lib/storage';

jest.mock('expo-secure-store', () => ({
  WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'device-only',
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

const store = jest.mocked(SecureStore);

beforeEach(async () => {
  jest.clearAllMocks();
  await clearAuth();
});

it('saves the token in the secure store, out of backups', async () => {
  await saveAuth({ token: 't1', userId: 'u1' });
  expect(store.setItemAsync).toHaveBeenCalledWith('pitchme.access_token', 't1', {
    keychainAccessible: 'device-only',
  });
});

it('reads the sign-in back from the secure store', async () => {
  store.getItemAsync.mockImplementation(async (key: string) =>
    key === 'pitchme.access_token' ? 't2' : 'u2',
  );
  await expect(getAuth()).resolves.toEqual({ token: 't2', userId: 'u2' });
});

it('keeps the sign-in in memory when the secure store fails', async () => {
  store.setItemAsync.mockRejectedValue(new Error('Keychain locked'));
  store.getItemAsync.mockRejectedValue(new Error('Keychain locked'));

  await saveAuth({ token: 't3', userId: 'u3' });

  await expect(getToken()).resolves.toBe('t3');
  await expect(getAuth()).resolves.toEqual({ token: 't3', userId: 'u3' });
});

it('counts a token without a user id as signed out', async () => {
  store.getItemAsync.mockImplementation(async (key: string) =>
    key === 'pitchme.access_token' ? 't4' : null,
  );
  await expect(getAuth()).resolves.toBeNull();
});

it('clears both values on sign out', async () => {
  await clearAuth();
  expect(store.deleteItemAsync).toHaveBeenCalledWith('pitchme.access_token');
  expect(store.deleteItemAsync).toHaveBeenCalledWith('pitchme.user_id');
});
