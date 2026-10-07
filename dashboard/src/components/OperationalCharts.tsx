import { useId } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { BatchSummary } from '../types';
import { batchLabelLines } from '../lib/chartData';

function BatchTick({ x = 0, y = 0, payload }: { x?: number; y?: number; payload?: { value: string } }) {
  const lines = batchLabelLines(payload?.value ?? '');
  return <text x={x - 8} y={y} textAnchor="end" fill="var(--foreground)" fontSize={12}>
    {lines.map((line, index) => <tspan key={index} x={x - 8} dy={index === 0 ? -((lines.length - 1) * 7.5) + 4 : 15}>{line}</tspan>)}
  </text>;
}

export function OperationalCharts({ batches, loading = false }: { batches: BatchSummary[]; loading?: boolean }) {
  const id = useId();
  const recorded = batches.filter(batch => batch.total_scanned > 0);
  const results = recorded.map(batch => ({ batch: batch.batch_code, Fertile: batch.fertile_count, Infertile: batch.infertile_count }));
  const comparison = batches.map(batch => ({ batch: batch.batch_code, Scanned: batch.total_scanned, Set: batch.initial_egg_count }));
  const tooltip = { backgroundColor: 'var(--card)', borderColor: 'var(--border)', color: 'var(--foreground)', borderRadius: 8, fontSize: 13 };
  const panels = [
    { title: 'Day 10 classification', description: 'Current classifications from saved scans, including results awaiting review.', data: results, rows: recorded, keys: ['Fertile', 'Infertile'], colors: ['var(--success-ink)', 'var(--chart-reject)'], stacked: true },
    { title: 'Scans vs eggs set', description: 'Scan events and initial eggs set. Repeat scans are counted; this is not unique-egg coverage.', data: comparison, rows: batches, keys: ['Set', 'Scanned'], colors: ['#64748B', 'var(--brand-ink)'], stacked: false },
  ];
  return <div className="operational-charts">
    {panels.map((panel, index) => {
      const rowHeight = Math.max(56, ...panel.rows.map(batch => batchLabelLines(batch.batch_code).length * 15 + 20));
      const height = Math.max(180, panel.data.length * rowHeight + 60);
      return <section key={panel.title} className="chart-panel" aria-labelledby={`${id}-${index}`}>
        <div className="chart-heading"><h2 id={`${id}-${index}`}>{panel.title}</h2><p>{panel.description}</p></div>
        {panel.data.length ? <>
          <div className="chart-scroll" tabIndex={0} role="region" aria-label={`${panel.title}. Scroll vertically for more batches. Exact values follow the chart.`}>
            <div style={{ height }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0}><BarChart data={panel.data} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 0 }} barCategoryGap="25%">
                <CartesianGrid horizontal={false} stroke="var(--border)" />
                <XAxis type="number" allowDecimals={false} domain={[0, 'auto']} tick={{ fill: 'var(--foreground)', fontSize: 12 }} tickLine={false} tickCount={3} interval="preserveStartEnd" minTickGap={10} />
                <YAxis type="category" dataKey="batch" tick={<BatchTick />} width={140} tickLine={false} axisLine={false} interval={0} />
                <Tooltip contentStyle={tooltip} cursor={{ fill: 'var(--border)', opacity: .3 }} />
                {panel.keys.map((key, keyIndex) => <Bar key={key} dataKey={key} stackId={panel.stacked ? 'classification' : undefined} fill={panel.colors[keyIndex]} maxBarSize={panel.stacked ? 24 : 14} isAnimationActive={false} />)}
              </BarChart></ResponsiveContainer>
            </div>
          </div>
          <div className="chart-legend" aria-label="Chart legend">{panel.keys.map((key, keyIndex) => <span key={key}><i style={{ background: panel.colors[keyIndex] }} aria-hidden="true" />{key === 'Set' ? 'Eggs set' : key}</span>)}</div>
          <details className="chart-values"><summary>View exact counts</summary><div className="table-scroll" tabIndex={0} role="region" aria-label={`${panel.title} counts`}><table><caption className="sr-only">{panel.title} counts</caption><thead><tr><th scope="col">Batch</th>{panel.keys.map(key => <th scope="col" key={key}>{key === 'Set' ? 'Eggs set' : key}</th>)}</tr></thead><tbody>{panel.rows.map(batch => <tr key={batch.batch_id}><th scope="row">{batch.batch_code}</th>{panel.stacked ? <><td>{batch.fertile_count.toLocaleString()}</td><td>{batch.infertile_count.toLocaleString()}</td></> : <><td>{batch.initial_egg_count.toLocaleString()}</td><td>{batch.total_scanned.toLocaleString()}{batch.total_scanned > batch.initial_egg_count && <span className="block text-xs text-amber-800">Exceeds set count</span>}</td></>}</tr>)}</tbody></table></div></details>
        </> : <p className="chart-empty" role="status">{loading ? 'Loading saved records...' : panel.stacked ? 'No scans recorded for this selection.' : 'No batches match this selection.'}</p>}
      </section>;
    })}
  </div>;
}
