/**
 * Motion. There are three kinds, and nothing else moves:
 *
 *   Entrance  plays once, on mount: content rises and fades in.
 *   Ambient   loops, and only where something is live: the call dot, a
 *             spinner, the one breathing button on Home.
 *   Data      bars and rings draw from zero, so you see the value arrive.
 *
 * With reduce motion on, entrance and ambient motion stop, and data is set
 * at once.
 */

import { Easing } from 'react-native-reanimated';

export const Motion = {
  entrance: {
    duration: 600,
    /** How far content rises, in points. */
    offset: 12,
    /** Delay between items in a group. */
    stagger: 80,
    /** After this many items a group feels slow, so the delay stops growing. */
    maxSteps: 9,
  },
  data: {
    duration: 1000,
    ringDuration: 1300,
    delay: 350,
  },
  ambient: {
    pulse: 1600,
    spin: 2400,
    breathe: 5000,
    glowRing: 2600,
  },
} as const;

/** cubic-bezier(.22, .61, .36, 1), for every entrance and data draw. */
export const EaseOut = Easing.bezier(0.22, 0.61, 0.36, 1);
export const EaseInOut = Easing.inOut(Easing.quad);

/** The delay for item `index` of a group. */
export function stagger(index: number): number {
  return Math.min(index, Motion.entrance.maxSteps) * Motion.entrance.stagger;
}
