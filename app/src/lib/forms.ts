import { ApiError, messageOf } from '@/lib/api';

export type FieldErrors = Record<string, string>;

export const PASSWORD_MIN = 8;

/** The same rules the API checks, so most mistakes show before a request. */
export function checkSignUp(input: { name: string; email: string; password: string }): FieldErrors {
  const errors: FieldErrors = {};
  if (!input.name.trim()) errors.display_name = 'Add the name the buyer should call you.';
  Object.assign(errors, checkSignIn(input));
  if (input.password.length < PASSWORD_MIN) {
    errors.password = input.password
      ? `Use at least ${PASSWORD_MIN} characters.`
      : `Choose a password of at least ${PASSWORD_MIN} characters.`;
  }
  return errors;
}

let lastEmail: string | null = null;

/**
 * Carries an email from sign-up to sign-in (after "Sign in instead") in
 * memory. A route param would put the address in the web URL and history.
 */
export function handOverEmail(email: string): void {
  lastEmail = email.trim();
}

export function handedOverEmail(): string {
  return lastEmail ?? '';
}

export function checkSignIn(input: { email: string; password: string }): FieldErrors {
  const errors: FieldErrors = {};
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.email.trim())) {
    errors.email = 'Add an email address such as you@company.com.';
  }
  if (!input.password) errors.password = 'Add your password.';
  return errors;
}

/**
 * Splits an error into messages under the fields the screen shows, and one
 * message for everything else. A 422 on a field the screen does not show
 * still reaches the user.
 */
export function formError(
  error: unknown,
  shown: readonly string[],
): { message: string | null; fields: FieldErrors } {
  if (!(error instanceof ApiError) || error.code !== 'validation') {
    return { message: messageOf(error), fields: {} };
  }
  const fields: FieldErrors = {};
  const other: string[] = [];
  for (const [name, text] of Object.entries(error.fields)) {
    if (shown.includes(name)) fields[name] = text;
    else other.push(text);
  }
  return { message: other.length > 0 ? other.join(' ') : null, fields };
}
