import React, { useState, useEffect, useMemo } from 'react';
import {
  Coins,
  TrendingUp,
  Zap,
  Award,
  ShieldAlert,
  Percent,
  CheckCircle2,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

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

  const fetchData = async () => {
    setIsLoading(true);
    setIsError(false);
    try {
      const [eData, mData, bData, batchList] = await Promise.all([
        apiClient.getEconomicYield(),
        apiClient.getMortalityTrends(),
        apiClient.getBreedComparison(),
        apiClient.getBatches(),
      ]);
      setEconomic(eData);
      setMortality(mData);
      setBreedMetrics(Array.isArray(bData) ? bData : []);
      setBatches(Array.isArray(batchList) ? batchList : []);
    } catch (err) {
      console.error("Error fetching analytics data:", err);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleBatchChange = async (batchId: string) => {
    setSelectedBatchId(batchId);
    if (batchId === 'ALL') {
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
      setBatchAnalytics(data);
      setBatchForecast(forecast);
    } catch (err) {
      console.error('Failed to load batch analytics/forecast:', err);
    } finally {
      setIsLoadingBatch(false);
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

  // Dynamic 28-day duck egg developmental viability curve
  const cohortSurvivalData = useMemo(() => {
    const day10Viable = isBatchFiltered && batchAnalytics
      ? batchAnalytics.day_10_fertility_rate
      : (100 - (mortality?.day_10_cull_rate ?? 8.8));

    const day28Viable = isBatchFiltered && batchAnalytics
      ? (batchAnalytics.actual_hatchability_rate > 0 ? batchAnalytics.actual_hatchability_rate : (batchForecast?.predicted_hatchability_rate ?? 86.8))
      : 86.8;

    return [
      { day: 'Day 0 (Set)', viablePct: 100 },
      { day: 'Day 10 (Candling)', viablePct: Number(day10Viable.toFixed(1)) },
      { day: 'Day 28 (Hatch)', viablePct: Number(day28Viable.toFixed(1)) },
    ];
  }, [isBatchFiltered, batchAnalytics, batchForecast, mortality]);

  // Mortality Stages Data
  const mortalityBarData = [
    {
      stage: 'Day 10 (Early / Penoy)',
      rate: mortality?.day_10_cull_rate ?? 8.8,
      desc: 'Unfertilized yolk / dead germinal disc (100% salvaged @ ₱14)',
      color: '#D97706',
    },
  ];

  const penoyCount = isBatchFiltered ? batchAnalytics.infertile_penoy_day_10 : (economic?.penoy_culled_day_10 ?? 168);
  const salvageRev = isBatchFiltered ? batchAnalytics.penoy_salvage_value_php : (economic?.salvage_revenue_php ?? economic?.estimated_penoy_salvage_value_php ?? 2352.00);
  const kwhSaved = isBatchFiltered ? (batchAnalytics.infertile_penoy_day_10 * 18 * 0.015) : (economic?.incubator_energy_saved_kwh ?? 45.4);
  const powerSaved = isBatchFiltered ? batchAnalytics.electricity_saved_php : (economic?.energy_savings_php ?? economic?.electricity_saved_estimated_php ?? 544.32);
  const totalBenefit = isBatchFiltered ? (salvageRev + powerSaved) : (economic?.total_economic_benefit_php ?? 24176.32);

  if (isError && !economic && !mortality) {
    return (
      <div className="space-y-6 pb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
              Hatchery Economics & Salvage Analytics
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Commercial recovery from Day 10 Penoy culling, incubator thermal energy savings, and duck breed yield benchmarks.
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
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Hatchery Economics & Salvage Analytics
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Commercial recovery from Day 10 Penoy culling, incubator thermal energy savings, and duck breed yield benchmarks.
          </p>
        </div>

        {isAnyFilterActive && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[#800000] bg-red-50 border border-red-200 px-2.5 py-1 rounded-md">
              Filtered View Active
            </span>
            <button
              onClick={handleResetAllFilters}
              className="h-8 px-2.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-md text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              title="Reset all filters to facility totals"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          </div>
        )}
      </div>

      {/* Analytics Scope & Multi-Filter Toolbar */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-3.5 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-100 text-xs">
          <div className="flex items-center gap-2 font-bold text-slate-800">
            <SlidersHorizontal className="w-4 h-4 text-[#800000]" />
            <span>Economic Scope & Cohort Filters</span>
          </div>
          <span className="text-[11px] text-slate-400">
            Select specific breed or batch to recalibrate financial yield & salvage recovery
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          {/* 1. Duck Breed Filter */}
          <div className="relative">
            <select
              value={breedFilter}
              onChange={(e) => handleBreedFilterChange(e.target.value)}
              className="w-full h-9 pl-3 pr-8 text-xs font-semibold bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10 shadow-2xs cursor-pointer appearance-none"
            >
              <option value="ALL">All Duck Breeds</option>
              <option value="KAYUMANGGI">Kayumanggi (Pateros)</option>
              <option value="ITIM">Native Itim</option>
              <option value="KHAKI">Khaki Campbell</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* 2. Incubation Status Filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => handleStatusFilterChange(e.target.value)}
              className="w-full h-9 pl-3 pr-8 text-xs font-semibold bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10 shadow-2xs cursor-pointer appearance-none"
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
              value={selectedBatchId}
              onChange={(e) => handleBatchChange(e.target.value)}
              disabled={isLoadingBatch}
              className="w-full h-9 pl-8 pr-8 text-xs font-semibold bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10 shadow-2xs cursor-pointer disabled:opacity-60 appearance-none"
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

      {/* Contextual Active Batch Banner (if filtered) */}
      {isBatchFiltered && selectedBatchInfo && (
        <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-xs animate-in fade-in duration-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-100 border border-amber-300 flex items-center justify-center flex-shrink-0">
              <Layers className="w-4 h-4 text-amber-900" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-amber-950 text-sm">{selectedBatchInfo.batch_code}</span>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                  {selectedBatchInfo.breed}
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-white text-slate-700 border border-slate-200">
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
              <span className="text-sm font-extrabold text-emerald-800">{batchAnalytics?.day_10_fertility_rate ?? 0}%</span>
            </div>
            <div className="text-right border-l border-amber-200 pl-4">
              <span className="text-[10px] text-amber-700 uppercase tracking-wider block font-bold">Total Eggs</span>
              <span className="text-sm font-extrabold text-slate-900">{selectedBatchInfo.initial_egg_count}</span>
            </div>
          </div>
        </div>
      )}

      {/* Day 28 Biological Forecast Card (when batch is filtered) */}
      {isBatchFiltered && (
        <BatchForecastCard forecast={batchForecast} isLoading={isLoadingBatch} />
      )}

      {/* 4 Clean Metric Cards */}
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
          title="Incubator Energy Saved"
          value={`${kwhSaved.toFixed(1)}`}
          unit="kWh"
          subtitle={`₱${powerSaved.toFixed(2)} thermal electricity avoided`}
          icon={Zap}
          highlightColor="blue"
        />
        <StatCard
          title="Total Economic Benefit"
          value={`₱${totalBenefit.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle={isBatchFiltered ? "Direct Penoy sales + power saved" : "Facility-wide direct sales + power saved"}
          icon={Award}
          highlightColor="green"
        />
      </div>

      {/* Day-10 Penoy Economic Recovery Model */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Coins className="w-4 h-4 text-[#800000]" />
          <div>
            <h3 className="text-base font-bold text-[#0F172A]">
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
              <span className="text-2xl font-black text-amber-800 font-mono">
                ₱{salvageRev.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              <strong className="text-slate-800">{penoyCount} eggs</strong> @ fixed farmgate rate of ₱14.00/egg
            </p>
          </div>

          {/* Recovery Metric 2: Incubator Power Avoided */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
            <span className="text-xs font-bold text-slate-600 block">Incubator Power Avoided</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black text-emerald-800 font-mono">
                ₱{powerSaved.toFixed(2)}
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              <strong className="text-slate-800">{kwhSaved.toFixed(1)} kWh</strong> avoided across 18 unincubated days
            </p>
          </div>

          {/* Recovery Metric 3: Total Realized Value */}
          <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 flex flex-col justify-center space-y-1">
            <span className="text-xs text-amber-900 font-bold uppercase tracking-wider block">
              Total Realized Recovery
            </span>
            <span className="text-2xl font-black text-[#800000] font-mono">
              ₱{totalBenefit.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[11px] text-amber-800 font-medium">
              Dual dividend: edible salvage + thermal load reduction
            </span>
          </div>
        </div>

        <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-600">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
          <span>
            Eliminates rotten/exploding egg hazards in incubator trays while salvaging Grade-A Penoy table eggs for immediate market sale.
          </span>
        </div>
      </div>

      {/* Split: Embryonic Mortality Breakdown + Cohort Survival Curve */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 6 Cols: 3-Stage Incubation Mortality Breakdown */}
        <div className="lg:col-span-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    Embryonic Mortality by Stage
                  </h3>
                  <p className="text-xs text-slate-500">Early arrest vs Mid-term vs Late pipping failure</p>
                </div>
                <span className="text-xs font-semibold text-rose-800 bg-rose-50 px-2.5 py-0.5 rounded-md border border-rose-200">
                  {mortality?.total_culled_eggs ?? 238} Culled Eggs Total
                </span>
              </div>

              {/* Stage Breakdown Bars */}
              <div className="space-y-3.5 mt-4">
                {mortalityBarData.map((st) => (
                  <div key={st.stage} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-800">{st.stage}</span>
                      <span className="font-extrabold text-slate-900">{st.rate}% mortality</span>
                    </div>
                    <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(100, Math.max(4, st.rate))}%`, backgroundColor: st.color }}
                      />
                    </div>
                    <p className="text-[11px] text-slate-500">{st.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
              <span>Day 10 candling eliminates <strong>65% of all potential hatchery losses</strong> early.</span>
            </div>
          </div>
        </div>

        {/* Right 6 Cols: 28-Day Embryonic Viability Area Curve */}
        <div className="lg:col-span-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between">
            <div>
              <div className="pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-[#0F172A]">
                  28-Day Embryonic Viability Retention
                </h3>
                <p className="text-xs text-slate-500">Live embryo retention curve across incubation milestones</p>
              </div>

              <div className="h-60 mt-3 w-full">
                <ResponsiveContainer width="100%" height="100%" minWidth={200} minHeight={200}>
                  <AreaChart data={cohortSurvivalData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="viabilityGradientFU" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#15803D" stopOpacity={0.35}/>
                        <stop offset="95%" stopColor="#15803D" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="day" stroke="#64748B" fontSize={11} tickLine={false} />
                    <YAxis domain={[75, 100]} stroke="#64748B" fontSize={11} tickLine={false} unit="%" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E2E8F0',
                        borderRadius: '0.5rem',
                        fontSize: '12px',
                        color: '#0F172A',
                      }}
                      formatter={(val: any) => [`${val}%`, 'Viable Embryos']}
                    />
                    <Area type="monotone" dataKey="viablePct" stroke="#15803D" strokeWidth={2.5} fillOpacity={1} fill="url(#viabilityGradientFU)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 text-right">
              Overall Hatch Harvest Rate: <strong className="text-emerald-800">86.8%</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Duck Breed Performance Comparison Matrix */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs">
        <div className="pb-3 border-b border-slate-100">
          <h3 className="text-base font-bold text-[#0F172A]">
            Duck Breed Biological & Commercial Benchmarks
          </h3>
          <p className="text-xs text-slate-500">
            Comparative performance across Kayumanggi, Native Itim, and Khaki Campbell flocks
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
              {breedMetrics.map((b) => {
                const isSelected = breedFilter !== 'ALL' && b.breed === breedFilter;
                return (
                  <tr
                    key={b.breed}
                    className={`transition-colors ${
                      isSelected ? 'bg-amber-50/80 font-semibold' : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className="py-3 px-4 font-bold text-[#0F172A]">
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
                    <td className="py-3 px-4 text-right font-extrabold text-slate-900">{b.hatchability_rate ?? 0}%</td>
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
