/**
 * Score bands.
 *
 * A low score is the next thing to work on, not a failure, so the lowest band
 * is russet and says "Needs work". Never show a band as colour alone: every
 * pill carries its label.
 */

import type { Scheme } from './theme';

export type Band = 'strong' | 'steady' | 'focus';

export type BandStyle = {
  /** Bars, rings and underlines. */
  bar: string;
  /** Pill background. */
  tint: string;
  /** Pill text; darker than `bar` so it has contrast on `tint`. */
  text: string;
  label: string;
};

export const Bands: Record<Scheme, Record<Band, BandStyle>> = {
  light: {
    strong: { bar: '#4F7D60', tint: '#E7EFE8', text: '#3B5F49', label: 'Strong' },
    steady: { bar: '#B5872F', tint: '#F5EBD8', text: '#7F5D18', label: 'Getting there' },
    focus: { bar: '#A05C3E', tint: '#F3E4DA', text: '#7E4529', label: 'Needs work' },
  },
  dark: {
    strong: { bar: '#8FBF9E', tint: '#20302699', text: '#A8CDB4', label: 'Strong' },
    steady: { bar: '#D9A94E', tint: '#33291699', text: '#E0BC72', label: 'Getting there' },
    focus: { bar: '#C4805C', tint: '#33231A99', text: '#D69A78', label: 'Needs work' },
  },
};

/** The pitch-integrity card: a correction to make, the loudest surface. */
export const Correction: Record<Scheme, { background: string; border: string; text: string }> = {
  light: { background: '#F7EBE2', border: '#E7D2C3', text: '#6E4630' },
  dark: { background: '#2E211B', border: '#4A362B', text: '#D9B29A' },
};

export const BAND_STRONG = 80;
export const BAND_STEADY = 65;

/** Scores are 0 to 100, as the API sends them. */
export function bandFor(score: number): Band {
  if (score >= BAND_STRONG) return 'strong';
  if (score >= BAND_STEADY) return 'steady';
  return 'focus';
}
