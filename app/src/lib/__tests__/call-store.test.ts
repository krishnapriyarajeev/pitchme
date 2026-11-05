import { forgetCall, JOIN_WINDOW_MS, keepCall, pendingCall } from '@/lib/call-store';

const room = { session_id: 's1', room_name: 'r1', token: 't', livekit_url: 'ws://lk' };
const buyer = { name: 'Jo', company: 'Saber', manner: 'Direct' };

it('keeps a call for the join window only', () => {
  keepCall(room, buyer, 1000);
  expect(pendingCall('s1', 1000 + JOIN_WINDOW_MS)?.token).toBe('t');
  expect(pendingCall('s1', 1001 + JOIN_WINDOW_MS)).toBeNull();
  // Once too late, it is gone for good.
  expect(pendingCall('s1', 1000)).toBeNull();
});

it('forgets a call after it ends', () => {
  keepCall(room, buyer, 0);
  forgetCall('s1');
  expect(pendingCall('s1', 0)).toBeNull();
  expect(pendingCall('unknown', 0)).toBeNull();
});
