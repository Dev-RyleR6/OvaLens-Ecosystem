import React, { useState, useEffect } from 'react';
import {
  Layers,
  Activity,
  Coins,
  Flame,
  ArrowRight,
  Download,
  Clock,
  Sparkles
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { Link } from 'react-router-dom';

import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { apiClient } from '../api/client';
import { AnalyticsOverview, EconomicYield, BatchSummary, EggScan } from '../types';

export const OverviewPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [economic, setEconomic] = useState<EconomicYield | null>(null);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [recentScans, setRecentScans] = useState<EggScan[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [oData, eData, bData, sData] = await Promise.all([
          apiClient.getOverview(),
          apiClient.getEconomicYield(),
          apiClient.getBatches(),
          apiClient.getScans({ limit: 6 })
        ]);
        setOverview(oData);
        setEconomic(eData);
        setBatches(bData);
        setRecentScans(sData);
      } catch (err) {
        console.error("Failed to load overview data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Breed breakdown data
  const breedData = [
    { breed: 'Kayumanggi', eggs: 1000, fertileRate: 90.2, color: '#800000' },
    { breed: 'Itim (Native)', eggs: 450, fertileRate: 88.0, color: '#357a38' },
    { breed: 'Khaki Campbell', eggs: 600, fertileRate: 91.0, color: '#D97706' },
  ];

  // Classification pie data
  const classPieData = overview ? [
    { name: 'Fertile (Active)', value: overview.total_fertile, color: '#357a38' },
    { name: 'Infertile (Penoy)', value: overview.total_infertile, color: '#D97706' },
    { name: 'Abnormal / Dead', value: overview.total_abnormal, color: '#DC2626' },
  ] : [];

  return (
    <div className="space-y-6">
      {/* Page Banner */}
      <div className="bg-gradient-to-r from-[#800000] via-[#5C0000] to-slate-900 rounded-2xl p-6 shadow-xl border border-[#991B1B]/40 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-400 text-slate-900 uppercase tracking-wide">
              Live Operations
            </span>
            <span className="text-xs text-amber-200/80">Bayawan Incubation Facility</span>
          </div>
          <h2 className="text-2xl font-black text-white mt-1">Hatchery Executive Overview</h2>
          <p className="text-sm text-slate-200 mt-0.5 max-w-xl">
            Real-time duck egg fertility classification, Day-10 penoy salvage tracking, and incubator lifecycle management.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/batches"
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-900/80 hover:bg-slate-900 text-white rounded-lg text-sm font-semibold border border-slate-700 transition-all shadow-md"
          >
            <Layers className="w-4 h-4 text-amber-400" />
            Manage Batches
          </Link>
          <Link
            to="/scans"
            className="flex items-center gap-2 px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-900 rounded-lg text-sm font-bold transition-all shadow-md"
          >
            <Sparkles className="w-4 h-4" />
            Live Scans
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Eggs Candled"
          value={overview ? overview.total_eggs_scanned.toLocaleString() : '---'}
          subtitle={`Avg Latency: ${overview ? overview.avg_inference_ms : 28}ms`}
          icon={Layers}
          colorScheme="maroon"
          trend={{ value: '+500 today', isPositive: true }}
        />
        <StatCard
          title="Overall Fertility Rate"
          value={overview ? `${overview.overall_fertility_rate.toFixed(1)}%` : '---'}
          subtitle={`${overview ? overview.total_fertile : 0} fertile embryos`}
          icon={Activity}
          colorScheme="green"
          trend={{ value: '+1.8% vs benchmark', isPositive: true }}
        />
        <StatCard
          title="Day 10 Penoy Economic Gain"
          value={economic ? `₱${economic.total_economic_benefit_php.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '---'}
          subtitle={`${economic ? economic.penoy_culled_day_10 : 0} eggs salvaged @ ₱14`}
          icon={Coins}
          colorScheme="amber"
          trend={{ value: '+₱544 energy saved', isPositive: true }}
        />
        <StatCard
          title="Active Incubating Batches"
          value={overview ? overview.active_batches_count : '---'}
          subtitle="Kayumanggi & Itim Flocks"
          icon={Flame}
          colorScheme="blue"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Classification Donut (1 col) */}
        <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-1">
            Fertility Distribution
          </h3>
          <p className="text-xs text-slate-400 mb-4">Total breakdown across all candling runs</p>

          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={classPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {classPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', color: '#fff' }}
                />
                <Legend
                  formatter={(value) => <span className="text-xs text-slate-300">{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Breed Benchmark Comparison (2 cols) */}
        <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-5 shadow-lg lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Breed Fertility Benchmarking
              </h3>
              <p className="text-xs text-slate-400">Fertility yield percentage by duck breed</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
              Season 2026
            </span>
          </div>

          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={breedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="breed" stroke="#64748B" fontSize={12} tickLine={false} />
                <YAxis domain={[80, 100]} stroke="#64748B" fontSize={12} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', color: '#fff' }}
                  formatter={(val: any) => [`${val}%`, 'Fertility Rate']}
                />
                <Bar dataKey="fertileRate" radius={[6, 6, 0, 0]}>
                  {breedData.map((entry, index) => (
                    <Cell key={`bar-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Active Batches & Quick Progress */}
      <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-100">Active Incubation Batches</h3>
            <p className="text-xs text-slate-400">Current 28-day lifecycle status and candling milestones</p>
          </div>
          <Link
            to="/batches"
            className="text-xs text-amber-400 hover:text-amber-300 font-semibold flex items-center gap-1 transition-colors"
          >
            View All <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="space-y-4">
          {batches.filter(b => b.status === 'INCUBATING').map((b) => (
            <div key={b.batch_id} className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-100">{b.batch_code}</span>
                  <Badge type="stage" value={b.current_stage} />
                  <span className="text-xs text-amber-400 font-medium">{b.breed}</span>
                </div>
                <p className="text-xs text-slate-400">
                  {b.initial_egg_count} eggs • Incubator: {b.incubator_id} • Fertility: <strong className="text-emerald-400">{b.fertility_rate}%</strong>
                </p>
              </div>

              <div className="w-full md:w-1/2">
                <BatchProgressTimeline currentStage={b.current_stage} setDate={b.set_date} />
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <a
                  href={apiClient.downloadPDFUrl(b.batch_id)}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> PDF
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity Scans */}
      <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-100">Live Conveyor Scan Stream</h3>
            <p className="text-xs text-slate-400">Real-time edge candling triggers and automated diverter actions</p>
          </div>
          <Link
            to="/scans"
            className="text-xs text-amber-400 hover:text-amber-300 font-semibold flex items-center gap-1 transition-colors"
          >
            Explore Scans <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4"># Sequence</th>
                <th className="py-3 px-4">Batch ID</th>
                <th className="py-3 px-4">Classification</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4">Latency</th>
                <th className="py-3 px-4">Diverter Action</th>
                <th className="py-3 px-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 font-mono">
              {recentScans.map((scan) => (
                <tr key={scan.scan_id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-2.5 px-4 font-bold text-slate-300">#{scan.sequence_number.toString().padStart(3, '0')}</td>
                  <td className="py-2.5 px-4 text-slate-300">{scan.batch_id}</td>
                  <td className="py-2.5 px-4"><Badge type="fertility" value={scan.final_class} /></td>
                  <td className="py-2.5 px-4 text-slate-200">{(scan.confidence * 100).toFixed(1)}%</td>
                  <td className="py-2.5 px-4 text-slate-400">{scan.inference_ms}ms</td>
                  <td className="py-2.5 px-4 font-sans font-bold">
                    <span className={scan.routing_action === 'ACCEPT' ? 'text-emerald-400' : 'text-red-400'}>
                      {scan.routing_action}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-slate-500 font-sans">{new Date(scan.scanned_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
