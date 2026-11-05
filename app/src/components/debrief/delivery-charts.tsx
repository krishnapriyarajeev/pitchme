import { StyleSheet, View } from 'react-native';

import { LineChart } from '@/components/charts/line-chart';
import { StatTile } from '@/components/charts/stat-tile';
import { Card } from '@/components/ui/card';
import { Text } from '@/components/ui/text';
import type { Metrics } from '@/lib/api';
import { PACE_RANGE } from '@/lib/debrief';
import { formatClock } from '@/lib/format';

const time = (seconds: number) => formatClock(seconds);
const percent = (share: number | undefined) =>
  share === undefined ? '–' : `${Math.round(share * 100)}%`;

/** Pace, pitch and loudness over the call, and body language as numbers. */
export function DeliveryCharts({ metrics }: { metrics: Metrics }) {
  const pace = metrics.speech?.fluency?.wpm_windows ?? [];
  const pitch = metrics.voice?.pitch?.windows ?? [];
  const loudness = metrics.voice?.loudness?.windows ?? [];
  const fillers = metrics.speech?.fluency?.filler_counts ?? [];
  const vision = metrics.vision;

  return (
    <View style={styles.wrap}>
      {pace.length > 1 ? (
        <Card>
          <Text variant="rowTitle">Your pace</Text>
          <Text variant="secondary" color="textSecondary" style={styles.sub}>
            Words a minute while you spoke. Average{' '}
            {Math.round(metrics.speech?.fluency?.wpm_mean ?? 0)}.
          </Text>
          <LineChart
            points={pace.map((w) => ({ x: w.t_start_ms / 1000, y: w.wpm }))}
            formatX={time}
            formatY={(y) => `${Math.round(y)} wpm`}
            range={{ ...PACE_RANGE, label: 'a comfortable pace' }}
            summary={`Your pace over the call, from ${Math.round(Math.min(...pace.map((w) => w.wpm)))} to ${Math.round(Math.max(...pace.map((w) => w.wpm)))} words a minute.`}
          />
        </Card>
      ) : null}

      {pitch.length > 1 ? (
        <Card>
          <Text variant="rowTitle">Your pitch</Text>
          <Text variant="secondary" color="textSecondary" style={styles.sub}>
            How high your voice was. A line that moves sounds engaged; a flat one can sound
            rehearsed.
          </Text>
          <LineChart
            points={pitch.map((w) => ({ x: w.t_start_s, y: w.mean_hz }))}
            formatX={time}
            formatY={(y) => `${Math.round(y)} Hz`}
            summary={`Your average pitch over the call, across ${pitch.length} parts.`}
          />
        </Card>
      ) : null}

      {loudness.length > 1 ? (
        <Card>
          <Text variant="rowTitle">Your volume</Text>
          <Text variant="secondary" color="textSecondary" style={styles.sub}>
            How loud you were. A drop at the end of a point can make it sound unsure.
          </Text>
          <LineChart
            points={loudness.map((w) => ({ x: w.t_start_s, y: w.mean_db }))}
            formatX={time}
            formatY={(y) => `${Math.round(y)} dB`}
            summary={`Your volume over the call, across ${loudness.length} parts.`}
          />
        </Card>
      ) : null}

      {fillers.length > 0 ? (
        <Card>
          <Text variant="rowTitle">Filler words</Text>
          <Text variant="secondary" color="textSecondary" style={styles.sub}>
            {metrics.speech?.fluency?.filler_total ?? 0} in total, about{' '}
            {(metrics.speech?.fluency?.filler_per_min ?? 0).toFixed(1)} a minute.
          </Text>
          <View style={styles.words}>
            {fillers.map((filler) => (
              <Text key={filler.word} variant="secondary">
                “{filler.word}” ×{filler.count}
              </Text>
            ))}
          </View>
        </Card>
      ) : null}

      {vision ? (
        <Card>
          <Text variant="rowTitle">Body language</Text>
          <View style={styles.tiles}>
            <StatTile
              label="Eye contact"
              value={percent(vision.eye_contact?.contact_pct)}
              detail="looking at the camera"
            />
            <StatTile
              label="Posture"
              value={percent(vision.pose?.good_posture_pct)}
              detail="sitting upright"
            />
            <StatTile
              label="Gestures"
              value={
                vision.movement?.gestures_per_min === undefined
                  ? '–'
                  : `${Math.round(vision.movement.gestures_per_min)}`
              }
              detail="a minute"
            />
            <StatTile
              label="Expression"
              value={vision.emotion?.dominant_emotion ?? '–'}
              detail="most of the time"
            />
          </View>
        </Card>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 10 },
  sub: { marginTop: 2, marginBottom: 10 },
  words: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  tiles: { marginTop: 10, flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
});
