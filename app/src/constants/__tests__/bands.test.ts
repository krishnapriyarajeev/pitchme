import { BAND_STEADY, BAND_STRONG, Bands, bandFor } from '@/constants/bands';

describe('bandFor', () => {
  it('splits scores at the band edges', () => {
    expect(bandFor(100)).toBe('strong');
    expect(bandFor(BAND_STRONG)).toBe('strong');
    expect(bandFor(BAND_STRONG - 1)).toBe('steady');
    expect(bandFor(BAND_STEADY)).toBe('steady');
    expect(bandFor(BAND_STEADY - 1)).toBe('focus');
    expect(bandFor(0)).toBe('focus');
  });

  it('never calls a band poor or failed', () => {
    const labels = Object.values(Bands).flatMap((scheme) =>
      Object.values(scheme).map((band) => band.label.toLowerCase()),
    );
    for (const word of ['poor', 'fail', 'bad', 'weak']) {
      expect(labels.some((label) => label.includes(word))).toBe(false);
    }
  });
});
