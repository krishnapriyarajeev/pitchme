import {
  AudioSession,
  BarVisualizer,
  LiveKitRoom,
  registerGlobals,
  useConnectionState,
  useLocalParticipant,
  useRoomContext,
  useVoiceAssistant,
  VideoTrack,
} from '@livekit/react-native';
import { ConnectionState, Track } from 'livekit-client';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Pulse } from '@/components/motion/pulse';
import { Icon } from '@/components/ui/icon';
import { IconButton } from '@/components/ui/icon-button';
import { Text } from '@/components/ui/text';
import { Camera, Radius } from '@/constants/theme';
import type { PendingCall } from '@/lib/call-store';
import { formatClock } from '@/lib/format';

// WebRTC's globals must exist before a Room is made.
registerGlobals();

/** The longest call; the buyer then says goodbye (REHEARSAL_MAX_MINUTES). */
const MAX_MINUTES = 20;

type Props = {
  call: PendingCall;
  /** The call is over: the user ended it, or the room closed. */
  onEnd: () => void;
};

/**
 * The live call. Camera and microphone go into the room; the recording is
 * made on the server, so nothing is uploaded from the phone afterwards.
 */
export function CallRoom({ call, onEnd }: Props) {
  // Plays the buyer on the speaker, not the earpiece.
  useEffect(() => {
    void AudioSession.startAudioSession();
    return () => {
      void AudioSession.stopAudioSession();
    };
  }, []);

  return (
    <LiveKitRoom
      serverUrl={call.livekit_url}
      token={call.token}
      connect
      audio
      video
      onDisconnected={onEnd}>
      <CallSurface call={call} onEnd={onEnd} />
    </LiveKitRoom>
  );
}

function CallSurface({ call, onEnd }: Props) {
  const insets = useSafeAreaInsets();
  const room = useRoomContext();
  const connection = useConnectionState();
  const { localParticipant, cameraTrack } = useLocalParticipant();
  const assistant = useVoiceAssistant();
  const [muted, setMuted] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const connected = connection === ConnectionState.Connected;

  // The clock starts when the room connects, not when the screen opens.
  useEffect(() => {
    if (!connected) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 500);
    return () => clearInterval(timer);
  }, [connected]);

  async function toggleMute() {
    const next = !muted;
    setMuted(next);
    await localParticipant.setMicrophoneEnabled(!next);
  }

  async function end() {
    // The buyer's worker sees the user leave and reports the call.
    await room.disconnect();
    onEnd();
  }

  const lastSaid = assistant.agentTranscriptions.at(-1)?.text?.trim();
  const firstName = call.buyer.name.split(' ')[0] ?? call.buyer.name;
  const left = MAX_MINUTES * 60 - elapsed;

  return (
    <View style={styles.root}>
      {cameraTrack ? (
        <VideoTrack
          trackRef={{
            participant: localParticipant,
            publication: cameraTrack,
            source: Track.Source.Camera,
          }}
          style={StyleSheet.absoluteFill}
          objectFit="cover"
          mirror
        />
      ) : (
        <View style={[StyleSheet.absoluteFill, styles.noCamera]} />
      )}

      <View style={[styles.top, { paddingTop: insets.top + 12 }]}>
        <View style={styles.buyer}>
          <View style={styles.avatar}>
            <Icon name="user" size={15} color={Camera.accent} strokeWidth={1.6} />
          </View>
          <View style={styles.buyerText}>
            <Text variant="rowTitle" color={Camera.text} numberOfLines={1}>
              {call.buyer.name}
            </Text>
            <Text variant="secondary" color={Camera.textMuted} numberOfLines={1}>
              {connected ? call.buyer.company : 'Connecting'}
            </Text>
          </View>
        </View>
        <View style={styles.live}>
          <Pulse>
            <View style={styles.liveDot} />
          </Pulse>
          <Text variant="pill" color={Camera.text}>
            {formatClock(elapsed)}
          </Text>
        </View>
      </View>

      <View style={styles.middle}>
        {assistant.audioTrack ? (
          <BarVisualizer
            trackRef={assistant.audioTrack}
            state={assistant.state}
            barCount={9}
            style={styles.bars}
            options={{ minHeight: 6 }}
          />
        ) : null}
        <View style={styles.says} accessibilityLiveRegion="polite">
          <Text variant="pill" color={Camera.accent}>
            {stateLabel(assistant.state, connected, firstName).toUpperCase()}
          </Text>
          <Text variant="cardTitle" color={Camera.text} style={styles.saysText}>
            {lastSaid
              ? `“${lastSaid}”`
              : `${firstName} speaks first. Answer as you would on the real call.`}
          </Text>
        </View>
      </View>

      <View style={[styles.bottom, { paddingBottom: insets.bottom + 18 }]}>
        {connected && left <= 120 ? (
          <Text variant="secondary" color={Camera.accent} style={styles.centred}>
            {formatClock(Math.max(0, left))} left. {firstName} will wrap up soon.
          </Text>
        ) : (
          <Text variant="secondary" color={Camera.textMuted} style={styles.centred}>
            {call.buyer.manner ? `${call.buyer.manner}. ` : ''}End the call when you are done.
          </Text>
        )}
        <View style={styles.controls}>
          <IconButton
            name="mic"
            size={21}
            color={muted ? Camera.live : Camera.text}
            onPress={toggleMute}
            accessibilityLabel={muted ? 'Turn your microphone on' : 'Mute your microphone'}
            style={styles.square}
          />
          <Pressable
            onPress={end}
            accessibilityRole="button"
            accessibilityLabel="End the call"
            style={({ pressed }) => [styles.end, { opacity: pressed ? 0.85 : 1 }]}>
            <View style={styles.stop} />
          </Pressable>
          <View style={[styles.square, styles.hidden]} />
        </View>
      </View>
    </View>
  );
}

