import { act, renderHook, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';

import { AuthProvider, PROFILE_NOT_SAVED, restoreSession, useAuth } from '@/hooks/use-auth';
import * as api from '@/lib/api';
import { getAuth } from '@/lib/storage';

jest.mock('@/lib/api', () => {
  const actual = jest.requireActual('@/lib/api/client');
  return {
    ApiError: actual.ApiError,
    MESSAGES: actual.MESSAGES,
    getProfile: jest.fn(),
    login: jest.fn(),
    logout: jest.fn(),
    register: jest.fn(),
    updateProfile: jest.fn(),
    onSignedOut: jest.fn(),
  };
});
jest.mock('@/lib/storage', () => ({ getAuth: jest.fn() }));

const mocked = jest.mocked(api);
const saved = { token: 't', userId: 'u' };
let signedOutListener: (() => void) | undefined;

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(getAuth).mockResolvedValue(null);
  mocked.onSignedOut.mockImplementation((listener) => {
    signedOutListener = listener;
    return () => undefined;
  });
});

const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>;

async function renderAuth() {
  const view = await renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(view.result.current.status).not.toBe('checking'));
  return view;
}

describe('restoreSession', () => {
  it('is signed out with no saved token, and asks the API nothing', async () => {
    await expect(restoreSession()).resolves.toBe('signed_out');
    expect(mocked.getProfile).not.toHaveBeenCalled();
  });

  it('signs in when the API takes the saved token', async () => {
    jest.mocked(getAuth).mockResolvedValue(saved);
    mocked.getProfile.mockResolvedValue({} as never);
    await expect(restoreSession()).resolves.toBe('signed_in');
  });

  it('signs out when the API rejects the saved token', async () => {
    jest.mocked(getAuth).mockResolvedValue(saved);
    mocked.getProfile.mockRejectedValue(new api.ApiError(401, 'unauthorized', 'x'));
    await expect(restoreSession()).resolves.toBe('signed_out');
  });

  it('keeps the user signed in without a network', async () => {
    jest.mocked(getAuth).mockResolvedValue(saved);
    mocked.getProfile.mockRejectedValue(new api.ApiError(0, 'network', 'x'));
    await expect(restoreSession()).resolves.toBe('signed_in');
  });
});

describe('AuthProvider', () => {
  it('signs up, saves the role and product, and opens onboarding', async () => {
    const { result } = await renderAuth();

    await act(() =>
      result.current.signUp({
        email: ' jo@saber.com ',
        password: 'long-enough',
        name: 'Jo ',
        roleTitle: 'AE',
        sells: ' ',
      }),
    );

    expect(mocked.register).toHaveBeenCalledWith('jo@saber.com', 'long-enough', 'Jo');
    expect(mocked.updateProfile).toHaveBeenCalledWith({ role_title: 'AE' });
    expect(result.current).toMatchObject({ status: 'signed_in', onboarding: true, notice: null });
  });

  it('goes on with a note when the profile save fails after sign-up', async () => {
    mocked.updateProfile.mockRejectedValue(new api.ApiError(0, 'network', 'x'));
    const { result } = await renderAuth();

    await act(() =>
      result.current.signUp({ email: 'a@b.com', password: 'long-enough', name: 'A', sells: 'CRM' }),
    );

    expect(result.current).toMatchObject({ status: 'signed_in', notice: PROFILE_NOT_SAVED });
  });

  it('stays signed out when sign-up fails', async () => {
    mocked.register.mockRejectedValue(new api.ApiError(409, 'email_taken', 'Taken.'));
    const { result } = await renderAuth();

    await expect(
      act(() => result.current.signUp({ email: 'a@b.com', password: 'long-enough', name: 'A' })),
    ).rejects.toThrow('Taken.');
    expect(result.current.status).toBe('signed_out');
  });

  it('ends onboarding, then signs out', async () => {
    const { result } = await renderAuth();
    await act(() => result.current.signIn('a@b.com', 'pw'));
    expect(result.current).toMatchObject({ status: 'signed_in', onboarding: false });

    await act(() => result.current.signOut());

    expect(mocked.logout).toHaveBeenCalled();
    expect(result.current.status).toBe('signed_out');
  });

  it('moves to signed out, with a reason, when the API rejects the token', async () => {
    jest.mocked(getAuth).mockResolvedValue(saved);
    mocked.getProfile.mockResolvedValue({} as never);
    const { result } = await renderAuth();
    expect(result.current.status).toBe('signed_in');

    await act(async () => signedOutListener?.());

    expect(result.current).toMatchObject({ status: 'signed_out', notice: api.MESSAGES.expired });
  });
});
