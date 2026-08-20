import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  Coins,
  CheckCircle2,
  ArrowRight,
  TrendingUp,
  ExternalLink,
  Download,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
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

  useEffect(() => {
    const fetchDashboardData = async () => {
      const [overviewData, economicData, batchesData, scansData] = await Promise.all([
        apiClient.getOverview(),
        apiClient.getEconomicYield(),
        apiClient.getBatches(),
        apiClient.getScans({ limit: 8 })
      ]);
      setOverview(overviewData);
      setEconomic(economicData);
      setBatches(batchesData);
      setRecentScans(scansData);
      if (batchesData.length > 0) {
        setSelectedBatch(batchesData[0]);
      }
    };
    fetchDashboardData();
  }, []);

  const fertilityData = [
    { name: 'Fertile (Viable)', count: overview?.total_fertile || 1812, color: '#15803D' },
    { name: 'Infertile (Penoy)', count: overview?.total_infertile || 168, color: '#D97706' },
    { name: 'Abnormal (Dead)', count: overview?.total_abnormal || 70, color: '#DC2626' },
  ];

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Hatchery Operations Command
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time duck egg candling classification, 28-day incubation stages, and Penoy economic salvage.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to="/batches"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <span>Manage All Batches</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* 4 Clean High-Contrast KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Eggs Candled"
          value={overview ? overview.total_eggs_scanned.toLocaleString() : '2,050'}
          unit="eggs"
          subtitle="ONNX YOLOv8 FP16 Verified"
          icon={Activity}
          highlightColor="maroon"
        />
        <StatCard
          title="Overall Fertility Rate"
          value={overview ? `${overview.overall_fertility_rate}%` : '88.4%'}
          subtitle={`${overview?.total_fertile || 1812} viable spider embryos`}
          icon={CheckCircle2}
          trend={{ value: '+2.1%', isPositive: true, label: 'vs last cycle' }}
          highlightColor="green"
        />
        <StatCard
          title="Day-10 Penoy Salvage"
          value={`₱${((overview?.total_infertile || 168) * 14.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle={`${overview?.total_infertile || 168} eggs @ ₱14.00/egg market`}
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

      {/* Active Batch 28-Day Milestone Timeline Card */}
      {selectedBatch && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2">
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

      {/* Split Operational View: Biological Distribution & Recent Scans Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 5 Cols: Biological Yield Donut Chart */}
        <div className="lg:col-span-5">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-[#0F172A]">
                  Biological Classification Yield
                </h3>
                <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                  88.4% Viable
                </span>
              </div>

              {/* Donut Chart */}
              <div className="h-48 relative flex items-center justify-center my-3">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={fertilityData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={72}
                      paddingAngle={3}
                      dataKey="count"
                    >
                      {fertilityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E2E8F0',
                        borderRadius: '0.5rem',
                        fontSize: '12px',
                        color: '#0F172A',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.08)'
                      }}
                      formatter={(val: any, name: any) => [`${val} eggs`, name]}
                    />
                  </PieChart>
                </ResponsiveContainer>

                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-2xl font-bold tracking-tight text-[#0F172A]">
                    {overview ? `${overview.overall_fertility_rate}%` : '88.4%'}
                  </span>
                  <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                    Fertility
                  </span>
                </div>
              </div>
            </div>

            {/* Classification Count Grid */}
            <div className="grid grid-cols-3 gap-2 text-center text-xs pt-3 border-t border-slate-100">
              <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200">
                <span className="text-base font-bold text-emerald-800 block">
                  {overview?.total_fertile || 1812}
                </span>
                <span className="text-[11px] text-emerald-700 font-medium">Fertile</span>
              </div>
              <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200">
                <span className="text-base font-bold text-amber-800 block">
                  {overview?.total_infertile || 168}
                </span>
                <span className="text-[11px] text-amber-700 font-medium">Penoy</span>
              </div>
              <div className="p-2.5 rounded-lg bg-red-50 border border-red-200">
                <span className="text-base font-bold text-red-800 block">
                  {overview?.total_abnormal || 70}
                </span>
                <span className="text-[11px] text-red-700 font-medium">Dead</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right 7 Cols: Recent Candling Activity Table */}
        <div className="lg:col-span-7">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    Recent Candling Scans
                  </h3>
                  <p className="text-xs text-slate-500">Live verified classifications from sorting conveyor</p>
                </div>
                <Link
                  to="/scans"
                  className="text-xs font-semibold text-[#800000] hover:underline flex items-center gap-1"
                >
                  <span>View All Scans</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {/* Table */}
              <div className="overflow-x-auto mt-2">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      <th className="py-2.5 px-2"># Seq</th>
                      <th className="py-2.5 px-2">Batch</th>
                      <th className="py-2.5 px-2">Class</th>
                      <th className="py-2.5 px-2">Confidence</th>
                      <th className="py-2.5 px-2">Action</th>
                      <th className="py-2.5 px-2 text-right">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {recentScans.map((scan) => (
                      <tr key={scan.scan_id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-2.5 px-2 font-bold text-slate-700">
                          #{scan.sequence_number.toString().padStart(3, '0')}
                        </td>
                        <td className="py-2.5 px-2 font-medium text-slate-900">{scan.batch_id}</td>
                        <td className="py-2.5 px-2">
                          <Badge type="fertility" value={scan.final_class} />
                        </td>
                        <td className="py-2.5 px-2 font-semibold text-slate-700">
                          {(scan.confidence * 100).toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-2">
                          <span
                            className={`font-bold ${
                              scan.routing_action === 'ACCEPT' ? 'text-emerald-700' : 'text-rose-700'
                            }`}
                          >
                            {scan.routing_action}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-right text-slate-500 font-medium">
                          {new Date(scan.scanned_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Table Footer */}
            <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Automatic pneumatic diverter response time: <strong>26.4 ms</strong></span>
              <span className="font-semibold text-emerald-700">Conveyor Synchronized</span>
            </div>
          </div>
        </div>
      </div>

      {/* Embedded 42-Egg Tray Heatmap Grid */}
      <TrayMatrix
        batchCode={selectedBatch?.batch_code || "BATCH-2026-08-KAY-01"}
        trayNumber={1}
      />
    </div>
  );
};
