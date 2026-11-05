import { voiceFile, voicePassage } from '@/lib/voice';

describe('voicePassage', () => {
  it('uses the name, role and product the user gave', () => {
    const text = voicePassage({
      display_name: 'Jo Bennett',
      role_title: 'Account executive',
      sells: 'payroll software',
    });
    expect(text.startsWith("I'm Jo Bennett, Account executive. I sell payroll software, and")).toBe(
      true,
    );
  });

  it('reads well with nothing known', () => {
    expect(voicePassage(null).startsWith('I have learned that')).toBe(true);
    expect(voicePassage({ display_name: ' ', role_title: null, sells: '' })).toBe(
      voicePassage(undefined),
    );
  });
});

describe('voiceFile', () => {
  it('keeps the extension of a phone recording', () => {
    expect(voiceFile('file:///cache/recording-1.m4a')).toEqual({
      uri: 'file:///cache/recording-1.m4a',
      name: 'voice.m4a',
      mimeType: 'audio/mp4',
    });
  });

  it('treats a browser blob URL as WebM', () => {
    expect(voiceFile('blob:http://localhost/42')).toMatchObject({
      name: 'voice.webm',
      mimeType: 'audio/webm',
    });
  });
});
