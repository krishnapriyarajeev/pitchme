import { useRef, useState } from 'react';
import { Pressable, StyleSheet, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Polyline, Rect } from 'react-native-svg';

import { Text } from '@/components/ui/text';
import { useTheme } from '@/hooks/use-theme';

export type Point = { x: number; y: number };

type Props = {
  points: Point[];
  /** "1:05" for an x value. */
  formatX: (x: number) => string;
  /** "164 wpm" for a y value. */
  formatY: (y: number) => string;
  /** A shaded range with its own label, for example the comfortable pace. */
  range?: { low: number; high: number; label: string };
  /** One sentence for screen readers: what the line shows. */
  summary: string;
  height?: number;
};

const PAD = { top: 10, bottom: 18, left: 4, right: 4 };

/**
 * One series over time. A tap reads the nearest point. With one series the
 * title names it, so there is no legend; values are in text colours, and
 * the line carries the only data colour.
 */
export function LineChart({ points, formatX, formatY, range, summary, height = 120 }: Props) {
  const theme = useTheme();
  const [width, setWidth] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const area = useRef<View>(null);

  if (points.length < 2) {
    return (
      <Text variant="secondary" color="textSubtle">
        Not enough of the call to draw this.
      </Text>
    );
  }

  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const yLow = Math.min(...ys, range?.low ?? Infinity);
  const yHigh = Math.max(...ys, range?.high ?? -Infinity);
  const ySpan = yHigh - yLow || 1;
  const xLow = Math.min(...xs);
  const xSpan = Math.max(...xs) - xLow || 1;
  const plotW = Math.max(1, width - PAD.left - PAD.right);
  const plotH = height - PAD.top - PAD.bottom;
  const px = (x: number) => PAD.left + ((x - xLow) / xSpan) * plotW;
  const py = (y: number) => PAD.top + (1 - (y - yLow) / ySpan) * plotH;
  const chosen = picked === null ? null : points[picked];

  function pick(locationX: number) {
    let best = 0;
    points.forEach((p, i) => {
      if (Math.abs(px(p.x) - locationX) < Math.abs(px(points[best]!.x) - locationX)) best = i;
    });
    setPicked((current) => (current === best ? null : best));
  }

  return (
    <View>
      <View style={styles.readout}>
        <Text variant="secondary" color={chosen ? 'text' : 'textSubtle'} numberOfLines={1}>
          {chosen
            ? `${formatX(chosen.x)} · ${formatY(chosen.y)}`
            : `Tap the line to read a point. ${formatY(yLow)} to ${formatY(yHigh)}.`}
        </Text>
      </View>
      <Pressable
        onLayout={(event: LayoutChangeEvent) => setWidth(event.nativeEvent.layout.width)}
        ref={area}
        onPress={(event) => {
          // locationX is not set on the web, so measure from the page edge.
          const { pageX } = event.nativeEvent;
          area.current?.measure((_x, _y, _w, _h, left) => pick(pageX - left));
        }}
        accessibilityRole="image"
        accessibilityLabel={summary}
        style={{ height }}>
        {width > 0 ? (
          // The drawing takes no touches, so a tap's position is measured
          // against the chart area, not a line under the finger.
          <View style={styles.passThrough}>
            <Svg width={width} height={height}>
              {range ? (
                <Rect
                  x={PAD.left}
                  width={plotW}
                  y={py(range.high)}
                  height={Math.max(0, py(range.low) - py(range.high))}
                  fill={theme.sageSoft}
                />
              ) : null}
              {[0, 0.5, 1].map((t) => (
                <Line
                  key={t}
                  x1={PAD.left}
                  x2={PAD.left + plotW}
                  y1={PAD.top + t * plotH}
                  y2={PAD.top + t * plotH}
                  stroke={theme.hairline}
                  strokeWidth={1}
                />
              ))}
              <Polyline
                points={points.map((p) => `${px(p.x)},${py(p.y)}`).join(' ')}
                fill="none"
                stroke={theme.accent}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {chosen ? (
                <>
                  <Line
                    x1={px(chosen.x)}
                    x2={px(chosen.x)}
                    y1={PAD.top}
                    y2={PAD.top + plotH}
                    stroke={theme.borderStrong}
                    strokeWidth={1}
                  />
                  <Circle
                    cx={px(chosen.x)}
                    cy={py(chosen.y)}
                    r={5}
                    fill={theme.accent}
                    stroke={theme.surface}
                    strokeWidth={2}
                  />
                </>
              ) : null}
            </Svg>
          </View>
        ) : null}
      </Pressable>
      <View style={styles.axis}>
        <Text variant="secondary" color="textSubtle">
          {formatX(xLow)}
        </Text>
        {range ? (
          <Text variant="secondary" color="sageText">
            Shaded: {range.label}
          </Text>
        ) : null}
        <Text variant="secondary" color="textSubtle">
          {formatX(xLow + xSpan)}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  readout: { minHeight: 20, marginBottom: 4 },
  passThrough: { pointerEvents: 'none' },
  axis: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 2 },
});
