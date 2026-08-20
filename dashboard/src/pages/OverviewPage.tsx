import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  TrendingUp,
  Coins,
  Cpu,
  Eye,
  Zap,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Flame,
  HardDrive
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell
} from 'recharts';

import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';
import { TrayMatrix } from '../components/TrayMatrix';
import { CandlingAperture } from '../components/CandlingAperture';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { apiClient } from '../api/client';
import { AnalyticsOverview, BatchSummary, EggScan } from '../types';

export const OverviewPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [recentScans, setRecentScans] = useState<EggScan[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      const [overviewData, batchesData, scansData] = await Promise.all([
        apiClient.getOverview(),
        apiClient.getBatches(),
        apiClient.getScans({ limit: 10 })
      ]);
      setOverview(overviewData);
      setBatches(batchesData);
      setRecentScans(scansData);
      if (batchesData.length > 0) {
        setSelectedBatch(batchesData[0]);
      }
    };
    fetchDashboardData();
  }, []);

  const fertilityDistribution = [
    { name: 'Fertile (Accept)', count: overview?.total_fertile || 436, color: '#16A34A' },
    { name: 'Infertile (Penoy)', count: overview?.total_infertile || 48, color: '#F59E0B' },
    { name: 'Abnormal (Dead)', count: overview?.total_abnormal || 16, color: '#DC2626' },
  ];

  const breedPerformance = [
    { breed: 'Kayumanggi', fertility: 91.2, eggs: 500 },
    { breed: 'Itim (Native)', fertility: 87.5, eggs: 450 },
    { breed: 'Khaki Campbell', fertility: 84.8, eggs: 350 },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner / System Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-obsidian-900 border border-obsidian-700/80 p-4 rounded-lg shadow-xl">
        <div>
          <h2 className="text-lg font-display font-black tracking-wide text-white uppercase flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-led-pulse shadow-[0_0_8px_#10B981]" />
            Hatchery Candling Operations & Biological Telemetry
          </h2>
          <p className="text-xs font-mono text-slate-400">
            Real-time duck egg developmental monitoring • YOLOv8 ONNX FP16 Vision Engine • Foundation University
          </p>
        </div>

        {/* Quick Conveyor Control Actions */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <div className="px-3 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-300 flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-amber-400" />
            <span>CONVEYOR: <strong className="text-emerald-400">12.5 cm/s</strong></span>
          </div>
          <div className="px-3 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-300 flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-amber-400" />
            <span>THROUGHPUT: <strong className="text-amber-300">45 eggs/min</strong></span>
          </div>
        </div>
      </div>

      {/* 4 High-Density SCADA KPI Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Candled (Day 10-25)"
          value={overview ? overview.total_eggs_scanned : '500'}
          unit="eggs"
          subtitle="98.2% Optical Verification"
          icon={Activity}
          accentColor="cyan"
          trend={{ value: '100% SLA', isPositive: true, label: 'FP16 ONNX' }}
        />
        <StatCard
          title="Fertility Viability Rate"
          value={overview ? `${overview.overall_fertility_rate}%` : '87.2%'}
          subtitle={`${overview?.total_fertile || 436} Viable Spider Veins`}
          icon={CheckCircle2}
          accentColor="green"
          trend={{ value: '+2.4%', isPositive: true, label: 'vs baseline' }}
        />
        <StatCard
          title="Day 10 Penoy Salvage"
          value={`₱${((overview?.total_infertile || 48) * 14.0).toFixed(2)}`}
          subtitle={`${overview?.total_infertile || 48} Eggs Culled @ ₱14.00/egg`}
          icon={Coins}
          accentColor="amber"
          trend={{ value: '100% Salvage', isPositive: true, label: 'Food Market' }}
        />
        <StatCard
          title="Active Incubating Batches"
          value={overview ? overview.active_batches_count : '3'}
          unit="batches"
          subtitle="1,300 Total Incubator Set"
          icon={Layers}
          accentColor="maroon"
          baseline="3 Units Online"
        />
      </div>

      {/* Split Centerpiece: Physical 42-Egg Tray Heatmap + Optical Candling Aperture */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Left: Physical 42-Egg Tray Heatmap Matrix */}
        <TrayMatrix
          batchCode={selectedBatch?.batch_code || "BATCH-2026-08-KAY-01"}
          trayNumber={1}
        />

        {/* Right: Live Optical Candling Aperture & Spectral Layer Inspector */}
        <CandlingAperture
          finalClass={recentScans[0]?.final_class || 'FERTILE'}
          confidence={recentScans[0]?.confidence || 0.948}
          inferenceMs={recentScans[0]?.inference_ms || 26.4}
          sequenceNumber={recentScans[0]?.sequence_number || 42}
          batchId={selectedBatch?.batch_code || 'BATCH-2026-08-KAY-01'}
        />
      </div>

      {/* Analytics & Cohort Benchmarks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Fertility Class Breakdown Donut */}
        <div className="panel-scada p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-obsidian-700/60 pb-2">
            <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-200">
              Fertility Distribution (3-Class YOLO)
            </h3>
            <span className="text-[10px] font-mono text-slate-400">Total: 500 Eggs</span>
          </div>

          <div className="h-44 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={fertilityDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={68}
                  paddingAngle={4}
                  dataKey="count"
                >
                  {fertilityDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} stroke="#070A11" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#070A11', borderColor: '#1E293B', borderRadius: '6px', fontSize: '11px', fontFamily: 'JetBrains Mono', color: '#fff' }}
                  formatter={(val: any, name: any) => [`${val} eggs`, name]}
                />
              </PieChart>
            </ResponsiveContainer>

            {/* Inner Donut Center Metric */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-lg font-mono font-black text-white">87.2%</span>
              <span className="text-[8px] font-mono text-emerald-400 font-bold">FERTILE</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-1.5 text-center text-[10px] font-mono pt-1">
            <div className="p-1.5 bg-emerald-950/40 rounded border border-emerald-800/40">
              <span className="text-emerald-400 block font-bold">436 FERTILE</span>
              <span className="text-[9px] text-slate-400">ACCEPT</span>
            </div>
            <div className="p-1.5 bg-amber-950/40 rounded border border-amber-800/40">
              <span className="text-amber-300 block font-bold">48 PENOY</span>
              <span className="text-[9px] text-slate-400">DAY 10 CULL</span>
            </div>
            <div className="p-1.5 bg-rose-950/40 rounded border border-rose-800/40">
              <span className="text-rose-400 block font-bold">16 DEAD</span>
              <span className="text-[9px] text-slate-400">DISCARD</span>
            </div>
          </div>
        </div>

        {/* Breed Fertility Benchmark Comparison */}
        <div className="panel-scada p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-obsidian-700/60 pb-2">
            <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-200">
              Breed Fertility Benchmark
            </h3>
            <span className="text-[10px] font-mono text-emerald-400 font-bold">KAYUMANGGI LEADS</span>
          </div>

          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={breedPerformance} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <XAxis dataKey="breed" stroke="#64748B" fontSize={10} tickLine={false} />
                <YAxis domain={[75, 100]} stroke="#64748B" fontSize={10} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#070A11', borderColor: '#1E293B', borderRadius: '6px', fontSize: '11px', fontFamily: 'JetBrains Mono', color: '#fff' }}
                  formatter={(val: any) => [`${val}%`, 'Fertility Rate']}
                />
                <Bar dataKey="fertility" fill="#800000" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="text-[10px] font-mono text-slate-400 text-center pt-1 border-t border-obsidian-800">
            Kayumanggi yields highest Day 10 viability (91.2%) vs Native Itim (87.5%).
          </div>
        </div>

        {/* Live Conveyor Scan Ticker */}
        <div className="panel-scada p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-obsidian-700/60 pb-2">
            <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-led-pulse" />
              Live Sorter Scan Feed
            </h3>
            <span className="text-[10px] font-mono text-slate-400">Stream: Active</span>
          </div>

          <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
            {recentScans.slice(0, 5).map((scan) => (
              <div
                key={scan.scan_id}
                className="p-2 bg-obsidian-950 rounded border border-obsidian-800 flex items-center justify-between text-[11px] font-mono hover:border-obsidian-700 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="font-bold text-amber-400">#{scan.sequence_number.toString().padStart(3, '0')}</span>
                  <Badge type="fertility" value={scan.final_class} size="sm" />
                </div>
                <div className="flex items-center gap-3 text-[10px]">
                  <span className="text-slate-300">{(scan.confidence * 100).toFixed(0)}%</span>
                  <span className="text-slate-500">{scan.inference_ms}ms</span>
                  <span className={`font-bold ${scan.routing_action === 'ACCEPT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {scan.routing_action}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Active Incubation Batch Timeline */}
      {selectedBatch && (
        <div className="panel-scada p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-obsidian-700/60 pb-2">
            <div>
              <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-200">
                Active Incubation Lifecycle — {selectedBatch.batch_code}
              </h3>
              <p className="text-[10px] font-mono text-slate-400">
                Breed: <strong>{selectedBatch.breed}</strong> • Incubator: <strong>{selectedBatch.incubator_id}</strong> • Initial Set: <strong>{selectedBatch.initial_egg_count} eggs</strong>
              </p>
            </div>
            <Badge type="status" value={selectedBatch.status} />
          </div>

          <BatchProgressTimeline
            currentStage={selectedBatch.current_stage}
            setDate={selectedBatch.set_date}
          />
        </div>
      )}
    </div>
  );
};
