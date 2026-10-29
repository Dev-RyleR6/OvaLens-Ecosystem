export function formatRunDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return 'Unavailable';
  const whole = Math.floor(seconds);
  const fraction = (seconds % 1).toFixed(6).slice(1).replace(/0+$/, '').replace(/\.$/, '');
  return [Math.floor(whole / 3600), Math.floor(whole / 60) % 60, whole % 60]
    .map(value => String(value).padStart(2, '0')).join(':') + fraction;
}

export function estimateCapacity(count: number, seconds: number | null, minutes: string): number | null {
  const duration = Number(minutes);
  if (!minutes.trim() || !Number.isFinite(duration) || duration <= 0 || seconds === null || seconds <= 0 || count <= 0) return null;
  const estimate = count * duration * 60 / seconds;
  return Number.isFinite(estimate) ? Math.floor(estimate) : null;
}
