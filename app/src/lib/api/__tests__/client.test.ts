import { ApiError, MESSAGES, messageOf, onSignedOut, request } from '@/lib/api/client';
import { clearAuth, getToken } from '@/lib/storage';

let mockApiUrl: string | null = 'http://api.test';

jest.mock('@/lib/config', () => ({
  get API_URL() {
    return mockApiUrl;
  },
}));
jest.mock('@/lib/storage', () => ({ getToken: jest.fn(), clearAuth: jest.fn() }));

const fetchMock = jest.fn();
global.fetch = fetchMock as unknown as typeof fetch;

function reply(status: number, body?: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json:
      body === undefined
        ? () => Promise.reject(new SyntaxError('no body'))
        : () => Promise.resolve(body),
  };
}

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  const error = await promise.then(
    () => null,
    (caught: unknown) => caught,
  );
  expect(error).toBeInstanceOf(ApiError);
  return error as ApiError;
}

beforeEach(() => {
  jest.clearAllMocks();
  mockApiUrl = 'http://api.test';
  jest.mocked(getToken).mockResolvedValue('token-1');
});

describe('request', () => {
  it('sends JSON with the bearer token and reads the reply', async () => {
    fetchMock.mockResolvedValue(reply(200, { id: 'u1' }));

    await expect(
      request('/api/profile', { method: 'PUT', body: { sells: 'CRM' } }),
    ).resolves.toEqual({ id: 'u1' });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('http://api.test/api/profile');
    expect(init.method).toBe('PUT');
    expect(init.body).toBe('{"sells":"CRM"}');
    expect(init.headers).toMatchObject({
      Authorization: 'Bearer token-1',
      'Content-Type': 'application/json',
    });
  });

  it('leaves the token out when auth is off', async () => {
    fetchMock.mockResolvedValue(reply(200, {}));
    await request('/api/auth/login', { method: 'POST', body: {}, auth: false });
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
    expect(getToken).not.toHaveBeenCalled();
  });

  it('returns nothing for 204', async () => {
    fetchMock.mockResolvedValue(reply(204));
    await expect(request('/x', { method: 'POST' })).resolves.toBeUndefined();
  });

  it('fails clearly with no API address, and sends nothing', async () => {
    mockApiUrl = null;
    const error = await failure(request('/api/profile'));
    expect(error.code).toBe('not_configured');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('turns a dropped connection into a network error', async () => {
    fetchMock.mockRejectedValue(new TypeError('Network request failed'));
    const error = await failure(request('/api/profile'));
    expect([error.status, error.code, error.message]).toEqual([0, 'network', MESSAGES.network]);
  });

  it('gives up after the timeout', async () => {
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () =>
            reject(Object.assign(new Error('aborted'), { name: 'AbortError' })),
          );
        }),
    );
    const error = await failure(request('/api/profile', { timeoutMs: 10 }));
    expect(error.code).toBe('timeout');
  });
});

describe('errors', () => {
  it('keeps the API message and code', async () => {
    fetchMock.mockResolvedValue(
      reply(409, { detail: 'That email already has an account.', code: 'email_taken' }),
    );
    const error = await failure(request('/api/auth/register', { method: 'POST', auth: false }));
    expect([error.status, error.code, error.message]).toEqual([
      409,
      'email_taken',
      'That email already has an account.',
    ]);
  });

  it('names each field to change on a 422', async () => {
    fetchMock.mockResolvedValue(
      reply(422, {
        detail: [
          { loc: ['body', 'password'], msg: 'String should have at least 8 characters' },
          { loc: ['body', 'deal_stage'], msg: "Value error, unknown deal stage 'x'" },
        ],
      }),
    );
    const error = await failure(request('/api/sessions', { method: 'POST' }));
    expect(error.code).toBe('validation');
    expect(error.fields).toEqual({
      password: 'String should have at least 8 characters',
      deal_stage: "Unknown deal stage 'x'",
    });
  });

  it('gives a plain message for a server error with no body', async () => {
    fetchMock.mockResolvedValue(reply(502));
    const error = await failure(request('/api/sessions'));
    expect([error.code, error.message]).toEqual(['server', MESSAGES.server]);
  });

  it('falls back to a general message for errors that are not ApiError', () => {
    expect(messageOf(new Error('boom'))).toBe(MESSAGES.server);
    expect(messageOf(new ApiError(404, 'not_found', 'No such session.'))).toBe('No such session.');
  });
});

describe('a rejected token', () => {
  it('clears the sign-in and tells the listeners', async () => {
    const listener = jest.fn();
    const stop = onSignedOut(listener);
    fetchMock.mockResolvedValue(reply(401, { detail: 'Token expired', code: 'unauthorized' }));

    const error = await failure(request('/api/profile'));

    expect(error.message).toBe(MESSAGES.expired);
    expect(clearAuth).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledTimes(1);
    stop();
  });

  it('does not sign out on a wrong password', async () => {
    const listener = jest.fn();
    const stop = onSignedOut(listener);
    fetchMock.mockResolvedValue(
      reply(401, { detail: 'Wrong email or password.', code: 'invalid_credentials' }),
    );

    const error = await failure(request('/api/auth/login', { method: 'POST', auth: false }));

    expect([error.code, error.message]).toEqual([
      'invalid_credentials',
      'Wrong email or password.',
    ]);
    expect(clearAuth).not.toHaveBeenCalled();
    expect(listener).not.toHaveBeenCalled();
    stop();
  });
});
