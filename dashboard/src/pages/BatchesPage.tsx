import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Download,
  FileText,
  Layers,
  ChevronRight,
  FastForward,
  Clock,
  User,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { BatchSummary, DuckBreed, BatchStage, CandlingSession } from '../types';
import { Badge } from '../components/Badge';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { Dialog } from '../components/ui/dialog';
import { Sheet } from '../components/ui/sheet';

export const BatchesPage: React.FC = () => {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [breedFilter, setBreedFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);
  const [batchSessions, setBatchSessions] = useState<CandlingSession[]>([]);
  const [isAdvancing, setIsAdvancing] = useState(false);

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

  const handleSelectBatch = async (b: BatchSummary) => {
    setSelectedBatch(b);
    const sessions = await apiClient.getSessions(b.batch_id);
    setBatchSessions(sessions);
  };

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

  const getNextStage = (stage: BatchStage): BatchStage | null => {
    switch (stage) {
      case 'SETTING': return 'DAY_10';
      case 'DAY_10': return 'DAY_18';
      case 'DAY_18': return 'DAY_25';
      case 'DAY_25': return 'HATCHED';
      case 'HATCHED': return 'COMPLETED';
      default: return null;
    }
  };

  const handleAdvanceStage = async () => {
    if (!selectedBatch) return;
    const next = getNextStage(selectedBatch.current_stage);
    if (!next) return;

    setIsAdvancing(true);
    try {
      const updated = await apiClient.advanceBatchStage(selectedBatch.batch_id, next);
      setSelectedBatch({ ...updated });
      fetchBatches();
    } finally {
      setIsAdvancing(false);
    }
  };

  const filteredBatches = batches.filter((b) => {
    const matchSearch = b.batch_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        b.incubator_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchBreed = breedFilter === 'ALL' || b.breed === breedFilter;
    const matchStatus = statusFilter === 'ALL' || b.status === statusFilter;
    return matchSearch && matchBreed && matchStatus;
  });

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Incubation Batches
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage 28-day incubation cohorts, monitor operator candling sessions, and export official audit reports.
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Set New Incubation Batch</span>
        </button>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search batch code or incubator unit..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#800000] shadow-xs"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          <select
            value={breedFilter}
            onChange={(e) => setBreedFilter(e.target.value)}
            className="h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Duck Breeds</option>
            <option value="KAYUMANGGI">Kayumanggi</option>
            <option value="ITIM">Itim (Native)</option>
            <option value="KHAKI">Khaki Campbell</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Statuses</option>
            <option value="INCUBATING">Incubating</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>
      </div>

      {/* Batches Table Card */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Batch Code</th>
                <th className="py-3 px-4">Duck Breed</th>
                <th className="py-3 px-4">Incubator</th>
                <th className="py-3 px-4">Initial Set</th>
                <th className="py-3 px-4">Current Stage</th>
                <th className="py-3 px-4">Fertility Rate</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredBatches.map((b) => (
                <tr
                  key={b.batch_id}
                  className="hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => handleSelectBatch(b)}
                >
                  <td className="py-3 px-4 font-bold text-[#0F172A]">
                    <div className="flex items-center gap-2">
                      <Layers className="w-3.5 h-3.5 text-[#800000]" />
                      <span>{b.batch_code}</span>
                    </div>
                    <span className="text-[11px] text-slate-500 font-normal block mt-0.5">
                      Set: {new Date(b.set_date).toLocaleDateString()}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-700">{b.breed}</td>
                  <td className="py-3 px-4 text-slate-600 font-medium">{b.incubator_id}</td>
                  <td className="py-3 px-4 text-slate-800 font-bold">{b.initial_egg_count} eggs</td>
                  <td className="py-3 px-4">
                    <Badge type="stage" value={b.current_stage} />
                  </td>
                  <td className="py-3 px-4 font-bold text-slate-900">
                    {b.fertility_rate > 0 ? `${b.fertility_rate}%` : 'Pending Day 10'}
                  </td>
                  <td className="py-3 px-4">
                    <Badge type="status" value={b.status} />
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                      <a
                        href={apiClient.downloadCSVUrl(b.batch_id)}
                        download
                        className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 hover:text-slate-900 transition-colors inline-block"
                        title="Export CSV Data"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                      <a
                        href={apiClient.downloadPDFUrl(b.batch_id)}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 rounded-md hover:bg-slate-100 text-[#800000] hover:text-[#5C0000] transition-colors inline-block"
                        title="Download PDF Audit Certificate"
                      >
                        <FileText className="w-4 h-4" />
                      </a>
                      <button
                        className="p-1.5 text-slate-400 hover:text-slate-700 cursor-pointer"
                        onClick={() => handleSelectBatch(b)}
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* New Batch Modal Dialog */}
      <Dialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Set New Incubation Batch"
        description="Initialize a new 28-day duck egg incubation cohort in the hatchery."
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4 text-sm">
          <div className="space-y-1.5">
            <label className="font-semibold text-xs text-slate-700">Batch Code / Identifier</label>
            <input
              required
              placeholder="e.g. BATCH-2026-08-KAY-03"
              value={batchCode}
              onChange={(e) => setBatchCode(e.target.value)}
              className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="font-semibold text-xs text-slate-700">Duck Breed</label>
              <select
                value={breed}
                onChange={(e) => setBreed(e.target.value as DuckBreed)}
                className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:border-[#800000]"
              >
                <option value="KAYUMANGGI">Kayumanggi</option>
                <option value="ITIM">Itim (Native)</option>
                <option value="KHAKI">Khaki Campbell</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="font-semibold text-xs text-slate-700">Incubator Unit</label>
              <input
                required
                value={incubatorId}
                onChange={(e) => setIncubatorId(e.target.value)}
                className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="font-semibold text-xs text-slate-700">Initial Egg Count</label>
            <input
              type="number"
              min="1"
              required
              value={initialCount}
              onChange={(e) => setInitialCount(Number(e.target.value))}
              className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-semibold text-xs text-slate-700">Source Notes & Farm Origin</label>
            <textarea
              rows={3}
              placeholder="Breeder farm source, flock age, initial candling condition..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-bold text-white bg-[#800000] hover:bg-[#6B0000] rounded-lg shadow-xs cursor-pointer"
            >
              Initialize Cohort
            </button>
          </div>
        </form>
      </Dialog>

      {/* Batch Details Drawer (Sheet) */}
      <Sheet
        isOpen={Boolean(selectedBatch)}
        onClose={() => setSelectedBatch(null)}
        title={selectedBatch ? `Batch: ${selectedBatch.batch_code}` : ''}
        description="Incubation progress, operator candling shifts, and yield metrics"
      >
        {selectedBatch && (
          <div className="space-y-5 text-xs">
            {/* Timeline */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-slate-800">28-Day Milestone Progress</span>
                {getNextStage(selectedBatch.current_stage) && (
                  <button
                    onClick={handleAdvanceStage}
                    disabled={isAdvancing}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#800000] hover:bg-[#6B0000] text-white text-[11px] font-bold shadow-xs cursor-pointer disabled:opacity-50"
                  >
                    <FastForward className="w-3 h-3" />
                    <span>Advance to {getNextStage(selectedBatch.current_stage)}</span>
                  </button>
                )}
              </div>
              <BatchProgressTimeline
                currentStage={selectedBatch.current_stage}
                setDate={selectedBatch.set_date}
              />
            </div>

            {/* Core Stats */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-semibold uppercase block">Breed</span>
                <span className="text-sm font-bold text-[#0F172A] mt-0.5 block">{selectedBatch.breed}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-semibold uppercase block">Incubator Unit</span>
                <span className="text-sm font-bold text-[#0F172A] mt-0.5 block">{selectedBatch.incubator_id}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-semibold uppercase block">Initial Egg Set</span>
                <span className="text-sm font-bold text-[#0F172A] mt-0.5 block">{selectedBatch.initial_egg_count} eggs</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-semibold uppercase block">Fertility Rate</span>
                <span className="text-sm font-bold text-emerald-700 mt-0.5 block">{selectedBatch.fertility_rate}%</span>
              </div>
            </div>

            {/* Classification Yield Breakdown */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <h4 className="font-bold text-slate-800">Candling Yield Summary</h4>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 bg-emerald-50 rounded-lg border border-emerald-200">
                  <span className="text-[10px] text-emerald-700 font-semibold block">Fertile</span>
                  <span className="text-base font-extrabold text-emerald-900">{selectedBatch.fertile_count}</span>
                </div>
                <div className="p-2 bg-amber-50 rounded-lg border border-amber-200">
                  <span className="text-[10px] text-amber-700 font-semibold block">Penoy</span>
                  <span className="text-base font-extrabold text-amber-900">{selectedBatch.infertile_count}</span>
                </div>
                <div className="p-2 bg-red-50 rounded-lg border border-red-200">
                  <span className="text-[10px] text-red-700 font-semibold block">Dead</span>
                  <span className="text-base font-extrabold text-red-900">{selectedBatch.abnormal_count}</span>
                </div>
              </div>
            </div>

            {/* Candling Sessions Shift Log */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-slate-800 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-600" />
                  <span>Operator Candling Sessions</span>
                </h4>
                <span className="text-[10px] font-semibold text-slate-500">{batchSessions.length} recorded</span>
              </div>

              {batchSessions.length > 0 ? (
                <div className="space-y-1.5">
                  {batchSessions.map((s) => (
                    <div key={s.session_id} className="p-2 bg-white rounded-lg border border-slate-200 space-y-1">
                      <div className="flex items-center justify-between font-medium">
                        <span className="font-bold text-[#0F172A]">{s.stage} Candling</span>
                        <span className="text-[11px] text-slate-500 font-mono">{s.device_id}</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-600">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3 text-slate-400" />
                          {s.operator_name}
                        </span>
                        <span className="font-bold text-emerald-700">
                          {s.fertile_count} / {s.total_scanned} Fertile ({s.avg_inference_ms.toFixed(1)}ms)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-slate-400 italic">No candling sessions logged yet for this batch.</p>
              )}
            </div>

            {/* Official Report Exports */}
            <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-200">
              <a
                href={apiClient.downloadCSVUrl(selectedBatch.batch_id)}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </a>
              <a
                href={apiClient.downloadPDFUrl(selectedBatch.batch_id)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white transition-colors"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Download Official PDF Certificate</span>
              </a>
            </div>
          </div>
        )}
      </Sheet>
    </div>
  );
};
