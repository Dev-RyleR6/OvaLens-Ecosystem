import React, { useState, useEffect, useMemo, useRef } from 'react';
import { OperationalCharts } from '../components/OperationalCharts';
import { usePreferences } from '../hooks/usePreferences';
import {
  Coins,
  TrendingUp,
  Zap,
  Award,
  ShieldAlert,
  Percent,
  CheckCircle2,
} from 'lucide-react';


import { StatCard } from '../components/StatCard';
import { apiClient } from '../api/client';
import { EconomicYield, MortalityTrends, BreedMetricItem, BatchSummary, BatchAnalyticsResponse, BatchForecastResponse } from '../types';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { BatchForecastCard } from '../components/BatchForecastCard';
import { Filter, RotateCcw, Layers, ChevronDown, SlidersHorizontal } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const [economic, setEconomic] = useState<EconomicYield | null>(null);
  const [mortality, setMortality] = useState<MortalityTrends | null>(null);
  const [breedMetrics, setBreedMetrics] = useState<BreedMetricItem[]>([]);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [breedFilter, setBreedFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedBatchId, setSelectedBatchId] = useState<string>('ALL');
  const [batchAnalytics, setBatchAnalytics] = useState<BatchAnalyticsResponse | null>(null);
  const [batchForecast, setBatchForecast] = useState<BatchForecastResponse | null>(null);
  const [isLoadingBatch, setIsLoadingBatch] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);

  const { pollingInterval } = usePreferences();
  const generation = useRef(0);
  const batchGeneration = useRef(0);
  const [batchError, setBatchError] = useState(false);

  const fetchData = async () => {
    const request = ++generation.current;
    setIsLoading(true);
    setIsError(false);
    try {
      const [eData, mData, bData, batchList] = await Promise.all([
        apiClient.getEconomicYield(),
        apiClient.getMortalityTrends(),
        apiClient.getBreedComparison(),
        apiClient.getAllBatches(),
      ]);
      if (request !== generation.current) return;
      setEconomic(eData);
      setMortality(mData);
      setBreedMetrics(Array.isArray(bData) ? bData : []);
      setBatches(Array.isArray(batchList) ? batchList : []);
    } catch (err) {
      console.error("Error fetching analytics data:", err);
      if (request === generation.current) setIsError(true);
    } finally {
      if (request === generation.current) setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
    const timer = pollingInterval > 0 ? setInterval(() => { void fetchData(); }, pollingInterval * 1000) : undefined;
    return () => { clearInterval(timer); generation.current++; batchGeneration.current++; };
  }, [pollingInterval]);

  const handleBatchChange = async (batchId: string) => {
    const request = ++batchGeneration.current;
    setSelectedBatchId(batchId);
    setBatchAnalytics(null); setBatchForecast(null); setBatchError(false);
    if (batchId === 'ALL') {
      setIsLoadingBatch(false);
      setBatchAnalytics(null);
      setBatchForecast(null);
      return;
    }

    setIsLoadingBatch(true);
    try {
      const [data, forecast] = await Promise.all([
        apiClient.getBatchAnalytics(batchId),
        apiClient.getBatchForecast(batchId)
      ]);
      if (request !== batchGeneration.current) return;
      setBatchAnalytics(data);
      setBatchForecast(forecast);
    } catch (err) {
      if (request === batchGeneration.current) setBatchError(true);
    } finally {
      if (request === batchGeneration.current) setIsLoadingBatch(false);
    }
  };

  const filteredBatches = useMemo(() => {
    return batches.filter((b) => {
      const matchesBreed = breedFilter === 'ALL' || b.breed === breedFilter;
      const matchesStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'ACTIVE' && b.status === 'INCUBATING') ||
        (statusFilter === 'COMPLETED' && b.status === 'COMPLETED');
      return matchesBreed && matchesStatus;
    });
  }, [batches, breedFilter, statusFilter]);

  const handleBreedFilterChange = (breed: string) => {
    setBreedFilter(breed);
    if (selectedBatchId !== 'ALL') {
      const batch = batches.find((b) => b.batch_id === selectedBatchId);
      if (batch && breed !== 'ALL' && batch.breed !== breed) {
        handleBatchChange('ALL');
      }
    }
  };

  const handleStatusFilterChange = (status: string) => {
    setStatusFilter(status);
    if (selectedBatchId !== 'ALL') {
      const batch = batches.find((b) => b.batch_id === selectedBatchId);
      if (batch) {
        const isMatch =
          status === 'ALL' ||
          (status === 'ACTIVE' && batch.status === 'INCUBATING') ||
          (status === 'COMPLETED' && batch.status === 'COMPLETED');
        if (!isMatch) {
          handleBatchChange('ALL');
        }
      }
    }
  };

  const handleResetAllFilters = () => {
    setBreedFilter('ALL');
    setStatusFilter('ALL');
    handleBatchChange('ALL');
  };

  const isAnyFilterActive = breedFilter !== 'ALL' || statusFilter !== 'ALL' || selectedBatchId !== 'ALL';
  const selectedBatchInfo = batches.find((b) => b.batch_id === selectedBatchId);
  const isBatchFiltered = selectedBatchId !== 'ALL' && batchAnalytics !== null;

  const penoyCount = isBatchFiltered ? batchAnalytics.infertile_penoy_day_10 : (economic?.penoy_culled_day_10 ?? 0);
  const salvageRev = isBatchFiltered ? batchAnalytics.penoy_salvage_value_php : (economic?.salvage_revenue_php ?? economic?.estimated_penoy_salvage_value_php ?? 0);
  const powerSaved = isBatchFiltered ? batchAnalytics.electricity_saved_php : (economic?.energy_savings_php ?? economic?.electricity_saved_estimated_php ?? 0);
  const totalBenefit = isBatchFiltered ? (salvageRev + powerSaved) : (economic?.total_economic_benefit_php ?? 0);

  if (isError && !economic && !mortality) {
    return (
      <div className="space-y-6 pb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-xl font-bold text-foreground tracking-tight">
              Analytics & graphs
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Recorded Day 10 results, candling coverage, and estimated economic recovery.
            </p>
          </div>
        </div>
        <DataUnavailableState
          title="Analytics Service Offline"
          description="Unable to compute fertility metrics and economic salvage yield from PostgreSQL. Check that the backend server is active."
          onRetry={fetchData}
          isRetrying={isLoading}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-foreground tracking-tight">
            Analytics & graphs
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Recorded Day 10 results, candling coverage, and estimated economic recovery.
          </p>
        </div>

        {isAnyFilterActive && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-brand bg-red-50 border border-red-200 px-2.5 py-1 rounded-md">
              Filtered View Active
            </span>
            <button
              onClick={handleResetAllFilters}
              className="h-8 px-2.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-md text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              aria-label="Reset all filters to facility totals" title="Reset all filters to facility totals"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          </div>
        )}
      </div>

      {/* Analytics Scope & Multi-Filter Toolbar */}
      <div className="bg-card border border-border rounded-xl p-3.5  space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-100 text-xs">
          <div className="flex items-center gap-2 font-bold text-slate-800">
            <SlidersHorizontal className="w-4 h-4 text-brand" />
            <span>Chart and batch filters</span>
          </div>
          <span className="text-[11px] text-slate-400">
            Breed and status filter charts; select a batch for its economics and forecast
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          {/* 1. Duck Breed Filter */}
          <div className="relative">
            <select
              aria-label="Filter charts by breed"
              value={breedFilter}
              onChange={(e) => handleBreedFilterChange(e.target.value)}
              className="w-full h-9 pl-3 pr-8 text-xs font-semibold bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10  cursor-pointer appearance-none"
            >
              <option value="ALL">All Duck Breeds</option>
              <option value="KAYUMANGGI">IP-Kayumanggi</option>
              <option value="ITIM">IP-Itim</option>
              <option value="KHAKI">IP-Khaki</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* 2. Incubation Status Filter */}
          <div className="relative">
            <select
              aria-label="Filter charts by batch status"
              value={statusFilter}
              onChange={(e) => handleStatusFilterChange(e.target.value)}
              className="w-full h-9 pl-3 pr-8 text-xs font-semibold bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10  cursor-pointer appearance-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active Only (Incubating)</option>
              <option value="COMPLETED">Completed Only (Hatched)</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* 3. Batch Selector */}
          <div className="relative">
            <Filter className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <select
              aria-label="Select analytics batch"
              value={selectedBatchId}
              onChange={(e) => handleBatchChange(e.target.value)}
              disabled={isLoadingBatch}
              className="w-full h-9 pl-8 pr-8 text-xs font-semibold bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10  cursor-pointer disabled:opacity-60 appearance-none"
            >
              <option value="ALL">
                {filteredBatches.length === batches.length
                  ? 'All Batches (Facility Total)'
                  : `All Filtered Batches (${filteredBatches.length} available)`}
              </option>
              {filteredBatches.map((b) => (
                <option key={b.batch_id} value={b.batch_id}>
                  {b.batch_code} • {b.breed} ({b.current_stage || 'Incubating'})
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-semibold">Operational analytics</h2><button className="border border-border rounded-lg px-3 py-2" disabled={isLoading || isLoadingBatch} onClick={() => { void fetchData(); void handleBatchChange(selectedBatchId); }}>Refresh analytics</button></div>
      {isError && <p role="alert" className="text-amber-900 bg-amber-50 border border-amber-300 rounded-xl p-4">Refresh failed. Showing previously loaded analytics; use Refresh analytics to try again.</p>}
      <OperationalCharts batches={selectedBatchId === 'ALL' ? filteredBatches : filteredBatches.filter(batch => batch.batch_id === selectedBatchId)} />
      <details className="text-sm"><summary className="cursor-pointer text-brand py-2">View candling coverage counts</summary><div className="overflow-x-auto"><table className="w-full text-left"><thead><tr><th>Batch</th><th>Scanned</th><th>Eggs set</th></tr></thead><tbody>{(selectedBatchId === 'ALL' ? filteredBatches : filteredBatches.filter(batch => batch.batch_id === selectedBatchId)).map(batch => <tr key={batch.batch_id}><td>{batch.batch_code}</td><td>{batch.total_scanned}</td><td>{batch.initial_egg_count}</td></tr>)}</tbody></table></div></details>
      <p className="text-slate-600">{selectedBatchId === 'ALL' ? 'Economic figures below are facility totals across all batches. Breed and status filters apply to the charts above. Select one batch for its economic estimates and forecast.' : 'Economic figures and forecast below apply to the selected batch.'} Figures are estimates, not confirmed sales.</p>
      {batchError && <p role="alert" className="text-red-700">Batch analytics could not be loaded. Use Refresh analytics to retry.</p>}
      {/* Contextual Active Batch Banner (if filtered) */}
      {isBatchFiltered && selectedBatchInfo && (
        <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs  animate-in fade-in duration-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-100 border border-amber-300 flex items-center justify-center flex-shrink-0">
              <Layers className="w-4 h-4 text-amber-900" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold text-amber-950 text-sm">{selectedBatchInfo.batch_code}</span>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                  {selectedBatchInfo.breed}
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-card text-slate-700 border border-slate-200">
                  {selectedBatchInfo.current_stage}
                </span>
              </div>
              <p className="text-amber-800 text-[11px] mt-0.5">
                Incubator: <strong>{selectedBatchInfo.incubator_id}</strong> • Day {batchAnalytics?.elapsed_days || 0} of 28 • Set Date: {selectedBatchInfo.set_date}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-amber-900 font-medium self-end sm:self-auto">
            <div className="text-right">
              <span className="text-[10px] text-amber-700 uppercase tracking-wider block font-bold">Fertility Rate</span>
              <span className="text-sm font-semibold text-emerald-800">{batchAnalytics?.day_10_fertility_rate ?? 0}%</span>
            </div>
            <div className="text-right border-l border-amber-200 pl-4">
              <span className="text-[10px] text-amber-700 uppercase tracking-wider block font-bold">Total Eggs</span>
              <span className="text-sm font-semibold text-slate-900">{selectedBatchInfo.initial_egg_count}</span>
            </div>
          </div>
        </div>
      )}

      {/* Day 28 Biological Forecast Card (when batch is filtered) */}
      {isBatchFiltered && (
        <BatchForecastCard forecast={batchForecast} isLoading={isLoadingBatch} />
      )}

      {((selectedBatchId === 'ALL' && economic) || isBatchFiltered) && <>
      {/* Economic metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Penoy Eggs Salvaged"
          value={`${penoyCount}`}
          unit="eggs"
          subtitle={isBatchFiltered ? "Culled from this batch on Day 10" : "Culled across all facility batches"}
          icon={Coins}
          highlightColor="amber"
        />
        <StatCard
          title="Penoy Salvage Revenue"
          value={`₱${salvageRev.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle={`@ ₱${economic?.penoy_unit_price_php ?? 14.0}/egg market price`}
          icon={TrendingUp}
          highlightColor="amber"
        />
        <StatCard
          title="Estimated Electricity Savings"
          value={`₱${powerSaved.toFixed(2)}`}
          subtitle="Calculated using backend energy settings"
          icon={Zap}
          highlightColor="blue"
        />
        <StatCard
          title="Total Economic Benefit"
          value={`₱${totalBenefit.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle={isBatchFiltered ? "Estimated salvage + power saved" : "Salvage + power saved + projected duckling revenue"}
          icon={Award}
          highlightColor="green"
        />
      </div>

      {/* Day-10 Penoy Economic Recovery Model */}
      <div className="bg-card border border-border rounded-xl p-5 ">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Coins className="w-4 h-4 text-brand" />
          <div>
            <h3 className="text-base font-bold text-foreground">
              Day-10 Penoy Economic Recovery Model
            </h3>
            <p className="text-xs text-slate-500">
              Commercial value recovered by early-diverting unfertilized eggs on Day 10 into the local food market instead of incubating to Day 28.
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Recovery Metric 1: Food Salvage */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
            <span className="text-xs font-bold text-slate-600 block">Direct Penoy Food Salvage</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold text-amber-800 font-mono">
                ₱{salvageRev.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              <strong className="text-slate-800">{penoyCount} eggs</strong> valued using the backend Penoy price
            </p>
          </div>

          {/* Recovery Metric 2: Incubator Power Avoided */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
            <span className="text-xs font-bold text-slate-600 block">Incubator Power Avoided</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold text-emerald-800 font-mono">
                ₱{powerSaved.toFixed(2)}
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              Estimated savings from early removal, using configured energy costs
            </p>
          </div>

          {/* Recovery Metric 3: Total Realized Value */}
          <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 flex flex-col justify-center space-y-1">
            <span className="text-xs text-amber-900 font-bold uppercase tracking-wider block">
              Total Estimated Benefit
            </span>
            <span className="text-2xl font-semibold text-brand font-mono">
              ₱{totalBenefit.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[11px] text-amber-800 font-medium">
              Includes projected duckling revenue in facility totals
            </span>
          </div>
        </div>

        <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-600">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
          <span>
            Day 10 infertile results identify Penoy recovery candidates for operator assessment.
          </span>
        </div>
      </div>

      </>}

      {/* Duck Breed Performance Comparison Matrix */}
      <div className="bg-card border border-border rounded-xl p-5 ">
        <div className="pb-3 border-b border-slate-100">
          <h3 className="text-base font-bold text-foreground">
            Facility breed results
          </h3>
          <p className="text-xs text-slate-500">
            Recorded facility totals by Itik Pinas breed. Batch status and batch selection do not filter this table.
          </p>
        </div>

        <div className="overflow-x-auto mt-3">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Duck Breed</th>
                <th className="py-3 px-4">Total Evaluated</th>
                <th className="py-3 px-4">Fertile Count</th>
                <th className="py-3 px-4">Fertility Rate</th>
                <th className="py-3 px-4">Penoy Culled</th>
                <th className="py-3 px-4">Hatched Count</th>
                <th className="py-3 px-4 text-right">Hatchability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {breedMetrics.filter(b => breedFilter === 'ALL' || b.breed === breedFilter).map((b) => {
                const isSelected = breedFilter !== 'ALL' && b.breed === breedFilter;
                return (
                  <tr
                    key={b.breed}
                    className={`transition-colors ${
                      isSelected ? 'bg-amber-50/80 font-semibold' : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className="py-3 px-4 font-bold text-foreground">
                      <div className="flex items-center gap-1.5">
                        <span>{b.breed}</span>
                        {isSelected && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-200 text-amber-900">
                            Filtered
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-medium">{b.total_eggs ?? 0} eggs</td>
                    <td className="py-3 px-4 text-emerald-700 font-bold">{b.fertile_count ?? 0}</td>
                    <td className="py-3 px-4 font-bold text-emerald-800">{b.fertility_rate ?? 0}%</td>
                    <td className="py-3 px-4 text-amber-800 font-semibold">
                      {b.infertile_count ?? 0} ({b.total_eggs > 0 ? (((b.infertile_count ?? 0) / b.total_eggs) * 100).toFixed(1) : '0.0'}%)
                    </td>
                    <td className="py-3 px-4 text-slate-800 font-bold">{b.hatched_count ?? 0}</td>
                    <td className="py-3 px-4 text-right font-semibold text-slate-900">{b.hatchability_rate ?? 0}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
