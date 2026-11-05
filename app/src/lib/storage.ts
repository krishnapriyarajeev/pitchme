/**
 * The sign-in on this device: the access token and the user id.
 *
 * The token is the real credential, so on a phone it goes in the Keychain
 * (iOS) or the Keystore (Android), never in plain storage. expo-secure-store
 * has no web version, so the web build uses localStorage. If the store
 * fails (private browsing, a locked Keychain), the values stay in memory
 * for this launch, so sign-in still works.
 *
 * Only this module touches device storage.
 */

import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const TOKEN = 'pitchme.access_token';
const USER_ID = 'pitchme.user_id';

const memory = new Map<string, string>();
const isWeb = Platform.OS === 'web';

async function read(key: string): Promise<string | null> {
  try {
    const stored = isWeb
      ? globalThis.localStorage?.getItem(key)
      : await SecureStore.getItemAsync(key);
    return stored ?? memory.get(key) ?? null;
  } catch {
    return memory.get(key) ?? null;
  }
}

async function write(key: string, value: string): Promise<void> {
  memory.set(key, value);
  try {
    if (isWeb) globalThis.localStorage?.setItem(key, value);
    else
      await SecureStore.setItemAsync(key, value, {
        // Not in backups, and not readable while the phone is locked.
        keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
      });
  } catch {
    // Kept in memory for this launch.
  }
}

async function remove(key: string): Promise<void> {
  memory.delete(key);
  try {
    if (isWeb) globalThis.localStorage?.removeItem(key);
    else await SecureStore.deleteItemAsync(key);
  } catch {
    // Nothing more to do.
  }
}

export type StoredAuth = { token: string; userId: string };

/** The saved sign-in, or null. A token without its user id counts as none. */
export async function getAuth(): Promise<StoredAuth | null> {
  const [token, userId] = await Promise.all([read(TOKEN), read(USER_ID)]);
  return token && userId ? { token, userId } : null;
}

export async function getToken(): Promise<string | null> {
  return read(TOKEN);
}

export async function saveAuth(auth: StoredAuth): Promise<void> {
  await Promise.all([write(TOKEN, auth.token), write(USER_ID, auth.userId)]);
}

/** Sign out. The two values always go together. */
export async function clearAuth(): Promise<void> {
  await Promise.all([remove(TOKEN), remove(USER_ID)]);
}
