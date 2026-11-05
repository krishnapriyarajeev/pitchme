/**
 * The request core: base URL, bearer token, timeouts and errors.
 *
 * There is no mock mode. With no API address set, every call fails with a
 * clear "not_configured" error, so the app never shows data that is not
 * real. Every failure is an ApiError with a message the user can act on.
 */

import { API_URL } from '@/lib/config';
import { clearAuth, getToken } from '@/lib/storage';

const TIMEOUT_MS = 20_000;

export type ApiErrorCode =
  | 'not_configured'
  | 'network'
  | 'timeout'
  | 'unauthorized'
  | 'validation'
  | 'server'
  // Any `code` the API sends, for example "email_taken" or "not_found".
  | (string & {});

export class ApiError extends Error {
  constructor(
    /** The HTTP status, or 0 when no response came back. */
    readonly status: number,
    readonly code: ApiErrorCode,
    message: string,
    /** For a 422: what to change in each field, by field name. */
    readonly fields: Readonly<Record<string, string>> = {},
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const MESSAGES = {
  notConfigured: 'The app has no server address. Set EXPO_PUBLIC_API_URL in app/.env.',
  network: 'Could not reach PitchMe. Check your connection and try again.',
  timeout: 'PitchMe took too long to answer. Try again.',
  expired: 'Your sign-in has expired. Sign in again.',
  server: 'PitchMe had a problem on its side. Try again in a minute.',
  invalid: 'Some details need a change.',
} as const;

// ---- sign-out on 401 ----

type Listener = () => void;
const signedOut = new Set<Listener>();

/**
 * Called when the API rejects the saved token (it expired, or the user was
 * removed). The token is already cleared; the listener only has to go to
 * the sign-in screen. Returns a function that stops the listener.
 */
export function onSignedOut(listener: Listener): () => void {
  signedOut.add(listener);
  return () => {
    signedOut.delete(listener);
  };
}

// ---- requests ----

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  /** Sent as JSON. */
  body?: unknown;
  /** Send the saved token. Off for sign-in and register. */
  auth?: boolean;
  timeoutMs?: number;
};

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, timeoutMs = TIMEOUT_MS } = options;
  if (!API_URL) throw new ApiError(0, 'not_configured', MESSAGES.notConfigured);

  const token = auth ? await getToken() : null;
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (error) {
    const aborted = error instanceof Error && error.name === 'AbortError';
    throw aborted
      ? new ApiError(0, 'timeout', MESSAGES.timeout)
      : new ApiError(0, 'network', MESSAGES.network);
  } finally {
    clearTimeout(timer);
  }

  if (response.status === 401 && token) {
    // Only a rejected token signs the user out. A 401 from the sign-in form
    // itself is a wrong password, and gets its own message below.
    await clearAuth();
    signedOut.forEach((listener) => listener());
    throw new ApiError(401, 'unauthorized', MESSAGES.expired);
  }
  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

type ErrorBody = {
  detail?: string | { loc?: (string | number)[]; msg?: string }[];
  code?: string;
};

/** Turns an error response into an ApiError with a usable message. */
export async function toError(response: Response): Promise<ApiError> {
  let body: ErrorBody = {};
  try {
    body = (await response.json()) as ErrorBody;
  } catch {
    // Not JSON, for example a proxy's HTML error page.
  }
  const { status } = response;

  if (Array.isArray(body.detail)) {
    const fields: Record<string, string> = {};
    for (const item of body.detail) {
      const field = item.loc?.filter((part) => part !== 'body').join('.') || 'form';
      if (item.msg && !fields[field]) fields[field] = cleanMessage(item.msg);
    }
    return new ApiError(status, 'validation', MESSAGES.invalid, fields);
  }
  if (typeof body.detail === 'string' && body.detail) {
    return new ApiError(status, body.code ?? codeFor(status), body.detail);
  }
  return new ApiError(
    status,
    codeFor(status),
    status >= 500 ? MESSAGES.server : `The request failed (${status}).`,
  );
}

function codeFor(status: number): ApiErrorCode {
  if (status === 401) return 'unauthorized';
  if (status === 422) return 'validation';
  if (status >= 500) return 'server';
  return `http_${status}`;
}

/** Pydantic says "Value error, unknown deal stage"; the user needs the rest. */
function cleanMessage(message: string): string {
  const text = message.replace(/^Value error, /, '');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : MESSAGES.server;
}

export type Health = { status: string; version: string };

/** A quick check that the API answers, for the start screen. */
export function getHealth(): Promise<Health> {
  return request<Health>('/health', { auth: false, timeoutMs: 5_000 });
}
