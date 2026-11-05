import type { LocalFile, Profile } from '@/lib/api';

/** About this much speech gives a voice clone enough to work with. */
export const TARGET_SECONDS = 20;
/** A shorter take is most likely a tap by mistake. */
export const MIN_SECONDS = 8;

/**
 * The text to read for the voice sample. It uses the user's own name, role
 * and product where we have them, so it sounds like their real calls.
 */
export function voicePassage(
  profile?: Pick<Profile, 'display_name' | 'role_title' | 'sells'> | null,
): string {
  const who = [profile?.display_name?.trim(), profile?.role_title?.trim()]
    .filter(Boolean)
    .join(', ');
  const product = profile?.sells?.trim();
  const opening = who ? `I'm ${who}. ` : '';
  const what = product ? `I sell ${product}, and I have ` : 'I have ';
  return (
    `${opening}${what}learned that the difference between a good call and a wasted one is ` +
    'preparation. When a buyer pushes back on price, I want the exact numbers ready, not ' +
    'adjectives. When they ask about delivery, I want a date. This is my normal speaking ' +
    'voice, at my normal pace.'
  );
}

/**
 * The recording as an upload. On a phone the file is an .m4a; in a browser
 * it is a blob URL with no name, recorded as WebM.
 */
export function voiceFile(uri: string): LocalFile {
  const match = /\.(m4a|wav|mp3|webm|ogg)$/i.exec(uri.split('?')[0] ?? '');
  const extension = match?.[1]?.toLowerCase() ?? 'webm';
  const types: Record<string, string> = {
    m4a: 'audio/mp4',
    wav: 'audio/wav',
    mp3: 'audio/mpeg',
    webm: 'audio/webm',
    ogg: 'audio/ogg',
  };
  return { uri, name: `voice.${extension}`, mimeType: types[extension] };
}
