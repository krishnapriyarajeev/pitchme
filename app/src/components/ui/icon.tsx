import Svg, { Circle, Path, Rect } from 'react-native-svg';

/**
 * One line icon set on a 24 by 24 grid. Icons are drawn at their visible
 * size; IconButton pads them up to a full tap area.
 */
export type IconName =
  | 'chevron-left'
  | 'chevron-right'
  | 'chevron-down'
  | 'chevron-up'
  | 'close'
  | 'more'
  | 'mic'
  | 'play'
  | 'pause'
  | 'refresh'
  | 'upload'
  | 'check'
  | 'check-circle'
  | 'info'
  | 'alert'
  | 'shield-check'
  | 'clock'
  | 'file'
  | 'eye'
  | 'eye-off'
  | 'home'
  | 'chart'
  | 'user'
  | 'message'
  | 'speaker'
  | 'sign-out'
  | 'video'
  | 'book';

type Props = {
  name: IconName;
  size?: number;
  color: string;
  /** Filled glyphs (play, pause) ignore this. */
  strokeWidth?: number;
};

const SHIELD = 'M12 2.4 19.4 5.5v5.8c0 4.6-3.1 8.2-7.4 9.3-4.3-1.1-7.4-4.7-7.4-9.3V5.5L12 2.4Z';

export function Icon({ name, size = 22, color, strokeWidth = 1.7 }: Props) {
  const s = {
    stroke: color,
    strokeWidth,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  };
  const ring = <Circle cx="12" cy="12" r="9.4" {...s} />;

  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {name === 'chevron-left' && <Path d="M14.5 5 8 12l6.5 7" {...s} />}
      {name === 'chevron-right' && <Path d="M9.5 5 16 12l-6.5 7" {...s} />}
      {name === 'chevron-down' && <Path d="M5 9.5 12 16l7-6.5" {...s} />}
      {name === 'chevron-up' && <Path d="M5 14.5 12 8l7 6.5" {...s} />}
      {name === 'close' && <Path d="M6 6l12 12M18 6 6 18" {...s} />}
      {name === 'more' && (
        <>
          <Circle cx="12" cy="5" r="1.6" fill={color} />
          <Circle cx="12" cy="12" r="1.6" fill={color} />
          <Circle cx="12" cy="19" r="1.6" fill={color} />
        </>
      )}
      {name === 'mic' && (
        <>
          <Rect x="8.3" y="2.6" width="7.4" height="12.4" rx="3.7" {...s} />
          <Path d="M4.8 11.1a7.2 7.2 0 0 0 14.4 0M12 18.3v3" {...s} />
        </>
      )}
      {name === 'play' && <Path d="M8.4 5.6v12.8L19 12 8.4 5.6Z" fill={color} />}
      {name === 'pause' && <Path d="M8 5h2v14H8V5Zm6 0h2v14h-2V5Z" fill={color} />}
      {name === 'refresh' && (
        <Path d="M4.2 12a7.8 7.8 0 1 1 2.4 5.6M3.5 17.4l.7-6.1 5.8 1.8" {...s} />
      )}
      {name === 'upload' && (
        <Path
          d="M12 16V4.2M12 4.2 7.6 8.6M12 4.2l4.4 4.4M4.2 16.4v2.2a1.9 1.9 0 0 0 1.9 1.9h11.8a1.9 1.9 0 0 0 1.9-1.9v-2.2"
          {...s}
        />
      )}
      {name === 'check' && <Path d="m5 12.4 4.6 4.6L19.4 6.8" {...s} />}
      {name === 'check-circle' && (
        <>
          {ring}
          <Path d="m7.9 12.2 2.9 2.9 5.4-5.9" {...s} />
        </>
      )}
      {name === 'info' && (
        <>
          {ring}
          <Path d="M12 10.8v5.4M12 7.4v1.1" {...s} />
        </>
      )}
      {name === 'alert' && <Path d="M12 2.6 22 20H2L12 2.6ZM12 9.4v4.1M12 16.1v1.2" {...s} />}
      {name === 'shield-check' && <Path d={`${SHIELD}M8.8 11.4l2.3 2.3 4.1-4.3`} {...s} />}
      {name === 'clock' && (
        <>
          {ring}
          <Path d="M12 6.6v5.6l3.4 2" {...s} />
        </>
      )}
      {name === 'file' && (
        <Path
          d="M14.2 2.8H6.9a2 2 0 0 0-2 2v14.4a2 2 0 0 0 2 2h10.2a2 2 0 0 0 2-2V7.6l-4.9-4.8Zm0 0v4.8h4.9"
          {...s}
        />
      )}
      {(name === 'eye' || name === 'eye-off') && (
        <>
          <Path
            d="M2.4 12S6.5 5.2 12 5.2 21.6 12 21.6 12 17.5 18.8 12 18.8 2.4 12 2.4 12Z"
            {...s}
          />
          <Circle cx="12" cy="12" r="3.1" {...s} />
          {name === 'eye-off' && <Path d="M4 4l16 16" {...s} />}
        </>
      )}
      {name === 'home' && (
        <Path
          d="M3.6 10 12 3.5l8.4 6.5v9.5a1.5 1.5 0 0 1-1.5 1.5H5.1a1.5 1.5 0 0 1-1.5-1.5V10Z"
          {...s}
        />
      )}
      {name === 'chart' && <Path d="M4.2 18.3v-5.2m5.2 5.2V8.9m5.2 9.4V4.7m5.2 13.6v-7.3" {...s} />}
      {name === 'user' && (
        <>
          <Circle cx="12" cy="8.4" r="4.1" {...s} />
          <Path d="M4.6 20.3a7.7 7.7 0 0 1 14.8 0" {...s} />
        </>
      )}
      {name === 'message' && (
        <Path
          d="M20.4 14a1.9 1.9 0 0 1-1.9 1.9H7.1L3.3 19.7V5.5a1.9 1.9 0 0 1 1.9-1.9h13.3a1.9 1.9 0 0 1 1.9 1.9V14Z"
          {...s}
        />
      )}
      {name === 'speaker' && (
        <Path d="M13.4 3.8 8.4 8.1H4.3v7.8h4.1l5 4.3V3.8ZM16.9 8.8a4.6 4.6 0 0 1 0 6.4" {...s} />
      )}
      {name === 'sign-out' && (
        <Path
          d="M15.4 16.6 20 12l-4.6-4.6M20 12H8.6M8.6 3.4H5a1.6 1.6 0 0 0-1.6 1.6v14a1.6 1.6 0 0 0 1.6 1.6h3.6"
          {...s}
        />
      )}
      {name === 'video' && (
        <>
          <Rect x="3" y="5.5" width="13" height="13" rx="2" {...s} />
          <Path d="m16 10.4 5-2.9v9l-5-2.9" {...s} />
        </>
      )}
      {name === 'book' && (
        <Path
          d="M5.2 4.6a1.6 1.6 0 0 1 1.6-1.6h12v15.2H6.8a1.6 1.6 0 0 0-1.6 1.6V4.6Zm0 14.8a1.6 1.6 0 0 0 1.6 1.6h12M9 7.4h6"
          {...s}
        />
      )}
    </Svg>
  );
}
