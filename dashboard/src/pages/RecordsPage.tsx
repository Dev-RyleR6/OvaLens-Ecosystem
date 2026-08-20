import React, { useState, useEffect } from 'react';
import {
  Archive,
  Search,
  Download,
  Calendar,
  Layers,
  Coins,
  CheckCircle2,
  TrendingUp,
  FileSpreadsheet,
  Clock,
  User,
  Zap,
  Award,
} from 'lucide-react';
import { apiClient } from '../api/client';
import {
  BatchSummary,
  PenoySalvageRecord,
  HistoricalRecordSummary,
  CandlingSession,
} from '../types';
import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';
import { CandlingCertificateModal } from '../components/CandlingCertificateModal';

export const RecordsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'BATCHES' | 'SALVAGE' | 'SESSIONS'>('BATCHES');
  const [summary, setSummary] = useState<HistoricalRecordSummary | null>(null);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [salvageRecords, setSalvageRecords] = useState<PenoySalvageRecord[]>([]);
  const [sessions, setSessions] = useState<CandlingSession[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);
  const [isCertificateOpen, setIsCertificateOpen] = useState(false);

  useEffect(() => {
    const fetchRecords = async () => {
      const [sum, bData, salData, sessData] = await Promise.all([
        apiClient.getHistoricalSummary(),
        apiClient.getBatches(),
        apiClient.getPenoySalvageRecords(),
        apiClient.getSessions(),
      ]);
      setSummary(sum);
      setBatches(bData);
      setSalvageRecords(salData);
      setSessions(sessData);
    };
    fetchRecords();
  }, []);

  const handleOpenCertificate = (b: BatchSummary) => {
    setSelectedBatch(b);
    setIsCertificateOpen(true);
  };

  const filteredBatches = batches.filter(
    (b) =>
      b.batch_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.breed.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredSalvage = salvageRecords.filter(
    (s) =>
      s.batch_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.buyer_destination.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredSessions = sessions.filter(
    (s) =>
      s.batch_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.operator_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Candling & Hatchery Historical Records
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable archives of past candling cohorts, Day 10 Penoy commercial sales, and operator shift sessions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const csvContent = "data:text/csv;charset=utf-8," +
                "BatchCode,Breed,InitialEggs,Fertile,Penoy,Dead,FertilityRate,HatchabilityRate\n" +
                batches.map(b => `${b.batch_code},${b.breed},${b.initial_egg_count},${b.fertile_count},${b.infertile_count},${b.abnormal_count},${b.fertility_rate}%,${b.hatchability_rate}%`).join("\n");
              const encodedUri = encodeURI(csvContent);
              const link = document.createElement("a");
              link.setAttribute("href", encodedUri);
              link.setAttribute("download", `OvaLens_Historical_Archive_${new Date().toISOString().slice(0,10)}.csv`);
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4 text-slate-600" />
            <span>Export Archive (CSV)</span>
          </button>
        </div>
      </div>

      {/* Top Historical KPI Summary Ribbon */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Lifetime Batches"
          value={summary ? summary.total_lifetime_batches : 18}
          unit="cohorts"
          subtitle="All historical incubation runs"
          icon={Archive}
          highlightColor="maroon"
        />
        <StatCard
          title="Total Eggs Candled"
          value={summary ? summary.total_lifetime_eggs_candled.toLocaleString() : "8,950"}
          unit="eggs"
          subtitle="Processed through Edge vision"
          icon={Layers}
          highlightColor="blue"
        />
        <StatCard
          title="Lifetime Penoy Salvaged"
          value={`₱${summary ? summary.total_lifetime_penoy_salvaged_php.toLocaleString('en-US', { minimumFractionDigits: 2 }) : "14,336.00"}`}
          subtitle="Day 10 food market recovery @ ₱14"
          icon={Coins}
          highlightColor="amber"
        />
        <StatCard
          title="Historical Fertility Mean"
          value={`${summary ? summary.avg_historical_fertility_rate : 89.4}%`}
          subtitle="Average viable embryo yield"
          icon={TrendingUp}
          highlightColor="green"
        />
      </div>

      {/* Tabs & Search Navigation Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
        {/* Tab Buttons */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg border border-slate-200 w-full sm:w-auto">
          <button
            onClick={() => setActiveTab('BATCHES')}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-md transition-colors cursor-pointer ${
              activeTab === 'BATCHES'
                ? 'bg-white text-[#800000] shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Batch Archives ({batches.length})
          </button>

          <button
            onClick={() => setActiveTab('SALVAGE')}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-md transition-colors cursor-pointer ${
              activeTab === 'SALVAGE'
                ? 'bg-white text-[#800000] shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Penoy Sales Ledger ({salvageRecords.length})
          </button>

          <button
            onClick={() => setActiveTab('SESSIONS')}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-md transition-colors cursor-pointer ${
              activeTab === 'SESSIONS'
                ? 'bg-white text-[#800000] shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Candling Shift Logs ({sessions.length})
          </button>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search records..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] shadow-xs"
          />
        </div>
      </div>

      {/* Tab 1: Batch Candling Archives Table */}
      {activeTab === 'BATCHES' && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Batch Identifier</th>
                  <th className="py-3 px-4">Duck Breed</th>
                  <th className="py-3 px-4">Set Date</th>
                  <th className="py-3 px-4">Initial Set</th>
                  <th className="py-3 px-4">Fertile</th>
                  <th className="py-3 px-4">Penoy (₱14)</th>
                  <th className="py-3 px-4">Dead</th>
                  <th className="py-3 px-4">Fertility %</th>
                  <th className="py-3 px-4">Hatch %</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredBatches.map((b) => (
                  <tr key={b.batch_id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-bold text-[#0F172A]">
                      <div className="flex items-center gap-2">
                        <Layers className="w-3.5 h-3.5 text-[#800000]" />
                        <span>{b.batch_code}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-700">{b.breed}</td>
                    <td className="py-3 px-4 text-slate-500 font-medium">{new Date(b.set_date).toLocaleDateString()}</td>
                    <td className="py-3 px-4 text-slate-800 font-bold">{b.initial_egg_count}</td>
                    <td className="py-3 px-4 text-emerald-700 font-bold">{b.fertile_count}</td>
                    <td className="py-3 px-4 text-amber-700 font-bold">{b.infertile_count}</td>
                    <td className="py-3 px-4 text-red-700 font-bold">{b.abnormal_count}</td>
                    <td className="py-3 px-4 font-bold text-slate-900">
                      {b.fertility_rate > 0 ? `${b.fertility_rate}%` : 'Pending'}
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-900">
                      {b.hatchability_rate > 0 ? `${b.hatchability_rate}%` : '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenCertificate(b)}
                          className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-bold rounded bg-maroon-50 hover:bg-maroon-100 text-[#800000] border border-maroon-200 transition-colors cursor-pointer"
                          title="View Official Certificate"
                        >
                          <Award className="w-3.5 h-3.5" />
                          <span>Certificate</span>
                        </button>
                        <a
                          href={apiClient.downloadCSVUrl(b.batch_id)}
                          download
                          className="p-1 rounded text-slate-400 hover:text-slate-700"
                          title="Download CSV"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Commercial Penoy Salvage Ledger */}
      {activeTab === 'SALVAGE' && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Record ID</th>
                  <th className="py-3 px-4">Batch ID</th>
                  <th className="py-3 px-4">Duck Breed</th>
                  <th className="py-3 px-4">Culled Date</th>
                  <th className="py-3 px-4">Salvaged Quantity</th>
                  <th className="py-3 px-4">Unit Rate</th>
                  <th className="py-3 px-4">Total Salvage Value</th>
                  <th className="py-3 px-4">Market / Buyer Destination</th>
                  <th className="py-3 px-4">Recorded By</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredSalvage.map((sal) => (
                  <tr key={sal.record_id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-600">{sal.record_id}</td>
                    <td className="py-3 px-4 font-bold text-[#0F172A]">{sal.batch_id}</td>
                    <td className="py-3 px-4 font-semibold text-slate-700">{sal.breed}</td>
                    <td className="py-3 px-4 text-slate-500 font-medium">
                      {new Date(sal.culled_date).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 font-extrabold text-amber-900 text-sm">{sal.egg_count} eggs</td>
                    <td className="py-3 px-4 font-mono text-slate-600">₱{sal.unit_price.toFixed(2)}</td>
                    <td className="py-3 px-4 font-extrabold text-emerald-800 text-sm">
                      ₱{sal.total_salvage_php.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-slate-800 font-medium">{sal.buyer_destination}</td>
                    <td className="py-3 px-4 text-slate-500">{sal.recorded_by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Candling Shift Logs */}
      {activeTab === 'SESSIONS' && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Session ID</th>
                  <th className="py-3 px-4">Batch ID</th>
                  <th className="py-3 px-4">Milestone</th>
                  <th className="py-3 px-4">Station ID</th>
                  <th className="py-3 px-4">Operator</th>
                  <th className="py-3 px-4">Total Candled</th>
                  <th className="py-3 px-4">Fertile</th>
                  <th className="py-3 px-4">Penoy</th>
                  <th className="py-3 px-4">Dead</th>
                  <th className="py-3 px-4">Speed</th>
                  <th className="py-3 px-4">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredSessions.map((sess) => (
                  <tr key={sess.session_id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-500">{sess.session_id}</td>
                    <td className="py-3 px-4 font-bold text-[#0F172A]">{sess.batch_id}</td>
                    <td className="py-3 px-4">
                      <span className="font-bold px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700 text-[11px]">
                        {sess.stage}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600">{sess.device_id}</td>
                    <td className="py-3 px-4 font-medium text-slate-800">{sess.operator_name}</td>
                    <td className="py-3 px-4 font-bold text-slate-900">{sess.total_scanned}</td>
                    <td className="py-3 px-4 font-bold text-emerald-700">{sess.fertile_count}</td>
                    <td className="py-3 px-4 font-bold text-amber-700">{sess.infertile_count}</td>
                    <td className="py-3 px-4 font-bold text-red-700">{sess.abnormal_count}</td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1 font-bold text-emerald-800 text-[11px] bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        <Zap className="w-3 h-3 text-emerald-600" />
                        120/min
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-500">{sess.avg_inference_ms.toFixed(1)} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Certificate Modal */}
      <CandlingCertificateModal
        isOpen={isCertificateOpen}
        onClose={() => setIsCertificateOpen(false)}
        batch={selectedBatch}
      />
    </div>
  );
};
