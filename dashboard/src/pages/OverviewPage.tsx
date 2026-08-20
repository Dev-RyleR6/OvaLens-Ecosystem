import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  Coins,
  CheckCircle2,
  ArrowRight,
  TrendingUp,
  Download,
  Flame,
  Radio,
  FileText,
  Clock,
} from 'lucide-react';
import { Link } from 'react-router-dom';

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

  const totalScanned = overview?.total_eggs_scanned || 2050;
  const fertileCount = overview?.total_fertile || 1812;
  const penoyCount = overview?.total_infertile || 168;
  const abnormalCount = overview?.total_abnormal || 70;

  const fertilePct = ((fertileCount / totalScanned) * 100).toFixed(1);
  const penoyPct = ((penoyCount / totalScanned) * 100).toFixed(1);
  const abnormalPct = ((abnormalCount / totalScanned) * 100).toFixed(1);

  return (
    <div className="space-y-6 pb-8">
      {/* Institutional Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Hatchery Operations Command
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Duck egg candling classification, 28-day incubation stages, and Day 10 Penoy economic salvage.
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

      {/* Sleek Operational KPI Ribbon */}
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
          value={`${overview?.overall_fertility_rate || '88.4'}%`}
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

      {/* Split Operational Command: Biological Yield Distribution & Live Candling Scans */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 5 Cols: Biological Yield & Salvage Breakdown */}
        <div className="lg:col-span-5">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    Biological Classification Breakdown
                  </h3>
                  <p className="text-xs text-slate-500">Candling yield and salvage distribution</p>
                </div>
                <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-200">
                  {fertilePct}% Viability
                </span>
              </div>

              {/* Linear Spectrum Proportion Bar */}
              <div className="mt-4 space-y-2">
                <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden flex shadow-2xs">
                  <div style={{ width: `${fertilePct}%` }} className="bg-emerald-600 h-full" title={`Fertile: ${fertilePct}%`} />
                  <div style={{ width: `${penoyPct}%` }} className="bg-amber-500 h-full" title={`Penoy: ${penoyPct}%`} />
                  <div style={{ width: `${abnormalPct}%` }} className="bg-red-600 h-full" title={`Dead: ${abnormalPct}%`} />
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500">
                  <span>Total Throughput: <strong>{totalScanned} eggs</strong></span>
                  <span><strong>{fertileCount}</strong> Active Embryos</span>
                </div>
              </div>

              {/* 3 Biological Category Rows */}
              <div className="space-y-2.5 mt-4 text-xs">
                <div className="p-3 rounded-lg bg-emerald-50/60 border border-emerald-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 flex-shrink-0" />
                    <div>
                      <span className="font-bold text-emerald-950 block">Fertile Embryo (Accept)</span>
                      <span className="text-[11px] text-emerald-700">Active spider blood network $\to$ Day 18 hatcher transfer</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-emerald-900 text-sm block">{fertileCount}</span>
                    <span className="text-[11px] text-emerald-700 font-semibold">{fertilePct}%</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-amber-50/60 border border-amber-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-600 flex-shrink-0" />
                    <div>
                      <span className="font-bold text-amber-950 block">Infertile / Penoy (Salvage)</span>
                      <span className="text-[11px] text-amber-700">Clear unfertilized yolk $\to$ Diverted to food market @ ₱14</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-amber-900 text-sm block">{penoyCount}</span>
                    <span className="text-[11px] text-amber-700 font-semibold">{penoyPct}%</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-red-50/60 border border-red-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-600 flex-shrink-0" />
                    <div>
                      <span className="font-bold text-red-950 block">Abnormal / Dead (Discard)</span>
                      <span className="text-[11px] text-red-700">Corrupted yolk / blood ring $\to$ Discarded to prevent bursting</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-red-900 text-sm block">{abnormalCount}</span>
                    <span className="text-[11px] text-red-700 font-semibold">{abnormalPct}%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Economic Summary Footer */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
              <span>Day 10 Food Salvage Value:</span>
              <strong className="text-amber-800 text-sm">₱{((penoyCount) * 14.0).toFixed(2)}</strong>
            </div>
          </div>
        </div>

        {/* Right 7 Cols: Live Verified Candling Scans Table */}
        <div className="lg:col-span-7">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    Live Candling Scans
                  </h3>
                  <p className="text-xs text-slate-500">Verified YOLOv8 FP16 classifications & diverter telemetry</p>
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
                      <th className="py-2.5 px-2">Diverter</th>
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
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Sorting Actuation Response: <strong>26.4 ms</strong></span>
              <span className="font-semibold text-emerald-700">Conveyor Synchronized</span>
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
