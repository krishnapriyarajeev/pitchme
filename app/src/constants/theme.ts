/**
 * Plum and Sage: the PitchMe palette, spacing and radius scale.
 *
 * The app coaches; it does not grade. There is no red anywhere. Terra and
 * gold mark things to correct before the real call, never a score.
 */

export const Colors = {
  light: {
    background: '#F8F5F0',
    surface: '#FFFFFF',
    surfaceAlt: '#F0EAE2',
    surfaceSunken: '#E9E2D8',

    text: '#2A2028',
    textSecondary: '#6B5C66',
    textSubtle: '#9A8D95',
    placeholder: '#B3A8AE',

    accent: '#4A2B44',
    accentPressed: '#382034',
    accentSoft: '#EFE6EC',
    onAccent: '#FFFFFF',

    sage: '#7C9885',
    sageDeep: '#4F7D60',
    sageSoft: '#E7EFE8',
    sageText: '#3B5F49',

    border: '#E3DAD0',
    hairline: '#EFE9E1',
    borderStrong: '#CBBFC6',

    // A claim the playbook does not support, or a price quoted wrong.
    terra: '#A05C3E',
    terraText: '#7E4529',
    terraSoft: '#F7EBE2',
    // A part that is short of where it should be.
    gold: '#B5872F',
    goldText: '#7F5D18',
    goldSoft: '#F5EBD8',
  },
  dark: {
    background: '#1A141A',
    surface: '#241C24',
    surfaceAlt: '#2C232C',
    surfaceSunken: '#322838',

    text: '#F2EDEF',
    textSecondary: '#A79BA3',
    textSubtle: '#8A7D86',
    placeholder: '#6E6270',

    accent: '#B98FAC',
    accentPressed: '#CDA9C2',
    accentSoft: '#31243040',
    onAccent: '#1A141A',

    sage: '#8FBF9E',
    sageDeep: '#8FBF9E',
    sageSoft: '#20302610',
    sageText: '#A8CDB4',

    // Lighter than a plain step up from the ground: on near-black, a text
    // field's outline is the only thing that marks it as an input.
    border: '#473C46',
    hairline: '#332A33',
    borderStrong: '#5C4D5A',

    // Brighter than the light values; at the same saturation they read as
    // mud on the dark ground.
    terra: '#D19571',
    terraText: '#E8B695',
    terraSoft: '#3A251A60',
    gold: '#D9B368',
    goldText: '#E8CE94',
    goldSoft: '#3A301660',
  },
} as const;

export type Scheme = keyof typeof Colors;
export type Palette = { readonly [K in keyof typeof Colors.light]: string };
export type ThemeColor = keyof Palette;

/**
 * The call room. It stands in for a camera feed, so it is the same in both
 * schemes and is not the dark palette.
 */
export const Camera = {
  top: '#322A32',
  mid: '#241C24',
  bottom: '#171117',
  accent: '#A8CDB4',
  // The live dot. Terra, not red.
  live: '#A05C3E',
  text: '#FFFFFF',
  textMuted: 'rgba(255,255,255,0.62)',
  scrim: 'rgba(0,0,0,0.42)',
  chip: 'rgba(255,255,255,0.13)',
} as const;

/** Radius carries hierarchy: the bigger the surface, the rounder it is. */
export const Radius = {
  nested: 10,
  control: 12,
  card: 14,
  hero: 18,
  pill: 999,
} as const;

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
  /** The same side margin on every screen. */
  gutter: 20,
} as const;

/** The smallest tap area. Icons are drawn smaller and padded up to this. */
export const HitTarget = 44;

/** On a tablet or the web, content stops growing at this width. */
export const MaxContentWidth = 640;
