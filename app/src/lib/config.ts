/**
 * Where the API is. Set EXPO_PUBLIC_API_URL in app/.env (see .env.example,
 * or run scripts/use-lan-ip.sh). Expo puts the value into the bundle at
 * build time, so restart Metro after a change.
 */
export const API_URL: string | null = cleanUrl(process.env.EXPO_PUBLIC_API_URL);

export function cleanUrl(value: string | undefined): string | null {
  const trimmed = value?.trim().replace(/\/+$/, '');
  return trimmed ? trimmed : null;
}
