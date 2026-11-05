import { ApiError, MESSAGES } from '@/lib/api';
import { checkSignIn, checkSignUp, formError, handedOverEmail, handOverEmail } from '@/lib/forms';

describe('checkSignUp', () => {
  it('passes a complete form', () => {
    expect(checkSignUp({ name: 'Jo', email: 'jo@saber.com', password: 'long-enough' })).toEqual({});
  });

  it('names each missing or short field', () => {
    expect(checkSignUp({ name: ' ', email: 'jo@', password: '' })).toEqual({
      display_name: 'Add the name the buyer should call you.',
      email: 'Add an email address such as you@company.com.',
      password: 'Choose a password of at least 8 characters.',
    });
    expect(checkSignUp({ name: 'Jo', email: 'jo@saber.com', password: 'short' }).password).toBe(
      'Use at least 8 characters.',
    );
  });
});

describe('checkSignIn', () => {
  it('asks for an email and a password, of any length', () => {
    expect(checkSignIn({ email: ' jo@saber.com ', password: 'x' })).toEqual({});
    expect(Object.keys(checkSignIn({ email: 'jo', password: '' }))).toEqual(['email', 'password']);
  });
});

describe('formError', () => {
  it('puts field messages under the fields the screen shows', () => {
    const error = new ApiError(422, 'validation', MESSAGES.invalid, {
      email: 'Not a valid email.',
      display_name: 'Too long.',
    });
    expect(formError(error, ['email'])).toEqual({
      message: 'Too long.',
      fields: { email: 'Not a valid email.' },
    });
  });

  it('keeps the message of any other error', () => {
    expect(formError(new ApiError(401, 'invalid_credentials', 'Wrong.'), ['email'])).toEqual({
      message: 'Wrong.',
      fields: {},
    });
    expect(formError(new Error('boom'), []).message).toBe(MESSAGES.server);
  });
});

it('hands an email from sign-up to sign-in in memory', () => {
  expect(handedOverEmail()).toBe('');
  handOverEmail(' jo@saber.com ');
  expect(handedOverEmail()).toBe('jo@saber.com');
});
