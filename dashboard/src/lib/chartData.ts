import type { BatchSummary } from '../types';

/** Both panels share categories and a count scale; repeated scans stay intact. */
export function operationalChartData(batches: BatchSummary[]) {
  const classification = batches.map(batch => ({ batch: batch.batch_code, Fertile: batch.fertile_count, Infertile: batch.infertile_count, total: batch.total_scanned }));
  const comparison = batches.map(batch => ({ batch: batch.batch_code, Scanned: batch.total_scanned, Set: batch.initial_egg_count }));
  const largest = Math.max(1, ...batches.flatMap(batch => [batch.initial_egg_count, batch.total_scanned, batch.fertile_count + batch.infertile_count]));
  const magnitude = 10 ** Math.floor(Math.log10(largest / 4));
  const step = Math.max(1, [1, 2, 5, 10].find(value => value * magnitude >= largest / 4)! * magnitude);
  const maximum = Math.ceil(largest / step) * step;
  const ticks = Array.from({ length: Math.round(maximum / step) + 1 }, (_, index) => index * step);
  return { classification, comparison, maximum, ticks };
}

/** Preserve the entire identifier; wrap long labels rather than overlapping ticks. */
export function batchLabelLines(label: string, width = 17): string[] {
  if (!label) return [''];
  const lines: string[] = [];
  let rest = label;
  while (rest.length > width) {
    const separator = rest.lastIndexOf('-', width - 1);
    const end = separator > width / 2 ? separator + 1 : width;
    lines.push(rest.slice(0, end));
    rest = rest.slice(end);
  }
  if (rest) lines.push(rest);
  return lines;
}
