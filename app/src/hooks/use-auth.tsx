import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  ApiError,
  getProfile,
  login,
  logout,
  MESSAGES,
  onSignedOut,
  register,
  updateProfile,
  type ProfileUpdate,
} from '@/lib/api';
import { getAuth } from '@/lib/storage';

export type AuthStatus = 'checking' | 'signed_out' | 'signed_in';

export type SignUpDetails = {
  email: string;
  password: string;
  name: string;
  roleTitle?: string;
  sells?: string;
};

type AuthValue = {
  status: AuthStatus;
  /** True from sign-up to the end of onboarding; it opens the onboarding steps. */
  onboarding: boolean;
  /** A message for the next screen, for example why the user was signed out. */
  notice: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (details: SignUpDetails) => Promise<void>;
  finishOnboarding: () => void;
  signOut: () => Promise<void>;
  clearNotice: () => void;
};

export const PROFILE_NOT_SAVED =
  'Your role and what you sell were not saved. You can add them in Profile.';

/**
 * Auto login. A saved token is checked with the API once, at launch. Only a
 * rejected token signs the user out: without a network the token is kept,
 * and each screen shows its own "try again".
 */
export async function restoreSession(): Promise<'signed_in' | 'signed_out'> {
  if (!(await getAuth())) return 'signed_out';
  try {
    await getProfile();
    return 'signed_in';
  } catch (error) {
    // On a 401 the API client has already cleared the token.
    return error instanceof ApiError && error.code === 'unauthorized' ? 'signed_out' : 'signed_in';
  }
}

const AuthContext = createContext<AuthValue | null>(null);

/**
 * The sign-in state of the app. The root layout shows screens by this state,
 * so a change here is all it takes to move the user to the right screen.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('checking');
  const [onboarding, setOnboarding] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void restoreSession().then((result) => {
      if (alive) setStatus(result);
    });
    // Without this, an expired session stays stuck on screens that can no
    // longer load anything.
    const stop = onSignedOut(() => {
      setOnboarding(false);
      setNotice(MESSAGES.expired);
      setStatus('signed_out');
    });
    return () => {
      alive = false;
      stop();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    await login(email.trim(), password);
    setNotice(null);
    setOnboarding(false);
    setStatus('signed_in');
  }, []);

  const signUp = useCallback(async (details: SignUpDetails) => {
    await register(details.email.trim(), details.password, details.name.trim());
    const changes: ProfileUpdate = {};
    if (details.roleTitle?.trim()) changes.role_title = details.roleTitle.trim();
    if (details.sells?.trim()) changes.sells = details.sells.trim();
    let message: string | null = null;
    if (Object.keys(changes).length > 0) {
      // The account exists now. A failure here must not leave the user on the
      // sign-up form, where a second try would say the email is taken.
      try {
        await updateProfile(changes);
      } catch {
        message = PROFILE_NOT_SAVED;
      }
    }
    setNotice(message);
    setOnboarding(true);
    setStatus('signed_in');
  }, []);

  const finishOnboarding = useCallback(() => setOnboarding(false), []);

  const signOut = useCallback(async () => {
    await logout();
    setNotice(null);
    setOnboarding(false);
    setStatus('signed_out');
  }, []);

  const clearNotice = useCallback(() => setNotice(null), []);

  const value = useMemo(
    () => ({
      status,
      onboarding,
      notice,
      signIn,
      signUp,
      finishOnboarding,
      signOut,
      clearNotice,
    }),
    [status, onboarding, notice, signIn, signUp, finishOnboarding, signOut, clearNotice],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthValue {
  const value = use(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
