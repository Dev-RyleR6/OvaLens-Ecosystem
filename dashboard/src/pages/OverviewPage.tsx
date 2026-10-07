import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, RefreshCw, ScanSearch, ChartNoAxesCombined } from 'lucide-react';
import { apiClient } from '../api/client';
import { AnalyticsOverview, BatchSummary, EconomicYield } from '../types';
import { Badge } from '../components/Badge';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { usePreferences } from '../hooks/usePreferences';
import { OperationalCharts } from '../components/OperationalCharts';

export const OverviewPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [economic, setEconomic] = useState<EconomicYield | null>(null);
  const [economicScope, setEconomicScope] = useState('');
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [updated, setUpdated] = useState<Date | null>(null);
  const generation = useRef(0);
  const { pollingInterval } = usePreferences();

  const refresh = useCallback(async () => {
    const request = ++generation.current;
    setLoading(true);
    try {
      const [summary, batchList, yieldSummary] = await Promise.all([
        apiClient.getOverview(), apiClient.getAllBatches(), apiClient.getEconomicYield(selectedBatchId === 'ALL' ? undefined : { batch_id: selectedBatchId }),
      ]);
      if (request !== generation.current) return;
      setOverview(summary); setBatches(batchList); setEconomic(yieldSummary);
      setEconomicScope(selectedBatchId);
      setUpdated(new Date()); setError(false);
    } catch {
      if (request === generation.current) setError(true);
    } finally {
      if (request === generation.current) setLoading(false);
    }
  }, [selectedBatchId]);

  useEffect(() => {
    void refresh();
    const timer = pollingInterval > 0 ? setInterval(() => { void refresh(); }, pollingInterval * 1000) : undefined;
    return () => { clearInterval(timer); generation.current++; };
  }, [refresh, pollingInterval]);

  const current = batches.find(batch => batch.batch_id === selectedBatchId);
  const scanned = current ? current.total_scanned : overview?.total_eggs_scanned;
  const fertile = current ? current.fertile_count : overview?.total_fertile;
  const infertile = current ? current.infertile_count : overview?.total_infertile;
  const fertility = current ? current.fertility_rate : overview?.overall_fertility_rate;
  const displayBatches = current ? [current] : batches;
  const penoyValue = economicScope === selectedBatchId ? economic?.estimated_penoy_salvage_value_php : undefined;
  const metrics = [
    { label: 'Recorded scans', value: scanned?.toLocaleString() ?? '—', detail: 'Day 10 scan events' },
    { label: 'Fertile', value: fertile?.toLocaleString() ?? '—', detail: fertility == null || !scanned ? 'No fertility rate yet' : `${fertility.toFixed(1)}% of scanned eggs` },
    { label: 'Infertile', value: infertile?.toLocaleString() ?? '—', detail: 'Penoy recovery candidates' },
    { label: current ? 'Batch stage' : 'Active batches', value: current ? current.current_stage.replace(/_/g, ' ') : overview?.active_batches_count.toLocaleString() ?? '—', detail: current ? current.batch_code : 'Currently incubating' },
  ];

  return (
    <div className="space-y-7 pb-8" aria-busy={loading}>
      <div className="page-header">
        <div><h1>Hatchery overview</h1><p className="text-slate-600 mt-1">Day 10 results and the current incubation schedule.</p><p className="text-xs text-slate-500 mt-2" role="status">{updated ? `Last refreshed ${updated.toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit' })}` : loading ? 'Loading hatchery records…' : 'No records loaded'}</p></div>
        <div className="page-actions"><button onClick={() => { void refresh(); }} disabled={loading} className="secondary-action"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />{loading ? 'Refreshing…' : 'Refresh'}</button><Link to="/batches" className="primary-action">Manage batches <ArrowRight className="w-4 h-4" aria-hidden="true" /></Link></div>
      </div>
      {error && (overview ? <div role="alert" className="border border-amber-300 bg-amber-50 text-amber-900 p-4 rounded-xl">Refresh failed. These are previously loaded records. Use Refresh to try again.</div> : <DataUnavailableState title="Hatchery records unavailable" description="We could not load the hatchery records. Check your connection and try again." onRetry={refresh} isRetrying={loading} />)}
      <div className="filter-panel flex flex-col sm:flex-row sm:items-end gap-3 sm:gap-5"><div className="min-w-0 sm:flex-1 sm:max-w-sm"><label htmlFor="overview-batch" className="block font-medium mb-1.5">Show results for</label><select id="overview-batch" className="border border-input rounded-lg px-3 py-2.5 w-full bg-card" value={selectedBatchId} onChange={event => setSelectedBatchId(event.target.value)}><option value="ALL">All batches</option>{batches.map(batch => <option key={batch.batch_id} value={batch.batch_id}>{batch.batch_code}</option>)}</select></div><Link to="/scans?review=1" className="action-link"><ScanSearch aria-hidden="true" />Inspect low-confidence scans</Link></div>
      <dl className="summary-strip grid grid-cols-2 lg:grid-cols-4 border-y border-slate-300 bg-card">{metrics.map(metric => <div key={metric.label} className="px-4 py-5 sm:px-6"><dt className="text-slate-600">{metric.label}</dt><dd className="text-3xl font-semibold tabular-nums mt-2 text-foreground">{metric.value}</dd><dd className="text-xs text-slate-500 mt-2">{metric.detail}</dd></div>)}</dl>
      <div className="section-header"><h2 className="section-heading">Operational analytics</h2><Link to="/analytics" className="action-link"><ChartNoAxesCombined aria-hidden="true" />Open analytics</Link></div>
      <OperationalCharts batches={displayBatches} loading={loading} />
      <section className="space-y-3" aria-labelledby="schedule-heading">
        <div className="flex flex-wrap items-center justify-between gap-2"><h2 id="schedule-heading" className="text-lg font-semibold">Incubation schedule</h2><span className="text-sm text-slate-600">{displayBatches.length} {displayBatches.length === 1 ? 'batch' : 'batches'}</span></div>
        <div className="table-scroll bordered-table" tabIndex={0} role="region" aria-label="Incubation schedule. Scroll horizontally for all columns."><table className="min-w-[820px]">
          <caption className="sr-only">Batch stage, scanned eggs, fertility, and expected hatch date</caption>
          <thead className="bg-slate-50 text-slate-600"><tr><th>Batch</th><th>Breed</th><th>Stage</th><th className="text-right">Scans / eggs set</th><th className="text-right">Fertility</th><th>Expected hatch</th></tr></thead>
          <tbody className="divide-y divide-slate-200">{displayBatches.map(batch => <tr key={batch.batch_id}>
            <td><Link className="font-medium text-brand underline underline-offset-4" to={`/batches?batch=${encodeURIComponent(batch.batch_id)}`}>{batch.batch_code}</Link><p className="text-xs text-slate-500 mt-1">{batch.incubator_id}</p></td><td>{batch.breed}</td><td><Badge type="stage" value={batch.current_stage} /></td><td className="text-right tabular-nums">{batch.total_scanned.toLocaleString()} / {batch.initial_egg_count.toLocaleString()}</td><td className="text-right tabular-nums">{batch.total_scanned ? `${batch.fertility_rate.toFixed(1)}%` : '—'}</td><td>{new Date(batch.target_hatch_date).toLocaleDateString('en-PH', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
          </tr>)}{!displayBatches.length && <tr><td colSpan={6} className="text-center py-10 text-slate-600">{loading ? 'Loading batches…' : 'No batches recorded. Create a batch to begin tracking incubation.'}</td></tr>}</tbody>
        </table></div>
      </section>
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-slate-200 pt-5" aria-labelledby="recovery-heading"><div><h2 id="recovery-heading" className="text-lg font-semibold">Penoy recovery</h2><p className="text-slate-600 mt-1">Estimated salvage value for the selected batches. Repeat scans can overstate Penoy quantities.</p></div><div className="flex items-center gap-5"><span className="text-xl font-semibold tabular-nums">{penoyValue == null ? '—' : new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(penoyValue)}</span><Link to="/analytics" className="text-brand underline underline-offset-4">View economics</Link></div></section>
    </div>
  );
};
