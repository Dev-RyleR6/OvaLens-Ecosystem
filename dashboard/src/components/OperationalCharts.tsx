import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { BatchSummary } from '../types';

export function OperationalCharts({ batches }: { batches: BatchSummary[] }) {
  const recorded = batches.filter(batch => batch.total_scanned > 0);
  const results = recorded.map(batch => ({ batch: batch.batch_code, Fertile: batch.fertile_count, Infertile: batch.infertile_count }));
  const progress = batches.map(batch => ({ batch: batch.batch_code, Scanned: batch.total_scanned, Set: batch.initial_egg_count }));
  const tooltip = { backgroundColor: 'var(--card)', borderColor: 'var(--border)', color: 'var(--foreground)', borderRadius: 8 };
  return <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
    <section className="border border-border rounded-xl bg-card p-5 min-w-0" aria-labelledby="results-chart-heading">
      <h2 id="results-chart-heading" className="text-lg font-semibold">Day 10 classification</h2>
      <p className="text-sm text-slate-600 mt-1">Recorded fertile and infertile scans by batch.</p>
      {recorded.length ? <div className="overflow-x-auto mt-5" role="img" aria-label="Stacked bar chart of fertile and infertile scans. Exact counts are listed below.">
        <div style={{ minWidth: Math.max(320, results.length * 90), height: 280 }}>
          <ResponsiveContainer width="100%" height="100%"><BarChart data={results}>
            <CartesianGrid vertical={false} stroke="var(--border)" /><XAxis dataKey="batch" tick={{ fill: 'var(--foreground)', fontSize: 12 }} interval={0} /><YAxis allowDecimals={false} tick={{ fill: 'var(--foreground)', fontSize: 12 }} width={45} />
            <Tooltip contentStyle={tooltip} cursor={{ fill: 'var(--border)', opacity: 0.3 }} /><Legend />
            <Bar dataKey="Fertile" stackId="results" fill="#357a38" maxBarSize={44} isAnimationActive={false} /><Bar dataKey="Infertile" stackId="results" fill="#DC2626" maxBarSize={44} isAnimationActive={false} />
          </BarChart></ResponsiveContainer>
        </div>
      </div> : <p className="py-16 text-center text-slate-600">No Day 10 scans recorded for this selection.</p>}
      {!!recorded.length && <details className="mt-3 text-sm"><summary className="cursor-pointer text-brand py-2">View classification counts</summary><div className="overflow-x-auto"><table className="w-full text-left"><thead><tr><th>Batch</th><th>Fertile</th><th>Infertile</th></tr></thead><tbody>{recorded.map(batch => <tr key={batch.batch_id}><td>{batch.batch_code}</td><td>{batch.fertile_count.toLocaleString()}</td><td>{batch.infertile_count.toLocaleString()}</td></tr>)}</tbody></table></div></details>}
    </section>
    <section className="border border-border rounded-xl bg-card p-5 min-w-0" aria-labelledby="coverage-chart-heading">
      <h2 id="coverage-chart-heading" className="text-lg font-semibold">Candling coverage</h2>
      <p className="text-sm text-slate-600 mt-1">Recorded scans compared with eggs initially set. Repeat scans can exceed the set count.</p>
      {batches.length ? <div className="overflow-x-auto mt-5" role="img" aria-label="Grouped bar chart comparing scanned and set egg counts. Exact counts are available in the batch table."><div style={{ minWidth: Math.max(320, progress.length * 90), height: 280 }}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={progress}>
          <CartesianGrid vertical={false} stroke="var(--border)" /><XAxis dataKey="batch" tick={{ fill: 'var(--foreground)', fontSize: 12 }} interval={0} /><YAxis allowDecimals={false} tick={{ fill: 'var(--foreground)', fontSize: 12 }} width={45} />
          <Tooltip contentStyle={tooltip} cursor={{ fill: 'var(--border)', opacity: 0.3 }} /><Legend /><Bar dataKey="Set" fill="#64748B" maxBarSize={30} isAnimationActive={false} /><Bar dataKey="Scanned" fill="#800000" maxBarSize={30} isAnimationActive={false} />
        </BarChart></ResponsiveContainer>
      </div></div> : <p className="py-16 text-center text-slate-600">Create a batch to start tracking candling coverage.</p>}
    </section>
  </div>;
}
