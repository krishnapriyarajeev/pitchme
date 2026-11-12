import type { CallRoom } from '@/lib/api';

/** The buyer, as the call screen shows them. */
export type Buyer = { name: string; company: string; manner: string };

export type PendingCall = CallRoom & { buyer: Buyer; createdAt: number };

/**
 * The AI buyer waits about two minutes for the user to join, then reports a
 * no-show (JOIN_TIMEOUT_S in backend/ai/rehearsal/agent.py). After that the
 * room is no use, so the call is forgotten a little earlier.
 */
export const JOIN_WINDOW_MS = 110_000;

const calls = new Map<string, PendingCall>();

/**
 * Keeps the join token in memory between the prepare and call screens. In
 * the route params, the web build would show it in the address bar and keep
 * it in history.
 */
export function keepCall(room: CallRoom, buyer: Buyer, now = Date.now()): void {
  calls.set(room.session_id, { ...room, buyer, createdAt: now });
}

/** The call to join, or null when there is none or it is too late to join. */
export function pendingCall(sessionId: string, now = Date.now()): PendingCall | null {
  const call = calls.get(sessionId);
  if (!call) return null;
  if (now - call.createdAt > JOIN_WINDOW_MS) {
    calls.delete(sessionId);
    return null;
  }
  return call;
}

/** After the call, the token is of no more use. */
export function forgetCall(sessionId: string): void {
  calls.delete(sessionId);
}
