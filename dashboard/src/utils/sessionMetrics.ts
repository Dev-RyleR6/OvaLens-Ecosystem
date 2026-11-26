export function formatRunDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return 'Unavailable';
  const whole = Math.floor(seconds);
  const fraction = (seconds % 1).toFixed(6).slice(1).replace(/0+$/, '').replace(/\.$/, '');
  return [Math.floor(whole / 3600), Math.floor(whole / 60) % 60, whole % 60]
    .map(value => String(value).padStart(2, '0')).join(':') + fraction;
}

export function formatReadableDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds) || seconds < 0) {
    return 'Unavailable';
  }
  if (seconds > 0 && seconds < 1) {
    const trimmed = Number(seconds.toFixed(2)).toString();
    return `${trimmed} ${trimmed === '1' ? 'sec' : 'secs'}`;
  }
  const whole = Math.round(seconds);
  if (whole === 0) return '0 secs';
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const secs = whole % 60;
  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours} ${hours === 1 ? 'hr' : 'hrs'}`);
  if (minutes > 0) parts.push(`${minutes} ${minutes === 1 ? 'min' : 'mins'}`);
  if (secs > 0 && parts.length < 2) parts.push(`${secs} ${secs === 1 ? 'sec' : 'secs'}`);
  return parts.join(' ');
}

export function estimateCapacity(count: number, seconds: number | null, minutes: string): number | null {
  const duration = Number(minutes);
  if (!minutes.trim() || !Number.isFinite(duration) || duration <= 0 || seconds === null || seconds <= 0 || count <= 0) return null;
  const estimate = count * duration * 60 / seconds;
  return Number.isFinite(estimate) ? Math.floor(estimate) : null;
}

export interface RunDurationSummary {
  totalDurationSeconds: number | null;
  timedRuns: number;
  totalRuns: number;
  untimedRuns: number;
}

export function summarizeRunDurations(
  sessions: ReadonlyArray<{ duration_seconds: number | null | undefined }>
): RunDurationSummary {
  let total = 0;
  let timedRuns = 0;
  for (const session of sessions) {
    const seconds = session.duration_seconds;
    if (typeof seconds === 'number' && Number.isFinite(seconds) && seconds >= 0) {
      total += seconds;
      timedRuns += 1;
    }
  }
  const totalRuns = sessions.length;
  return {
    totalDurationSeconds: timedRuns > 0 ? total : null,
    timedRuns,
    totalRuns,
    untimedRuns: totalRuns - timedRuns,
  };
}
