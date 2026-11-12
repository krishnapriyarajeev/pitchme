import { fireEvent, render, screen } from '@testing-library/react-native';

import { ObjectionCard } from '@/components/debrief/objection-card';
import type { Objection } from '@/lib/debrief';

jest.mock('expo-audio', () => ({
  useAudioPlayer: () => ({ play: jest.fn(), pause: jest.fn(), seekTo: jest.fn() }),
  // The player reports seconds, not milliseconds.
  useAudioPlayerStatus: () => ({ playing: false, currentTime: 3, duration: 65 }),
}));

const item: Objection = {
  question: 'What does it cost per seat?',
  said: 'It is affordable.',
  verdict: 'dodged',
  why: 'The price was asked and not given.',
  evidence: 'Pricing: 40 USD per seat',
  atMs: 72_000,
  stronger: {
    question: 'What does it cost per seat?',
    original: 'It is affordable.',
    stronger: 'It is 40 dollars a seat, billed yearly.',
    change: 'Gave the price.',
    citation: 'Pricing',
    verified: false,
    unsupported_numbers: ['yearly'],
    t_start_ms: 72_000,
    audio_url: null,
  },
};

it('opens to show what was said and a stronger answer', async () => {
  await render(<ObjectionCard item={item} hasVoice={false} />);
  expect(screen.getByText('Answer it next time')).toBeTruthy();
  expect(screen.queryByText('A STRONGER ANSWER')).toBeNull();

  await fireEvent.press(screen.getByRole('button'));

  expect(screen.getByText('YOU SAID · 1:12')).toBeTruthy();
  expect(screen.getByText('“It is 40 dollars a seat, billed yearly.”')).toBeTruthy();
  expect(screen.getByText(/yearly is not\s+in your playbook/)).toBeTruthy();
  expect(
    screen.getByText('Record a voice sample in Profile to hear this in your own voice.'),
  ).toBeTruthy();
});

it('plays the stronger answer in the user’s voice, with a clock in seconds', async () => {
  const withAudio = {
    ...item,
    stronger: { ...item.stronger!, audio_url: 'http://s3/answer-0.wav', unsupported_numbers: [] },
  };
  await render(<ObjectionCard item={withAudio} hasVoice startOpen />);
  expect(screen.getByLabelText('Play the stronger answer in your voice')).toBeTruthy();
  expect(screen.getByText('0:03 / 1:05')).toBeTruthy();
});

it('says when a question went unanswered', async () => {
  await render(<ObjectionCard item={{ ...item, said: '', stronger: null }} hasVoice startOpen />);
  expect(screen.getByText('This one went unanswered.')).toBeTruthy();
});
