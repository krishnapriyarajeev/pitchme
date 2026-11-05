import { Bands, Correction, type Band, type BandStyle } from '@/constants/bands';
import { useScheme } from '@/hooks/use-theme';

export function useBands(): Record<Band, BandStyle> {
  return Bands[useScheme()];
}

export function useCorrectionStyle() {
  return Correction[useScheme()];
}
