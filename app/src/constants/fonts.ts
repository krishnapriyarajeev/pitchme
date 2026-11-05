/**
 * Newsreader for headings and numbers, IBM Plex Sans for everything else.
 *
 * A serif number reads as a considered note, not a grade on a dashboard.
 * Custom fonts on Android ignore fontWeight, so each weight is its own
 * family and the type scale picks the family, not the weight.
 */

import { IBMPlexSans_400Regular } from '@expo-google-fonts/ibm-plex-sans/400Regular';
import { IBMPlexSans_500Medium } from '@expo-google-fonts/ibm-plex-sans/500Medium';
import { IBMPlexSans_600SemiBold } from '@expo-google-fonts/ibm-plex-sans/600SemiBold';
import { Newsreader_400Regular } from '@expo-google-fonts/newsreader/400Regular';
import { Newsreader_500Medium } from '@expo-google-fonts/newsreader/500Medium';

export const Fonts = {
  serif: 'Newsreader_400Regular',
  serifMedium: 'Newsreader_500Medium',
  sans: 'IBMPlexSans_400Regular',
  sansMedium: 'IBMPlexSans_500Medium',
  sansSemiBold: 'IBMPlexSans_600SemiBold',
} as const;

/** Passed to useFonts in the root layout. Only these weights are bundled. */
export const FontFiles = {
  [Fonts.serif]: Newsreader_400Regular,
  [Fonts.serifMedium]: Newsreader_500Medium,
  [Fonts.sans]: IBMPlexSans_400Regular,
  [Fonts.sansMedium]: IBMPlexSans_500Medium,
  [Fonts.sansSemiBold]: IBMPlexSans_600SemiBold,
};
