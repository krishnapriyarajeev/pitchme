import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { GlowRing } from '@/components/motion/glow-ring';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/icon';
import { Text } from '@/components/ui/text';
import { Camera, Radius } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { formatClock } from '@/lib/format';
import { MIN_SECONDS, TARGET_SECONDS } from '@/lib/voice';

const BUTTON = 64;

type Props = {
  passage: string;
  /** The finished take, or null while there is none or a new one runs. */
  onTake: (take: { uri: string; seconds: number } | null) => void;
  disabled?: boolean;
};

/**
 * Records the voice sample. The booth is the one dark surface in onboarding,
 * the same in both schemes, as the call room is.
 */
export function VoiceRecorder({ passage, onTake, disabled }: Props) {
  const theme = useTheme();
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const state = useAudioRecorderState(recorder, 250);
  const [take, setTake] = useState<{ uri: string; seconds: number } | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const player = useAudioPlayer(take?.uri ?? null);
  const playback = useAudioPlayerStatus(player);

  const seconds = Math.floor(state.durationMillis / 1000);
  const recording = state.isRecording;

  async function start() {
    setProblem(null);
    const permission = await requestRecordingPermissionsAsync();
    if (!permission.granted) {
      setProblem(
        'PitchMe needs the microphone to record your sample. Turn it on in Settings, then try again.',
      );
      return;
    }
    if (playback.playing) player.pause();
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    await recorder.prepareToRecordAsync();
    setTake(null);
    onTake(null);
    recorder.record();
  }

  async function stop() {
    const length = Math.floor(recorder.getStatus().durationMillis / 1000);
    await recorder.stop();
    await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
    if (!recorder.uri) {
      setProblem('The recording did not save. Try again.');
      return;
    }
    if (length < MIN_SECONDS) {
      setProblem(`That take was ${length} s. Read the whole text, about ${TARGET_SECONDS} s.`);
      return;
    }
    const next = { uri: recorder.uri, seconds: length };
    setTake(next);
    onTake(next);
  }

  function listen() {
    if (playback.playing) {
      player.pause();
      return;
    }
    if (playback.didJustFinish || playback.currentTime >= playback.duration) player.seekTo(0);
    player.play();
  }

  const caption = recording
    ? seconds < TARGET_SECONDS
      ? `${formatClock(seconds)}  Keep reading, to about ${TARGET_SECONDS} s`
      : `${formatClock(seconds)}  Tap to finish`
    : take
      ? `${formatClock(take.seconds)} recorded. Tap to record again.`
      : 'Tap to start recording';

  return (
    <View style={styles.booth}>
      <View style={styles.script}>
        <Text variant="body" style={styles.scriptText}>
          “{passage}”
        </Text>
      </View>

      <View style={styles.control}>
        {recording ? <GlowRing size={BUTTON} color={Camera.live} /> : null}
        <Pressable
          onPress={recording ? stop : start}
          disabled={disabled}
          accessibilityRole="button"
          accessibilityLabel={recording ? 'Stop recording' : 'Start recording'}
          style={({ pressed }) => [
            styles.button,
            {
              backgroundColor: recording ? Camera.live : theme.accent,
              opacity: disabled ? 0.5 : pressed ? 0.85 : 1,
            },
          ]}>
          {recording ? (
            <View style={styles.stop} />
          ) : (
            <Icon name="mic" size={26} color="#FFFFFF" strokeWidth={2} />
          )}
        </Pressable>
      </View>

      <Text variant="secondary" color={Camera.textMuted} accessibilityLiveRegion="polite">
        {caption}
      </Text>
      {problem ? (
        <Text variant="secondary" color={Camera.accent} style={styles.problem}>
          {problem}
        </Text>
      ) : null}

      {take && !recording ? (
        <Button
          label={playback.playing ? 'Pause' : 'Listen back'}
          icon={playback.playing ? 'pause' : 'play'}
          variant="text"
          onPress={listen}
          style={styles.listen}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  booth: {
    backgroundColor: Camera.mid,
    borderRadius: Radius.card,
    padding: 18,
    alignItems: 'center',
    gap: 10,
  },
  script: {
    alignSelf: 'stretch',
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderRadius: Radius.control,
    paddingVertical: 13,
    paddingHorizontal: 15,
  },
  scriptText: { fontStyle: 'italic', color: 'rgba(255,255,255,0.82)' },
  control: {
    marginTop: 10,
    width: BUTTON,
    height: BUTTON,
    alignItems: 'center',
    justifyContent: 'center',
  },
  button: {
    width: BUTTON,
    height: BUTTON,
    borderRadius: BUTTON / 2,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.15)',
  },
  stop: { width: 22, height: 22, borderRadius: 5, backgroundColor: '#FFFFFF' },
  problem: { textAlign: 'center' },
  listen: { height: 40, alignSelf: 'center' },
});
