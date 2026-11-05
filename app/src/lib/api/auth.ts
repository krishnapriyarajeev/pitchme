import { request } from '@/lib/api/client';
import type { AuthResponse } from '@/lib/api/types';
import { clearAuth, saveAuth } from '@/lib/storage';

export type SignedIn = { userId: string };

async function keep(response: AuthResponse): Promise<SignedIn> {
  await saveAuth({ token: response.access_token, userId: response.user_id });
  return { userId: response.user_id };
}

export async function register(
  email: string,
  password: string,
  displayName?: string,
): Promise<SignedIn> {
  const response = await request<AuthResponse>('/api/auth/register', {
    method: 'POST',
    auth: false,
    body: { email, password, display_name: displayName || undefined },
  });
  return keep(response);
}

export async function login(email: string, password: string): Promise<SignedIn> {
  const response = await request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    auth: false,
    body: { email, password },
  });
  return keep(response);
}

export async function logout(): Promise<void> {
  await clearAuth();
}
