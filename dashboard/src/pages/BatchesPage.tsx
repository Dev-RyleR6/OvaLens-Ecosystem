import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Filter,
  Download,
  FileText,
  Calendar,
  Layers,
  Sparkles,
  Info,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import { apiClient } from '../api/client';
import { BatchSummary, DuckBreed, BatchStage } from '../types';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';

export const BatchesPage: React.FC = () => {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [breedFilter, setBreedFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);

  // New Batch Form State
  const [batchCode, setBatchCode] = useState('');
  const [breed, setBreed] = useState<DuckBreed>('KAYUMANGGI');
  const [incubatorId, setIncubatorId] = useState('INCUBATOR-A1');
  const [initialCount, setInitialCount] = useState(500);
  const [notes, setNotes] = useState('');

  const fetchBatches = async () => {
    const data = await apiClient.getBatches();
    setBatches(data);
  };

  useEffect(() => {
    fetchBatches();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await apiClient.createBatch({
      batch_code: batchCode,
      breed,
      incubator_id: incubatorId,
      initial_egg_count: Number(initialCount),
      notes,
    });
    setIsCreateOpen(false);
    setBatchCode('');
    setNotes('');
    fetchBatches();
  };

  const filteredBatches = batches.filter((b) => {
    const matchSearch = b.batch_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        b.incubator_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchBreed = breedFilter === 'ALL' || b.breed === breedFilter;
    const matchStatus = statusFilter === 'ALL' || b.status === statusFilter;
    return matchSearch && matchBreed && matchStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-obsidian-900 border border-obsidian-700/80 p-4 rounded-lg shadow-xl">
        <div>
          <h2 className="text-lg font-display font-black tracking-wide text-white uppercase flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
            Incubation Batch Lifecycle Ledger
          </h2>
          <p className="text-xs font-mono text-slate-400">
            28-day duck egg developmental schedules, fertility rates, and automated audit reports
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-[#800000] hover:bg-[#991B1B] text-white rounded text-xs font-display font-bold uppercase tracking-wider shadow-md transition-all border border-[#991B1B]"
        >
          <Plus className="w-4 h-4" />
          Set New Incubation Batch
        </button>
      </div>

      {/* Filter / Search Bar */}
      <div className="bg-obsidian-900 border border-obsidian-700/80 rounded-lg p-3 flex flex-col md:flex-row items-center justify-between gap-3 text-xs font-mono">
        <div className="relative w-full md:w-72">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter batch code or incubator..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-obsidian-950 border border-obsidian-700 rounded pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-[#800000]"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Filter className="w-3.5 h-3.5" /> Breed:
          </div>
          <select
            value={breedFilter}
            onChange={(e) => setBreedFilter(e.target.value)}
            className="bg-obsidian-950 border border-obsidian-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#800000]"
          >
            <option value="ALL">All Breeds</option>
            <option value="KAYUMANGGI">Kayumanggi</option>
            <option value="ITIM">Itim (Native)</option>
            <option value="KHAKI">Khaki Campbell</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-obsidian-950 border border-obsidian-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#800000]"
          >
            <option value="ALL">All Statuses</option>
            <option value="INCUBATING">Incubating</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>
      </div>

      {/* High-Density Batch Table */}
      <div className="panel-scada p-0 overflow-hidden">
        <div className="panel-scada-header">
          <span>Active & Completed Incubation Cohorts</span>
          <span className="text-[10px] text-slate-400 font-mono">Found: {filteredBatches.length} batches</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-obsidian-950 text-slate-400 uppercase text-[10px] font-bold border-b border-obsidian-750">
              <tr>
                <th className="py-3 px-4">Batch Code</th>
                <th className="py-3 px-4">Duck Breed</th>
                <th className="py-3 px-4">Incubator Unit</th>
                <th className="py-3 px-4">Initial Set</th>
                <th className="py-3 px-4">Stage / Milestones</th>
                <th className="py-3 px-4">Fertility Rate</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-obsidian-800 text-slate-300">
              {filteredBatches.map((b) => (
                <tr key={b.batch_id} className="hover:bg-obsidian-800/50 transition-colors">
                  <td className="py-3 px-4">
                    <button
                      onClick={() => setSelectedBatch(b)}
                      className="font-bold text-amber-400 hover:underline flex items-center gap-1.5"
                    >
                      <Layers className="w-3.5 h-3.5 text-amber-400" />
                      {b.batch_code}
                    </button>
                    <span className="text-[10px] text-slate-500 block">Set: {new Date(b.set_date).toLocaleDateString()}</span>
                  </td>
                  <td className="py-3 px-4 font-sans font-bold text-slate-200">{b.breed}</td>
                  <td className="py-3 px-4 text-slate-400">{b.incubator_id}</td>
                  <td className="py-3 px-4 font-bold text-slate-100">{b.initial_egg_count} eggs</td>
                  <td className="py-3 px-4 min-w-[190px]">
                    <Badge type="stage" value={b.current_stage} size="sm" />
                    <span className="text-[10px] text-slate-500 block mt-1">Hatch: {new Date(b.target_hatch_date).toLocaleDateString()}</span>
                  </td>
                  <td className="py-3 px-4 font-bold text-emerald-400">
                    {b.fertility_rate > 0 ? `${b.fertility_rate}%` : 'Pending Day 10'}
                  </td>
                  <td className="py-3 px-4">
                    <Badge type="status" value={b.status} size="sm" />
                  </td>
                  <td className="py-3 px-4 text-right space-x-1.5">
                    <button
                      onClick={() => setSelectedBatch(b)}
                      className="p-1.5 rounded bg-obsidian-800 hover:bg-obsidian-700 text-slate-300 transition-colors inline-block"
                      title="Inspect Batch"
                    >
                      <Info className="w-3.5 h-3.5" />
                    </button>
                    <a
                      href={apiClient.downloadCSVUrl(b.batch_id)}
                      download
                      className="p-1.5 rounded bg-obsidian-800 hover:bg-obsidian-700 text-slate-300 transition-colors inline-block"
                      title="Export CSV Dataset"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                    <a
                      href={apiClient.downloadPDFUrl(b.batch_id)}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 rounded bg-[#800000]/40 hover:bg-[#800000] text-amber-300 transition-colors inline-block"
                      title="Official PDF Audit Certificate"
                    >
                      <FileText className="w-3.5 h-3.5" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Batch Modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Set New Incubation Batch">
        <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs font-mono">
          <div>
            <label className="block text-slate-300 font-bold mb-1">Batch Code Identifier</label>
            <input
              type="text"
              required
              placeholder="e.g. BATCH-2026-08-KAY-03"
              value={batchCode}
              onChange={(e) => setBatchCode(e.target.value)}
              className="w-full bg-obsidian-950 border border-obsidian-700 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-300 font-bold mb-1">Duck Breed</label>
              <select
                value={breed}
                onChange={(e) => setBreed(e.target.value as DuckBreed)}
                className="w-full bg-obsidian-950 border border-obsidian-700 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
              >
                <option value="KAYUMANGGI">Kayumanggi</option>
                <option value="ITIM">Itim (Native)</option>
                <option value="KHAKI">Khaki Campbell</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-300 font-bold mb-1">Incubator Unit</label>
              <input
                type="text"
                required
                value={incubatorId}
                onChange={(e) => setIncubatorId(e.target.value)}
                className="w-full bg-obsidian-950 border border-obsidian-700 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-300 font-bold mb-1">Initial Egg Set Count</label>
            <input
              type="number"
              min="1"
              required
              value={initialCount}
              onChange={(e) => setInitialCount(Number(e.target.value))}
              className="w-full bg-obsidian-950 border border-obsidian-700 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div>
            <label className="block text-slate-300 font-bold mb-1">Flock Source & Operational Notes</label>
            <textarea
              rows={3}
              placeholder="Flock source, breeder baseline, thermal incubator calibration..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-obsidian-950 border border-obsidian-700 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-obsidian-700">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-4 py-2 rounded bg-obsidian-800 hover:bg-obsidian-700 text-slate-300 font-bold transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded bg-[#800000] hover:bg-[#991B1B] text-white font-bold transition-colors shadow-md"
            >
              Initialize & Start 28-Day Incubation
            </button>
          </div>
        </form>
      </Modal>

      {/* Batch Details Modal */}
      {selectedBatch && (
        <Modal
          isOpen={Boolean(selectedBatch)}
          onClose={() => setSelectedBatch(null)}
          title={`Batch Details — ${selectedBatch.batch_code}`}
          maxWidth="max-w-2xl"
        >
          <div className="space-y-4 text-xs font-mono">
            {/* Timeline */}
            <div className="p-3.5 rounded bg-obsidian-950 border border-obsidian-800">
              <h4 className="font-bold text-slate-200 mb-2">28-Day Incubation Progress</h4>
              <BatchProgressTimeline currentStage={selectedBatch.current_stage} setDate={selectedBatch.set_date} />
            </div>

            {/* Info Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="p-2.5 bg-obsidian-950 rounded border border-obsidian-800">
                <span className="text-[10px] text-slate-500 block">BREED</span>
                <span className="font-bold text-slate-200 text-sm mt-0.5 block">{selectedBatch.breed}</span>
              </div>
              <div className="p-2.5 bg-obsidian-950 rounded border border-obsidian-800">
                <span className="text-[10px] text-slate-500 block">INCUBATOR UNIT</span>
                <span className="font-bold text-slate-200 text-sm mt-0.5 block">{selectedBatch.incubator_id}</span>
              </div>
              <div className="p-2.5 bg-obsidian-950 rounded border border-obsidian-800">
                <span className="text-[10px] text-slate-500 block">INITIAL SET</span>
                <span className="font-bold text-slate-200 text-sm mt-0.5 block">{selectedBatch.initial_egg_count} eggs</span>
              </div>
              <div className="p-2.5 bg-obsidian-950 rounded border border-obsidian-800">
                <span className="text-[10px] text-slate-500 block">FERTILITY RATE</span>
                <span className="font-bold text-emerald-400 text-sm mt-0.5 block">{selectedBatch.fertility_rate}%</span>
              </div>
            </div>

            {/* Candling Counts */}
            <div className="p-3 bg-obsidian-950 rounded border border-obsidian-800 space-y-1.5">
              <h4 className="font-bold text-slate-200 text-[11px]">Candling Classification Breakdown</h4>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 bg-emerald-950/60 rounded border border-emerald-800/40">
                  <span className="text-[9px] text-emerald-400 font-bold block">FERTILE (ACCEPT)</span>
                  <span className="text-base font-black text-white">{selectedBatch.fertile_count}</span>
                </div>
                <div className="p-2 bg-amber-950/60 rounded border border-amber-800/40">
                  <span className="text-[9px] text-amber-400 font-bold block">INFERTILE (PENOY)</span>
                  <span className="text-base font-black text-white">{selectedBatch.infertile_count}</span>
                </div>
                <div className="p-2 bg-rose-950/60 rounded border border-rose-800/40">
                  <span className="text-[9px] text-rose-400 font-bold block">ABNORMAL (DEAD)</span>
                  <span className="text-base font-black text-white">{selectedBatch.abnormal_count}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-obsidian-800">
              <a
                href={apiClient.downloadCSVUrl(selectedBatch.batch_id)}
                download
                className="px-3.5 py-1.5 rounded bg-obsidian-800 hover:bg-obsidian-700 text-slate-200 font-bold border border-obsidian-700 flex items-center gap-1.5 transition-colors"
              >
                <Download className="w-3.5 h-3.5" /> Export CSV
              </a>
              <a
                href={apiClient.downloadPDFUrl(selectedBatch.batch_id)}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-1.5 rounded bg-[#800000] hover:bg-[#991B1B] text-white font-bold flex items-center gap-1.5 transition-colors shadow-md"
              >
                <FileText className="w-3.5 h-3.5" /> Official PDF Audit Certificate
              </a>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
