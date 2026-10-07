import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { apiClient } from '../api/client';
import type { BatchSummary, BatchForecastResponse, EconomicYield } from '../types';
import { OperationalCharts } from '../components/OperationalCharts';
import { BatchForecastCard } from '../components/BatchForecastCard';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { usePreferences } from '../hooks/usePreferences';

export const AnalyticsPage = () => {
  const [batches, setBatches] = useState<BatchSummary[] | null>(null);
  const [economic, setEconomic] = useState<EconomicYield | null>(null);
  const [forecast, setForecast] = useState<BatchForecastResponse | null>(null);
  const [breed, setBreed] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [batchId, setBatchId] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [updated, setUpdated] = useState<Date | null>(null);
  const [loadedScope, setLoadedScope] = useState('');
  const generation = useRef(0);
  const { pollingInterval } = usePreferences();
  const scope = `${breed}/${status}/${batchId}`;
  const refresh = useCallback(async () => {
    const request = ++generation.current;
    setLoading(true);
    try {
      const params = { breed: breed === 'ALL' ? undefined : breed, status: status === 'ALL' ? undefined : status, batch_id: batchId === 'ALL' ? undefined : batchId };
      const [records, yieldData, prediction] = await Promise.all([
        apiClient.getAllBatches(), apiClient.getEconomicYield(params),
        batchId === 'ALL' ? Promise.resolve(null) : apiClient.getBatchForecast(batchId),
      ]);
      if (request !== generation.current) return;
      setBatches(records); setEconomic(yieldData); setForecast(prediction);
      setLoadedScope(scope); setUpdated(new Date()); setError(false);
    } catch { if (request === generation.current) setError(true); }
    finally { if (request === generation.current) setLoading(false); }
  }, [breed, status, batchId, scope]);
  useEffect(() => {
    void refresh();
    const timer = pollingInterval > 0 ? setInterval(() => { void refresh(); }, pollingInterval * 1000) : undefined;
    return () => { clearInterval(timer); generation.current++; };
  }, [refresh, pollingInterval]);
  const matching = useMemo(() => (batches ?? []).filter(batch =>
    (breed === 'ALL' || batch.breed === breed) && (status === 'ALL' || batch.status === status)), [batches, breed, status]);
  const selected = batchId === 'ALL' ? matching : matching.filter(batch => batch.batch_id === batchId);
  const scopeReady = loadedScope === scope;
  const totals = selected.reduce((sum, batch) => ({ scanned: sum.scanned + batch.total_scanned, fertile: sum.fertile + batch.fertile_count, infertile: sum.infertile + batch.infertile_count, review: sum.review + (batch.manual_review_count ?? 0) }), { scanned: 0, fertile: 0, infertile: 0, review: 0 });
  const currency = (value: number | undefined) => value == null || !scopeReady ? '\u2014' : new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(value);
  const financials = [
    ['Penoy salvage estimate', economic?.estimated_penoy_salvage_value_php],
    ['Electricity savings estimate', economic?.electricity_saved_estimated_php],
    ['Recorded hatch value', economic?.projected_duckling_revenue_php],
    ['Combined estimated benefit', economic?.total_economic_benefit_php],
  ] as const;
  const scopeLabel = batchId !== 'ALL' ? selected[0]?.batch_code ?? batchId : `${matching.length} matching ${matching.length === 1 ? 'batch' : 'batches'}`;

  return <div className="space-y-6 pb-8" aria-busy={loading}>
    <div className="page-header"><div><h1>Analytics &amp; graphs</h1><p className="page-description">Saved Day 10 results and economic estimates for your selected batches.</p><p className="refresh-status" role="status">{updated ? `Last refreshed ${updated.toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit' })}` : loading ? 'Loading saved records...' : 'No analytics loaded'}</p></div><button onClick={() => { void refresh(); }} disabled={loading} className="secondary-action"><RefreshCw className="w-4 h-4" />{loading ? 'Refreshing...' : 'Refresh'}</button></div>
    {error && (batches ? <p role="alert" className="feedback-warning">Refresh failed. Previously loaded records remain visible. Use Refresh to retry.</p> : <DataUnavailableState title="Analytics unavailable" description="Check your backend connection and try again." onRetry={refresh} isRetrying={loading} />)}
    <div className="filter-toolbar">
      <div><label htmlFor="analytics-breed">Breed</label><select id="analytics-breed" value={breed} onChange={event => { setBreed(event.target.value); setBatchId('ALL'); }}><option value="ALL">All breeds</option><option value="KAYUMANGGI">IP-Kayumanggi</option><option value="ITIM">IP-Itim</option><option value="KHAKI">IP-Khaki</option></select></div>
      <div><label htmlFor="analytics-status">Batch status</label><select id="analytics-status" value={status} onChange={event => { setStatus(event.target.value); setBatchId('ALL'); }}><option value="ALL">All statuses</option><option value="INCUBATING">Incubating</option><option value="CANDLING_DUE">Candling due</option><option value="COMPLETED">Completed</option><option value="ARCHIVED">Archived</option></select></div>
      <div><label htmlFor="analytics-batch">Batch</label><select id="analytics-batch" value={batchId} onChange={event => setBatchId(event.target.value)}><option value="ALL">All matching batches</option>{matching.map(batch => <option key={batch.batch_id} value={batch.batch_id}>{batch.batch_code}</option>)}</select></div>
      {(breed !== 'ALL' || status !== 'ALL' || batchId !== 'ALL') && <button className="secondary-action" onClick={() => { setBreed('ALL'); setStatus('ALL'); setBatchId('ALL'); }}>Reset filters</button>}
    </div>
    <p className="text-sm text-slate-600">Showing {scopeLabel}. All charts, tables, and economic figures use this selection.</p>
    <dl className="summary-strip">{[['Recorded scans', totals.scanned], ['Fertile classifications', totals.fertile], ['Infertile classifications', totals.infertile], ['Awaiting review', totals.review]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{batches ? value.toLocaleString() : '\u2014'}</dd></div>)}</dl>
    <OperationalCharts batches={selected} loading={loading} />
    <section className="space-y-3" aria-labelledby="economics-heading"><h2 id="economics-heading" className="section-heading">Estimated economic benefit</h2><p className="text-sm text-slate-600">Penoy and energy estimates use saved classifications and backend prices. Recorded hatch value uses actual hatch counts. These are estimated values, not confirmed sales; repeat scans can overstate Penoy quantities.</p><dl className="summary-strip financial-summary">{financials.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{currency(value)}</dd></div>)}</dl></section>
    {batchId !== 'ALL' && scopeReady && <BatchForecastCard forecast={forecast} isLoading={loading} />}
    <section className="space-y-3" aria-labelledby="batch-counts-heading"><div className="section-header"><h2 id="batch-counts-heading" className="section-heading">Batch results</h2><Link to="/batches" className="text-link">Manage batches</Link></div><p className="text-sm text-slate-600">Fertility is fertile classifications divided by recorded scans. Awaiting review is a subset of classifications, not an additional biological class.</p><div className="table-scroll bordered-table" tabIndex={0} role="region" aria-label="Batch results, scroll horizontally on smaller screens"><table className="w-full min-w-[760px] text-left"><thead><tr><th scope="col">Batch</th><th scope="col">Eggs set</th><th scope="col">Scans</th><th scope="col">Fertile</th><th scope="col">Infertile</th><th scope="col">Fertility</th><th scope="col">Hatched</th></tr></thead><tbody>{selected.map(batch => <tr key={batch.batch_id}><th scope="row"><Link className="text-link" to={`/batches?batch=${encodeURIComponent(batch.batch_id)}`}>{batch.batch_code}</Link></th><td>{batch.initial_egg_count.toLocaleString()}</td><td>{batch.total_scanned.toLocaleString()}</td><td>{batch.fertile_count.toLocaleString()}</td><td>{batch.infertile_count.toLocaleString()}</td><td>{batch.total_scanned ? `${batch.fertility_rate.toFixed(1)}%` : '\u2014'}</td><td>{batch.status === 'COMPLETED' ? batch.hatched_count.toLocaleString() : 'Pending'}</td></tr>)}{!selected.length && <tr><td colSpan={7} className="py-8 text-center text-slate-600">{loading ? 'Loading batches...' : 'No batches match these filters.'}</td></tr>}</tbody></table></div></section>
  </div>;
};