function stateLabel(state: string, connected: boolean, firstName: string): string {
  if (!connected) return 'Joining';
  switch (state) {
    case 'speaking':
      return `${firstName} says`;
    case 'thinking':
      return 'Thinking';
    case 'listening':
      return 'Listening';
    default:
      return `Waiting for ${firstName}`;
  }
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Camera.bottom },
  noCamera: { backgroundColor: Camera.mid },
  top: {
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  buyer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    backgroundColor: Camera.scrim,
    borderRadius: Radius.card,
    paddingVertical: 8,
    paddingHorizontal: 11,
    maxWidth: '70%',
  },
  avatar: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: 'rgba(124,152,133,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  buyerText: { flexShrink: 1, minWidth: 0 },
  live: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    backgroundColor: Camera.scrim,
    borderRadius: Radius.pill,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  liveDot: { width: 7, height: 7, borderRadius: 3.5, backgroundColor: Camera.live },
  middle: { flex: 1, justifyContent: 'center', paddingHorizontal: 22, gap: 16 },
  bars: { height: 24, width: 120, alignSelf: 'center' },
  says: {
    backgroundColor: Camera.scrim,
    borderWidth: 1,
    borderColor: 'rgba(124,152,133,0.3)',
    borderRadius: Radius.hero,
    padding: 16,
    gap: 7,
  },
  saysText: { fontSize: 18, lineHeight: 25 },
  bottom: { paddingHorizontal: 16, gap: 14 },
  centred: { textAlign: 'center' },
  controls: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  square: {
    width: 46,
    height: 46,
    borderRadius: Radius.control,
    backgroundColor: Camera.chip,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hidden: { opacity: 0 },
  end: {
    width: 62,
    height: 62,
    borderRadius: 31,
    backgroundColor: Camera.live,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stop: { width: 19, height: 19, borderRadius: 4, backgroundColor: '#FFFFFF' },
});
