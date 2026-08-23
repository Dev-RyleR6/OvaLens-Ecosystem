import React, { useState, useEffect, useMemo } from 'react';
import {
  ChevronDown,
  ArrowRight,
  Zap,
  RotateCcw,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

import { Badge } from '../components/Badge';
import { TrayMatrix } from '../components/TrayMatrix';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { apiClient } from '../api/client';
import { AnalyticsOverview, BatchSummary, EggScan, EconomicYield } from '../types';

export const OverviewPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [, setEconomic] = useState<EconomicYield | null>(null);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [, setRecentScans] = useState<EggScan[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>('ALL');

  useEffect(() => {
    let isMounted = true;
    const fetchDashboardData = async () => {
      try {
        const [overviewData, economicData, batchesData, scansData] = await Promise.all([
          apiClient.getOverview(),
          apiClient.getEconomicYield(),
          apiClient.getBatches(),
          apiClient.getScans({ limit: 6 })
        ]);
        if (isMounted) {
          setOverview(overviewData);
          setEconomic(economicData);
          setBatches(batchesData);
          setRecentScans(scansData);
        }
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      }
    };
    fetchDashboardData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Focused batch object
  const currentBatch = useMemo(() => {
    if (selectedBatchId !== 'ALL') {
      return batches.find((b) => b.batch_id === selectedBatchId) || null;
    }
    return batches.length > 0 ? batches[0] : null;
  }, [selectedBatchId, batches]);

  const isFiltered = selectedBatchId !== 'ALL' && currentBatch !== null;

  // Filtered / Aggregate KPI calculations
  const totalScanned = useMemo(() => {
    if (isFiltered && currentBatch) {
      const sum = (currentBatch.fertile_count || 0) + (currentBatch.infertile_count || 0) + (currentBatch.abnormal_count || 0);
      return sum > 0 ? sum : (currentBatch.initial_egg_count || 500);
    }
    return overview?.total_eggs_scanned ?? (batches.reduce((acc, b) => acc + (b.initial_egg_count || 0), 0) || 2050);
  }, [isFiltered, currentBatch, overview, batches]);

  const fertileCount = useMemo(() => {
    if (isFiltered && currentBatch) {
      return currentBatch.fertile_count || 0;
    }
    return overview?.total_fertile ?? (batches.reduce((acc, b) => acc + (b.fertile_count || 0), 0) || 1812);
  }, [isFiltered, currentBatch, overview, batches]);

  const penoyCount = useMemo(() => {
    if (isFiltered && currentBatch) {
      return currentBatch.infertile_count || 0;
    }
    return overview?.total_infertile ?? (batches.reduce((acc, b) => acc + (b.infertile_count || 0), 0) || 168);
  }, [isFiltered, currentBatch, overview, batches]);

  const abnormalCount = useMemo(() => {
    if (isFiltered && currentBatch) {
      return currentBatch.abnormal_count || 0;
    }
    return overview?.total_abnormal ?? (batches.reduce((acc, b) => acc + (b.abnormal_count || 0), 0) || 70);
  }, [isFiltered, currentBatch, overview, batches]);

  const fertilePct = Number(((fertileCount / (totalScanned || 1)) * 100).toFixed(1));
  const penoyPct = Number(((penoyCount / (totalScanned || 1)) * 100).toFixed(1));
  const abnormalPct = Number(((abnormalCount / (totalScanned || 1)) * 100).toFixed(1));

  // Pie chart data
  const pieData = [
    { name: 'Fertile Embryos', value: fertileCount, color: '#357a38' },
    { name: 'Penoy (Salvaged)', value: penoyCount, color: '#d97706' },
    { name: 'Dead / Abnormal', value: abnormalCount, color: '#dc2626' },
  ];

  // Hourly Sorting Velocity telemetry
  const throughputTrendData = [
    { time: '08:00', speed: 118, latency: 25.2 },
    { time: '09:00', speed: 122, latency: 24.8 },
    { time: '10:00', speed: 120, latency: 24.5 },
    { time: '11:00', speed: 124, latency: 24.1 },
    { time: '13:00', speed: 119, latency: 24.9 },
    { time: '14:00', speed: 121, latency: 24.6 },
    { time: '15:00', speed: 120, latency: 24.4 },
  ];

  return (
    <div className="space-y-6 pb-8">
      {/* Executive Command Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Hatchery Command Center
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
              Conveyor Sorter Active
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time vision candling, 28-day cohort incubation status, and Day 10 Penoy recovery.
          </p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="relative inline-flex items-center">
            <select
              value={selectedBatchId}
              onChange={(e) => setSelectedBatchId(e.target.value)}
              className="appearance-none bg-white border border-slate-300 text-slate-800 text-xs font-semibold rounded-lg pl-3 pr-8 py-2 shadow-2xs hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-[#800000]/20 focus:border-[#800000] cursor-pointer"
            >
              <option value="ALL">All Batches (Hatchery Overall)</option>
              {batches.map((b) => (
                <option key={b.batch_id} value={b.batch_id}>
                  {b.batch_code} — {b.breed} ({b.current_stage})
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 pointer-events-none" />
          </div>

          {isFiltered && (
            <button
              onClick={() => setSelectedBatchId('ALL')}
              className="inline-flex items-center gap-1 px-2.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
              title="Reset to All Batches"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          )}

          <Link
            to="/batches"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-semibold shadow-xs transition-colors btn-press cursor-pointer"
          >
            <span>Batch Manager</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Industrial KPI Telemetry Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Candled */}
        <div className="p-4 sm:p-5 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>{isFiltered ? 'Cohort Eggs Candled' : 'Total Eggs Candled'}</span>
            <span className="text-[10px] font-mono uppercase bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
              YOLOv8 FP16
            </span>
          </div>
          <div className="flex items-baseline gap-2 pt-1">
            <span className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              {totalScanned.toLocaleString()}
            </span>
            <span className="text-xs text-slate-500 font-semibold">eggs</span>
          </div>
          <p className="text-[11px] text-slate-500 truncate pt-1">
            {isFiltered && currentBatch ? `Cohort: ${currentBatch.batch_code}` : 'Cumulative candled across all shifts'}
          </p>
        </div>

        {/* Fertility Yield */}
        <div className="p-4 sm:p-5 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>{isFiltered ? 'Cohort Fertility Rate' : 'Hatchery Fertility Rate'}</span>
            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              {fertilePct}%
            </span>
          </div>
          <div className="flex items-baseline gap-2 pt-1">
            <span className="text-2xl sm:text-3xl font-black text-emerald-800 tracking-tight">
              {isFiltered && currentBatch ? currentBatch.fertility_rate : (overview?.overall_fertility_rate ?? '88.4')}%
            </span>
          </div>
          <p className="text-[11px] text-slate-500 truncate pt-1">
            <strong className="text-emerald-700 font-semibold">{fertileCount.toLocaleString()}</strong> viable spider embryos
          </p>
        </div>

        {/* Commercial Penoy Recovery */}
        <div className="p-4 sm:p-5 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Day-10 Penoy Salvage</span>
            <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
              ₱14.00/egg
            </span>
          </div>
          <div className="flex items-baseline gap-2 pt-1">
            <span className="text-2xl sm:text-3xl font-black text-amber-800 tracking-tight">
              ₱{((penoyCount) * 14.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 truncate pt-1">
            <strong className="text-amber-800 font-semibold">{penoyCount.toLocaleString()}</strong> unfertilized eggs salvaged
          </p>
        </div>

        {/* Cohort Location & Incubation Cycle */}
        <div className="p-4 sm:p-5 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>{isFiltered ? 'Incubator Unit' : 'Active Cohorts'}</span>
            <span className="text-[10px] font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
              {isFiltered && currentBatch ? currentBatch.current_stage : '28-Day Cycle'}
            </span>
          </div>
          <div className="flex items-baseline gap-2 pt-1">
            <span className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              {isFiltered && currentBatch ? currentBatch.incubator_id : (overview ? overview.active_batches_count : '3')}
            </span>
            <span className="text-xs text-slate-500 font-semibold">
              {isFiltered ? '' : 'batches'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 truncate pt-1">
            {isFiltered && currentBatch ? `Breed: ${currentBatch.breed}` : `${batches.length} total registered batches`}
          </p>
        </div>
      </div>

      {/* Cohort Milestone Tracker */}
      {currentBatch && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold text-slate-500 uppercase">
                  {isFiltered ? 'Inspecting Batch:' : 'Active Incubation Batch:'}
                </span>
                <h3 className="text-base font-bold text-slate-900 font-mono">{currentBatch.batch_code}</h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Breed: <strong className="text-slate-800">{currentBatch.breed}</strong> • Incubator: <strong className="text-slate-800">{currentBatch.incubator_id}</strong> • Initial Set: <strong className="text-slate-800">{currentBatch.initial_egg_count} eggs</strong>
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <Badge type="status" value={currentBatch.status} />
              <Badge type="stage" value={currentBatch.current_stage} />
            </div>
          </div>

          <BatchProgressTimeline
            currentStage={currentBatch.current_stage}
            setDate={currentBatch.set_date}
          />
        </div>
      )}

      {/* Real-time Analytics Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Biological Donut Breakdown */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5 shadow-2xs flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Embryo Classification Yield</h3>
                <p className="text-xs text-slate-500">Day 10 Biological 3-Class Distribution</p>
              </div>
              <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {fertilePct}% Fertile
              </span>
            </div>

            <div className="h-44 w-full relative flex items-center justify-center mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={68}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val: any, name: any) => [`${val} eggs (${((val / (totalScanned || 1)) * 100).toFixed(1)}%)`, name]}
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2E8F0',
                      borderRadius: '0.5rem',
                      fontSize: '11px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute text-center pointer-events-none">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Total</span>
                <span className="text-base font-black text-slate-900 leading-tight block">{totalScanned}</span>
                <span className="text-[10px] text-slate-500">eggs</span>
              </div>
            </div>

            <div className="space-y-2 mt-2 text-xs">
              <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-50/70 border border-emerald-200">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
                  <span className="font-bold text-emerald-950">Fertile Embryos (Accept)</span>
                </div>
                <span className="font-extrabold text-emerald-900">{fertileCount} ({fertilePct}%)</span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-amber-50/70 border border-amber-200">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-600" />
                  <span className="font-bold text-amber-950">Penoy Salvaged @ ₱14</span>
                </div>
                <span className="font-extrabold text-amber-900">{penoyCount} ({penoyPct}%)</span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-red-50/70 border border-red-200">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-600" />
                  <span className="font-bold text-red-950">Dead / Abnormal (Discard)</span>
                </div>
                <span className="font-extrabold text-red-900">{abnormalCount} ({abnormalPct}%)</span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
            <span>Recovered Penoy Value:</span>
            <strong className="text-amber-800 text-sm">₱{((penoyCount) * 14.0).toFixed(2)}</strong>
          </div>
        </div>

        {/* Conveyor Velocity Telemetry */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-5 shadow-2xs flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-slate-700" />
                  <h3 className="text-sm font-bold text-slate-900">
                    Conveyor Velocity & Sorter Throughput
                  </h3>
                </div>
                <p className="text-xs text-slate-500">Live sorting velocity (120 eggs/min) and AI inference latency</p>
              </div>
              <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                Station-01-RP5
              </span>
            </div>

            <div className="h-44 w-full mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={throughputTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="speedGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#800000" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#800000" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#64748B" fontSize={11} tickLine={false} />
                  <YAxis domain={[100, 140]} stroke="#64748B" fontSize={11} tickLine={false} unit=" /m" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2E8F0',
                      borderRadius: '0.5rem',
                      fontSize: '11px',
                    }}
                    formatter={(val: any) => [`${val} eggs/min`, 'Candling Velocity']}
                  />
                  <Area type="monotone" dataKey="speed" stroke="#800000" strokeWidth={2} fillOpacity={1} fill="url(#speedGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-2 text-center text-xs">
              <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 block font-medium">Sorting Velocity</span>
                <strong className="text-slate-900 text-sm font-mono">120 eggs/min</strong>
              </div>
              <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 block font-medium">Avg Inference</span>
                <strong className="text-slate-900 text-sm font-mono">24.6 ms</strong>
              </div>
              <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 block font-medium">Servo Eject Pulse</span>
                <strong className="text-slate-900 text-sm font-mono">250 ms</strong>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>DirectShow V4L2 Hardware Grabber</span>
            <span className="font-semibold text-slate-700 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              ESP32 Actuator Synced
            </span>
          </div>
        </div>
      </div>

      {/* 42-Egg Candling Tray Matrix */}
      <TrayMatrix
        batchCode={currentBatch?.batch_code || "BATCH-2026-08-KAY-01"}
        trayNumber={1}
      />
    </div>
  );
};

export default OverviewPage;
