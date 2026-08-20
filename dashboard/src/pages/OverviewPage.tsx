import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  Coins,
  CheckCircle2,
  ArrowRight,
  Zap,
  Info,
  X,
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

import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';
import { TrayMatrix } from '../components/TrayMatrix';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { apiClient } from '../api/client';
import { AnalyticsOverview, BatchSummary, EggScan, EconomicYield } from '../types';

export const OverviewPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [economic, setEconomic] = useState<EconomicYield | null>(null);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [recentScans, setRecentScans] = useState<EggScan[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);
  const [showOnboarding, setShowOnboarding] = useState<boolean>(() => {
    return localStorage.getItem('ovalens_onboarding_dismissed') !== 'true';
  });

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
          if (batchesData.length > 0) {
            setSelectedBatch(batchesData[0]);
          }
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

  const totalScanned = overview?.total_eggs_scanned ?? 2050;
  const fertileCount = overview?.total_fertile ?? 1812;
  const penoyCount = overview?.total_infertile ?? 168;
  const abnormalCount = overview?.total_abnormal ?? 70;

  const fertilePct = Number(((fertileCount / (totalScanned || 1)) * 100).toFixed(1));
  const penoyPct = Number(((penoyCount / (totalScanned || 1)) * 100).toFixed(1));
  const abnormalPct = Number(((abnormalCount / (totalScanned || 1)) * 100).toFixed(1));

  // Pie chart data for biological distribution
  const pieData = [
    { name: 'Fertile Embryos', value: fertileCount, color: '#15803D', pct: fertilePct },
    { name: 'Penoy Salvaged', value: penoyCount, color: '#D97706', pct: penoyPct },
    { name: 'Dead / Abnormal', value: abnormalCount, color: '#DC2626', pct: abnormalPct },
  ];

  // Hourly Sorting Velocity stream (eggs/min & inference latency)
  const throughputTrendData = [
    { time: '08:00', speed: 118, latency: 25.2 },
    { time: '09:00', speed: 122, latency: 24.8 },
    { time: '10:00', speed: 120, latency: 24.5 },
    { time: '11:00', speed: 124, latency: 24.1 },
    { time: '13:00', speed: 119, latency: 24.9 },
    { time: '14:00', speed: 121, latency: 24.6 },
    { time: '15:00', speed: 120, latency: 24.4 },
  ];

  const handleDismissOnboarding = () => {
    setShowOnboarding(false);
    localStorage.setItem('ovalens_onboarding_dismissed', 'true');
  };

  return (
    <div className="space-y-6 pb-8">
      {/* Institutional Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
              Hatchery Operations Command
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              Live Sorter Feed
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time duck egg candling classification, 28-day cohort tracking, and Day 10 commercial Penoy food salvage.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to="/batches"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-semibold shadow-xs transition-colors btn-press cursor-pointer"
          >
            <span>Manage All Batches</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Operator Onboarding Quick Guide */}
      {showOnboarding && (
        <div className="relative p-4 bg-slate-900 rounded-xl text-white shadow-xs border border-slate-800 space-y-3">
          <button
            onClick={handleDismissOnboarding}
            className="absolute top-3 right-3 text-slate-400 hover:text-white p-1 rounded-md transition-colors cursor-pointer"
            title="Dismiss Guide"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-slate-300" />
            <h3 className="font-bold text-xs text-white uppercase tracking-wider">Hatchery Sorting Workflow</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 bg-slate-800/80 rounded-lg border border-slate-700 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-200">1. Cohort Setup</span>
                <span className="text-[10px] text-slate-400 font-mono">Day 0</span>
              </div>
              <p className="text-xs text-slate-300">
                Register batch identifier, select breed (Kayumanggi / Native / Khaki), and load into setter cabinet.
              </p>
            </div>

            <div className="p-3 bg-slate-800/80 rounded-lg border border-slate-700 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-200">2. Vision Candling</span>
                <span className="text-[10px] text-slate-400 font-mono">Day 10 (120/min)</span>
              </div>
              <p className="text-xs text-slate-300">
                Conveyor belt feeds eggs under optical candling box. YOLOv8 FP16 executes 24.6ms automated sorting.
              </p>
            </div>

            <div className="p-3 bg-slate-800/80 rounded-lg border border-slate-700 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-200">3. Food Salvage</span>
                <span className="text-[10px] text-slate-400 font-mono">Penoy @ ₱14</span>
              </div>
              <p className="text-xs text-slate-300">
                Unfertilized yolks are cleanly salvaged for food markets; viable embryos transfer to Day 18 hatchers.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Operational KPI Ribbon */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Eggs Candled"
          value={totalScanned.toLocaleString()}
          unit="eggs"
          subtitle="ONNX YOLOv8 FP16 Verified"
          icon={Activity}
          highlightColor="maroon"
        />
        <StatCard
          title="Overall Fertility Rate"
          value={`${overview?.overall_fertility_rate ?? '88.4'}%`}
          subtitle={`${fertileCount.toLocaleString()} viable spider embryos`}
          icon={CheckCircle2}
          trend={{ value: '+2.1%', isPositive: true, label: 'vs previous cohort' }}
          highlightColor="green"
        />
        <StatCard
          title="Day-10 Penoy Salvage"
          value={`₱${((penoyCount) * 14.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle={`${penoyCount} eggs @ ₱14.00/egg market rate`}
          icon={Coins}
          highlightColor="amber"
        />
        <StatCard
          title="Active Incubating Batches"
          value={overview ? overview.active_batches_count : '3'}
          unit="batches"
          subtitle="In 28-day incubation cycle"
          icon={Layers}
          highlightColor="blue"
        />
      </div>

      {/* Active Incubation Cohort Stage Tracker */}
      {selectedBatch && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider text-[#800000]">Active Cohort:</span>
                <h3 className="text-base font-bold text-[#0F172A]">{selectedBatch.batch_code}</h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Breed: <strong>{selectedBatch.breed}</strong> • Incubator: <strong>{selectedBatch.incubator_id}</strong> • Initial Set: <strong>{selectedBatch.initial_egg_count} eggs</strong>
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge type="status" value={selectedBatch.status} />
              <Badge type="stage" value={selectedBatch.current_stage} />
            </div>
          </div>

          <div className="pt-2">
            <BatchProgressTimeline
              currentStage={selectedBatch.current_stage}
              setDate={selectedBatch.set_date}
            />
          </div>
        </div>
      )}

      {/* Visualizations Row: Candling Spectrum Donut + Live Conveyor Velocity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 5 Cols: Biological Spectrum Donut */}
        <div className="lg:col-span-5">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    Biological Candling Spectrum
                  </h3>
                  <p className="text-xs text-slate-500">Distribution across 3 verified embryo classes</p>
                </div>
                <span className="text-xs font-extrabold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-200">
                  {fertilePct}% Viable
                </span>
              </div>

              {/* Donut Chart Visual */}
              <div className="h-44 w-full relative flex items-center justify-center mt-2">
                <ResponsiveContainer width="100%" height="100%" minWidth={150} minHeight={150}>
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
                      formatter={(val: any, name: any) => [`${val} eggs (${((val / totalScanned) * 100).toFixed(1)}%)`, name]}
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E2E8F0',
                        borderRadius: '0.5rem',
                        fontSize: '11px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* Center Stat */}
                <div className="absolute text-center pointer-events-none">
                  <span className="text-xs text-slate-400 font-semibold uppercase block">Total</span>
                  <span className="text-base font-black text-slate-900 leading-tight block">{totalScanned}</span>
                  <span className="text-[10px] text-slate-500">eggs</span>
                </div>
              </div>

              {/* 3 Color Labels */}
              <div className="space-y-2 mt-2 text-xs">
                <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-50/60 border border-emerald-200">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
                    <span className="font-bold text-emerald-950">Fertile Embryos (Accept)</span>
                  </div>
                  <span className="font-extrabold text-emerald-900">{fertileCount} ({fertilePct}%)</span>
                </div>

                <div className="flex items-center justify-between p-2 rounded-lg bg-amber-50/60 border border-amber-200">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-600" />
                    <span className="font-bold text-amber-950">Penoy Salvaged @ ₱14</span>
                  </div>
                  <span className="font-extrabold text-amber-900">{penoyCount} ({penoyPct}%)</span>
                </div>

                <div className="flex items-center justify-between p-2 rounded-lg bg-red-50/60 border border-red-200">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-600" />
                    <span className="font-bold text-red-950">Dead / Abnormal (Discard)</span>
                  </div>
                  <span className="font-extrabold text-red-900">{abnormalCount} ({abnormalPct}%)</span>
                </div>
              </div>
            </div>

            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
              <span>Recovered Penoy Food Sales:</span>
              <strong className="text-amber-800 text-sm">₱{((penoyCount) * 14.0).toFixed(2)}</strong>
            </div>
          </div>
        </div>

        {/* Right 7 Cols: Conveyor Velocity & Shift Throughput Stream */}
        <div className="lg:col-span-7">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-slate-700" />
                    <h3 className="text-sm font-bold text-[#0F172A]">
                      Conveyor Velocity & Inference Latency Stream
                    </h3>
                  </div>
                  <p className="text-xs text-slate-500">Live operational pace (120 eggs/min SLA) and ONNX FP16 response</p>
                </div>
                <span className="text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  Station-01-RP5
                </span>
              </div>

              {/* Throughput Area Chart */}
              <div className="h-44 w-full mt-2">
                <ResponsiveContainer width="100%" height="100%" minWidth={200} minHeight={150}>
                  <AreaChart data={throughputTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="speedGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#800000" stopOpacity={0.25}/>
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
                      formatter={(val: any) => [`${val} eggs/min`, 'Candling Speed']}
                    />
                    <Area type="monotone" dataKey="speed" stroke="#800000" strokeWidth={2.5} fillOpacity={1} fill="url(#speedGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Stream Micro-Stats */}
              <div className="grid grid-cols-3 gap-2 mt-2 text-center text-xs">
                <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">Peak Speed</span>
                  <strong className="text-slate-900 text-sm">124 eggs/min</strong>
                </div>
                <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">Avg Inference</span>
                  <strong className="text-slate-900 text-sm">24.6 ms</strong>
                </div>
                <div className="p-2 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 block">Diverter Actuation</span>
                  <strong className="text-slate-900 text-sm">250 ms Pulse</strong>
                </div>
              </div>
            </div>

            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>60 FPS OpenCV DirectShow Frame Grabber</span>
              <span className="font-semibold text-slate-700 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                Conveyor Synchronized
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Embedded 42-Egg Tray Matrix Component */}
      <TrayMatrix
        batchCode={selectedBatch?.batch_code || "BATCH-2026-08-KAY-01"}
        trayNumber={1}
      />
    </div>
  );
};
