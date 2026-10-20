import type { Device } from '../types';

/** A stored ONLINE flag alone does not establish a live hardware connection. */
export function deviceAvailability(device: Device, now = Date.now()) {
  const heartbeat = device.last_heartbeat ? Date.parse(device.last_heartbeat) : NaN;
  if (!Number.isFinite(heartbeat)) return 'UNKNOWN';
  if (now - heartbeat > 90_000 || heartbeat > now + 5_000) return 'STALE';
  return device.status;
}
