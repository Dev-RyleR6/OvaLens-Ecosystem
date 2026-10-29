import { useId, useState } from 'react';
import type { CandlingSession } from '../types';
import { estimateCapacity, formatRunDuration } from '../utils/sessionMetrics';

export function SessionThroughput({ session }: { session: CandlingSession }) {
  const [minutes, setMinutes] = useState('10');
  const id = useId();
  const { duration_seconds: seconds, eggs_per_minute: rate, total_scanned: count } = session;
  const eligible = !!session.ended_at && seconds !== null && seconds > 0 && count > 0;
  const estimate = eligible ? estimateCapacity(count, seconds, minutes) : null;
  return (
    <div className="space-y-2 border-t border-border pt-2 text-sm text-foreground">
      <p className="tabular-nums">Duration: {formatRunDuration(seconds)} · Average: {rate === null ? 'Unavailable' : `${rate.toFixed(1)} scans/min`}</p>
      <p className="text-xs text-muted-foreground">Counts include manual-review captures and rescans. Diagnostic runs reflect diagnostic pace.</p>
      {eligible ? <>
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={id}>Estimate for (minutes)</label>
          <input id={id} type="number" min="0" step="any" value={minutes}
            onChange={event => setMinutes(event.target.value)} aria-invalid={estimate === null}
            aria-describedby={`${id}-result`}
            className="min-h-11 w-28 rounded-md border border-border bg-background px-3 text-base text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary" />
        </div>
        <p id={`${id}-result`} role="status" className="tabular-nums">
          {estimate === null ? 'Enter a finite number of minutes greater than zero.' :
            `Estimated capacity at this run’s average pace: approximately ${estimate.toLocaleString()} scans.`}
        </p>
        <p className="text-xs text-muted-foreground">Based on {count.toLocaleString()} scans in {formatRunDuration(seconds)}. Estimates do not control the conveyor.</p>
      </> : <p className="text-xs text-muted-foreground">Capacity estimates need a finalized run with positive duration and at least one scan.</p>}
    </div>
  );
}
