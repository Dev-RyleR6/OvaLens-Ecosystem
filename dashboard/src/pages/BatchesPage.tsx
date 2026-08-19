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
  Info
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
    // Reset
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Incubation Batch Management</h2>
          <p className="text-xs text-slate-400">Track 28-day duck egg developmental lifecycles and milestones</p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#800000] hover:bg-[#991B1B] text-white rounded-lg text-sm font-semibold shadow-md transition-all border border-[#991B1B]"
        >
          <Plus className="w-4 h-4" />
          Set New Batch
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-3 shadow-md">
        {/* Search */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search batch code or incubator..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900/80 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#800000]"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5" /> Breed:
          </div>
          <select
            value={breedFilter}
            onChange={(e) => setBreedFilter(e.target.value)}
            className="bg-slate-900/80 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#800000]"
          >
            <option value="ALL">All Breeds</option>
            <option value="KAYUMANGGI">Kayumanggi</option>
            <option value="ITIM">Itim (Native)</option>
            <option value="KHAKI">Khaki Campbell</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900/80 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#800000]"
          >
            <option value="ALL">All Statuses</option>
            <option value="INCUBATING">Incubating</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>
      </div>

      {/* Batches Table Grid */}
      <div className="bg-[#1E293B] border border-slate-800 rounded-xl shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Batch Code</th>
                <th className="py-3.5 px-4">Breed</th>
                <th className="py-3.5 px-4">Incubator</th>
                <th className="py-3.5 px-4">Initial Set</th>
                <th className="py-3.5 px-4">Stage / Timeline</th>
                <th className="py-3.5 px-4">Fertility %</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 font-medium text-slate-300">
              {filteredBatches.map((b) => (
                <tr key={b.batch_id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3.5 px-4">
                    <button
                      onClick={() => setSelectedBatch(b)}
                      className="font-bold text-amber-400 hover:underline flex items-center gap-1.5"
                    >
                      <Layers className="w-3.5 h-3.5 text-amber-400" />
                      {b.batch_code}
                    </button>
                    <span className="text-[10px] text-slate-500 block">Set: {new Date(b.set_date).toLocaleDateString()}</span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-200">{b.breed}</td>
                  <td className="py-3.5 px-4 text-slate-400">{b.incubator_id}</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-slate-200">{b.initial_egg_count} eggs</td>
                  <td className="py-3.5 px-4 min-w-[200px]">
                    <Badge type="stage" value={b.current_stage} />
                    <span className="text-[10px] text-slate-400 block mt-1">Hatch: {new Date(b.target_hatch_date).toLocaleDateString()}</span>
                  </td>
                  <td className="py-3.5 px-4 font-bold text-emerald-400">
                    {b.fertility_rate > 0 ? `${b.fertility_rate}%` : 'Pending Day 10'}
                  </td>
                  <td className="py-3.5 px-4">
                    <Badge type="status" value={b.status} />
                  </td>
                  <td className="py-3.5 px-4 text-right space-x-1.5">
                    <button
                      onClick={() => setSelectedBatch(b)}
                      className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors inline-block"
                      title="View Details"
                    >
                      <Info className="w-4 h-4" />
                    </button>
                    <a
                      href={apiClient.downloadCSVUrl(b.batch_id)}
                      download
                      className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors inline-block"
                      title="Download CSV"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                    <a
                      href={apiClient.downloadPDFUrl(b.batch_id)}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 rounded bg-[#800000]/40 hover:bg-[#800000] text-amber-300 transition-colors inline-block"
                      title="Download PDF Audit Report"
                    >
                      <FileText className="w-4 h-4" />
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
        <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 font-semibold mb-1">Batch Code Identifier</label>
            <input
              type="text"
              required
              placeholder="e.g. BATCH-2026-08-KAY-03"
              value={batchCode}
              onChange={(e) => setBatchCode(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Duck Breed</label>
              <select
                value={breed}
                onChange={(e) => setBreed(e.target.value as DuckBreed)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
              >
                <option value="KAYUMANGGI">Kayumanggi</option>
                <option value="ITIM">Itim (Native)</option>
                <option value="KHAKI">Khaki Campbell</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Incubator Unit</label>
              <input
                type="text"
                required
                value={incubatorId}
                onChange={(e) => setIncubatorId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">Initial Egg Set Count</label>
            <input
              type="number"
              min="1"
              required
              value={initialCount}
              onChange={(e) => setInitialCount(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">Breeder Source & Notes</label>
            <textarea
              rows={3}
              placeholder="Flock source, temperature baseline, or operational notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-700">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-lg bg-[#800000] hover:bg-[#991B1B] text-white font-bold transition-colors shadow-md"
            >
              Save & Start Incubation
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
          <div className="space-y-5 text-xs">
            {/* Timeline */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-700">
              <h4 className="font-bold text-slate-200 mb-2">28-Day Duck Egg Incubation Lifecycle</h4>
              <BatchProgressTimeline currentStage={selectedBatch.current_stage} setDate={selectedBatch.set_date} />
            </div>

            {/* Info Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Breed</p>
                <p className="font-bold text-slate-200 text-sm mt-0.5">{selectedBatch.breed}</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Incubator</p>
                <p className="font-bold text-slate-200 text-sm mt-0.5">{selectedBatch.incubator_id}</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Initial Set Count</p>
                <p className="font-bold text-slate-200 text-sm mt-0.5">{selectedBatch.initial_egg_count} eggs</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Fertility Rate</p>
                <p className="font-bold text-emerald-400 text-sm mt-0.5">{selectedBatch.fertility_rate}%</p>
              </div>
            </div>

            {/* Candling Counts Breakdown */}
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-200">Candling Breakdown</h4>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 bg-emerald-950/60 rounded border border-emerald-800/40">
                  <span className="text-[10px] text-emerald-400 font-bold block">FERTILE (ACCEPT)</span>
                  <span className="text-base font-black text-white">{selectedBatch.fertile_count}</span>
                </div>
                <div className="p-2 bg-amber-950/60 rounded border border-amber-800/40">
                  <span className="text-[10px] text-amber-400 font-bold block">INFERTILE (PENOY)</span>
                  <span className="text-base font-black text-white">{selectedBatch.infertile_count}</span>
                </div>
                <div className="p-2 bg-red-950/60 rounded border border-red-800/40">
                  <span className="text-[10px] text-red-400 font-bold block">ABNORMAL (DEAD)</span>
                  <span className="text-base font-black text-white">{selectedBatch.abnormal_count}</span>
                </div>
              </div>
            </div>

            {/* Export Actions */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <a
                href={apiClient.downloadCSVUrl(selectedBatch.batch_id)}
                download
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold border border-slate-700 flex items-center gap-1.5 transition-colors"
              >
                <Download className="w-4 h-4" /> Export CSV
              </a>
              <a
                href={apiClient.downloadPDFUrl(selectedBatch.batch_id)}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 rounded-lg bg-[#800000] hover:bg-[#991B1B] text-white font-bold flex items-center gap-1.5 transition-colors shadow-md"
              >
                <FileText className="w-4 h-4" /> Official PDF Report
              </a>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
