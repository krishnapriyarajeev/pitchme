import { Colors, type Palette, type Scheme } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';

export function useScheme(): Scheme {
  return useColorScheme() === 'dark' ? 'dark' : 'light';
}

/** The palette for the current light or dark scheme. */
export function useTheme(): Palette {
  return Colors[useScheme()];
}
