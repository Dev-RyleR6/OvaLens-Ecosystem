import React, { useState, useEffect, useMemo } from 'react';
import {
  Plus,
  Search,
  Download,
  Layers,
  ChevronRight,
  ChevronLeft,
  FastForward,
  Clock,
  User,
  Zap,
  Award,
  List,
  LayoutGrid,
  ArrowUpDown,
  CheckSquare,
  Square,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { BatchSummary, DuckBreed, BatchStage, CandlingSession } from '../types';
import { Badge } from '../components/Badge';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { Dialog } from '../components/ui/dialog';
import { Sheet } from '../components/ui/sheet';
import { CandlingCertificateModal } from '../components/CandlingCertificateModal';
import { BatchAnalyticsModal } from '../components/BatchAnalyticsModal';
import { FinalizeHatchModal } from '../components/FinalizeHatchModal';
import { Activity, Trash2, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

type ViewMode = 'TABLE' | 'GRID';
type SortField = 'batch_code' | 'set_date' | 'initial_egg_count' | 'fertility_rate';
type SortOrder = 'asc' | 'desc';

export const BatchesPage: React.FC = () => {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('TABLE');
  const [searchQuery, setSearchQuery] = useState('');
  const [breedFilter, setBreedFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [stageFilter, setStageFilter] = useState<string>('ALL');
  
  // Sorting & Pagination
  const [sortField, setSortField] = useState<SortField>('set_date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [selectedBatchIds, setSelectedBatchIds] = useState<string[]>([]);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);
  const [batchSessions, setBatchSessions] = useState<CandlingSession[]>([]);
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [isCertificateOpen, setIsCertificateOpen] = useState(false);
  const [certificateBatch, setCertificateBatch] = useState<BatchSummary | null>(null);

  // New Analytics & Finalize Modals
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState(false);
  const [analyticsBatchId, setAnalyticsBatchId] = useState<string | null>(null);
  const [isFinalizeOpen, setIsFinalizeOpen] = useState(false);
  const [finalizeBatch, setFinalizeBatch] = useState<BatchSummary | null>(null);
  const [milestoneMsg, setMilestoneMsg] = useState<string | null>(null);
  const [isCheckingMilestones, setIsCheckingMilestones] = useState(false);

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

  const handleOpenCertificate = (b: BatchSummary, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setCertificateBatch(b);
    setIsCertificateOpen(true);
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

  const handleOpenAnalytics = (b: BatchSummary, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setAnalyticsBatchId(b.batch_id);
    setIsAnalyticsOpen(true);
  };

  const handleOpenFinalize = (b: BatchSummary, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setFinalizeBatch(b);
    setIsFinalizeOpen(true);
  };

  const handleCheckMilestones = async () => {
    setIsCheckingMilestones(true);
    try {
      const res = await apiClient.checkBatchMilestones();
      setMilestoneMsg(`Evaluated ${res.evaluated_batches} active cohorts. ${res.updated_batches} milestone alerts updated.`);
      fetchBatches();
      setTimeout(() => setMilestoneMsg(null), 4000);
    } finally {
      setIsCheckingMilestones(false);
    }
  };

  const handleDeleteBatch = async (batchId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete batch '${batchId}'?`)) return;
    await apiClient.deleteBatch(batchId);
    if (selectedBatch?.batch_id === batchId) setSelectedBatch(null);
    fetchBatches();
  };

  // Filtered & Sorted Batches
  const processedBatches = useMemo(() => {
    let result = [...batches];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (b) =>
          b.batch_code.toLowerCase().includes(q) ||
          b.incubator_id.toLowerCase().includes(q) ||
          b.breed.toLowerCase().includes(q)
      );
    }

    if (breedFilter !== 'ALL') {
      result = result.filter((b) => b.breed === breedFilter);
    }

    if (statusFilter !== 'ALL') {
      result = result.filter((b) => b.status === statusFilter);
    }

    if (stageFilter !== 'ALL') {
      result = result.filter((b) => b.current_stage === stageFilter);
    }

    // Sort
    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (typeof aVal === 'string') {
        return sortOrder === 'asc'
          ? (aVal as string).localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal as string);
      }
      return sortOrder === 'asc'
        ? ((aVal as number) || 0) - ((bVal as number) || 0)
        : ((bVal as number) || 0) - ((aVal as number) || 0);
    });

    return result;
  }, [batches, searchQuery, breedFilter, statusFilter, stageFilter, sortField, sortOrder]);

  // Paginated Batches
  const paginatedBatches = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return processedBatches.slice(start, start + rowsPerPage);
  }, [processedBatches, currentPage, rowsPerPage]);

  const totalPages = Math.ceil(processedBatches.length / rowsPerPage) || 1;

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const toggleSelectAll = () => {
    if (selectedBatchIds.length === paginatedBatches.length) {
      setSelectedBatchIds([]);
    } else {
      setSelectedBatchIds(paginatedBatches.map((b) => b.batch_id));
    }
  };

  const toggleSelectBatch = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedBatchIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Incubation Batches & Candling Sessions
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Track 28-day duck egg incubation batches, automated stage milestones, operator candling throughput, and official quality certificates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCheckMilestones}
            disabled={isCheckingMilestones}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
            title="Evaluate elapsed incubation days and flag due candling/transfer milestones"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isCheckingMilestones ? 'animate-spin text-[#800000]' : 'text-slate-500'}`} />
            <span>Check Milestones</span>
          </button>

          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Batch</span>
          </button>
        </div>
      </div>

      {milestoneMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{milestoneMsg}</span>
        </div>
      )}

      {/* Enterprise Filter Toolbar */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search batch code or incubator unit..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#800000] shadow-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
              <button
                onClick={() => setViewMode('TABLE')}
                className={`p-1.5 rounded text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors ${
                  viewMode === 'TABLE' ? 'bg-white text-[#800000] shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
                title="Table View"
              >
                <List className="w-3.5 h-3.5" />
                <span>Table</span>
              </button>
              <button
                onClick={() => setViewMode('GRID')}
                className={`p-1.5 rounded text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors ${
                  viewMode === 'GRID' ? 'bg-white text-[#800000] shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
                title="Grid Cards View"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span>Grid</span>
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          <select
            value={breedFilter}
            onChange={(e) => {
              setBreedFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Duck Breeds</option>
            <option value="KAYUMANGGI">Kayumanggi</option>
            <option value="ITIM">Itim (Native)</option>
            <option value="KHAKI">Khaki Campbell</option>
          </select>

          <select
            value={stageFilter}
            onChange={(e) => {
              setStageFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Incubation Stages</option>
            <option value="SETTING">Setting (Day 0-9)</option>
            <option value="DAY_10">Day 10 (1st Candling)</option>
            <option value="DAY_18">Day 18 (2nd Candling)</option>
            <option value="DAY_25">Day 25 (Pipping)</option>
            <option value="COMPLETED">Completed</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Statuses</option>
            <option value="INCUBATING">Incubating</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>
      </div>

      {/* View Mode: Table vs Grid */}
      {viewMode === 'TABLE' ? (
        <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4 w-10 text-center">
                    <button onClick={toggleSelectAll} className="text-slate-400 hover:text-slate-700 cursor-pointer">
                      {selectedBatchIds.length === paginatedBatches.length && paginatedBatches.length > 0 ? (
                        <CheckSquare className="w-4 h-4 text-[#800000]" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </button>
                  </th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => toggleSort('batch_code')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Batch Code</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Duck Breed</th>
                  <th className="py-3 px-4">Incubator</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => toggleSort('initial_egg_count')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Initial Set</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Current Stage</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => toggleSort('fertility_rate')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Fertility Rate</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedBatches.map((b) => {
                  const isSelected = selectedBatchIds.includes(b.batch_id);
                  return (
                    <tr
                      key={b.batch_id}
                      className={`hover:bg-slate-50 transition-colors cursor-pointer ${
                        isSelected ? 'bg-maroon-50/30' : ''
                      }`}
                      onClick={() => handleSelectBatch(b)}
                    >
                      <td className="py-3 px-4 text-center" onClick={(e) => toggleSelectBatch(b.batch_id, e)}>
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-[#800000]" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-300 hover:text-slate-500" />
                        )}
                      </td>
                      <td className="py-3 px-4 font-bold text-[#0F172A]">
                        <div className="flex items-center gap-2">
                          <Layers className="w-3.5 h-3.5 text-[#800000]" />
                          <span>{b.batch_code}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[11px] text-slate-500 font-normal">
                            Set: {new Date(b.set_date).toLocaleDateString()}
                          </span>
                          {b.elapsed_days !== undefined && (
                            <span className="text-[10px] text-slate-400 font-semibold">
                              (Day {b.elapsed_days})
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-700">{b.breed}</td>
                      <td className="py-3 px-4 text-slate-600 font-medium">{b.incubator_id}</td>
                      <td className="py-3 px-4 text-slate-800 font-bold">{b.initial_egg_count} eggs</td>
                      <td className="py-3 px-4">
                        <div className="space-y-1">
                          <Badge type="stage" value={b.current_stage} />
                          {b.milestone_alert && (
                            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-900 border border-amber-300 animate-pulse">
                              {b.milestone_alert.split(':')[0]}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-900">
                        {b.fertility_rate > 0 ? `${b.fertility_rate}%` : 'Pending Day 10'}
                      </td>
                      <td className="py-3 px-4">
                        <Badge type="status" value={b.status} />
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={(e) => handleOpenAnalytics(b, e)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-bold rounded bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 transition-colors cursor-pointer"
                            title="Deep Batch Analytics & Embryo Mortality"
                          >
                            <Activity className="w-3.5 h-3.5 text-[#800000]" />
                            <span>Analytics</span>
                          </button>

                          {(b.current_stage === 'DAY_25' || b.current_stage === 'HATCHED' || b.current_stage === 'COMPLETED') && (
                            <button
                              onClick={(e) => handleOpenFinalize(b, e)}
                              className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-bold rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 transition-colors cursor-pointer"
                              title="Finalize Day 28 Hatch Trial"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              <span>Hatch</span>
                            </button>
                          )}

                          <button
                            onClick={(e) => handleOpenCertificate(b, e)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-bold rounded bg-maroon-50 hover:bg-maroon-100 text-[#800000] border border-maroon-200 transition-colors cursor-pointer"
                            title="View Official Candling Certificate"
                          >
                            <Award className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={(e) => handleDeleteBatch(b.batch_id, e)}
                            className="p-1.5 rounded-md hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors cursor-pointer"
                            title="Delete / Archive Cohort"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>

                          <button
                            className="p-1.5 text-slate-400 hover:text-slate-700 cursor-pointer"
                            onClick={() => handleSelectBatch(b)}
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Grid / Card View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {paginatedBatches.map((b) => (
            <div
              key={b.batch_id}
              onClick={() => handleSelectBatch(b)}
              className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs hover:border-[#800000] transition-colors cursor-pointer space-y-4 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between pb-3 border-b border-slate-100">
                  <div>
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-[#800000]" />
                      <h3 className="font-bold text-[#0F172A] text-sm">{b.batch_code}</h3>
                    </div>
                    <span className="text-[11px] text-slate-500 mt-0.5 block">
                      Breed: <strong>{b.breed}</strong> • Incubator: <strong>{b.incubator_id}</strong>
                    </span>
                  </div>
                  <Badge type="stage" value={b.current_stage} />
                </div>

                {/* Classification Breakdown */}
                <div className="grid grid-cols-3 gap-2 text-center mt-3">
                  <div className="p-2 bg-emerald-50 rounded-lg border border-emerald-200">
                    <span className="text-[10px] text-emerald-700 font-bold block">Fertile</span>
                    <span className="text-base font-extrabold text-emerald-900">{b.fertile_count}</span>
                  </div>
                  <div className="p-2 bg-amber-50 rounded-lg border border-amber-200">
                    <span className="text-[10px] text-amber-700 font-bold block">Penoy</span>
                    <span className="text-base font-extrabold text-amber-900">{b.infertile_count}</span>
                  </div>
                  <div className="p-2 bg-red-50 rounded-lg border border-red-200">
                    <span className="text-[10px] text-red-700 font-bold block">Dead</span>
                    <span className="text-base font-extrabold text-red-900">{b.abnormal_count}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs pt-3 text-slate-600">
                  <span>Initial Egg Set: <strong>{b.initial_egg_count}</strong></span>
                  <span className="font-bold text-emerald-700">{b.fertility_rate > 0 ? `${b.fertility_rate}% Fertile` : 'Pending'}</span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500">Day 10 Salvage: <strong>₱{(b.infertile_count * 14.0).toFixed(2)}</strong></span>
                <button
                  onClick={(e) => handleOpenCertificate(b, e)}
                  className="inline-flex items-center gap-1 text-[11px] font-bold text-[#800000] hover:underline"
                >
                  <Award className="w-3.5 h-3.5" />
                  <span>Certificate</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 pt-2">
        <div className="flex items-center gap-2">
          <span>Showing {paginatedBatches.length} of {processedBatches.length} batches</span>
          <span>•</span>
          <span>Rows per page:</span>
          <select
            value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="h-7 px-2 bg-white border border-slate-200 rounded text-slate-700 font-medium focus:outline-none"
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-2 font-bold text-slate-800">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* New Batch Modal Dialog */}
      <Dialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Set New Incubation Batch"
        description="Register a new 28-day duck egg incubation batch in the hatchery."
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
              Save & Register Batch
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

            {/* Candling Sessions Shift Log with Throughput Speed */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-slate-800 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-600" />
                  <span>Operator Candling Sessions & Throughput</span>
                </h4>
                <span className="text-[10px] font-semibold text-slate-500">{batchSessions.length} recorded</span>
              </div>

              {batchSessions.length > 0 ? (
                <div className="space-y-2">
                  {batchSessions.map((s) => (
                    <div key={s.session_id} className="p-2.5 bg-white rounded-lg border border-slate-200 space-y-1.5 shadow-2xs">
                      <div className="flex items-center justify-between font-medium">
                        <span className="font-bold text-[#0F172A]">{s.stage} Candling Run</span>
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 rounded">
                          <Zap className="w-3 h-3 text-emerald-600" />
                          120 eggs/min (2.0 /sec)
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-600">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3 text-slate-400" />
                          {s.operator_name} • {s.device_id}
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

            {/* Official Report Exports & Certificate Trigger */}
            <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-200">
              <button
                type="button"
                onClick={() => handleOpenCertificate(selectedBatch)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-maroon-50 text-[#800000] border border-maroon-200 hover:bg-maroon-100 transition-colors cursor-pointer"
              >
                <Award className="w-3.5 h-3.5" />
                <span>View Quality Certificate</span>
              </button>

              <a
                href={apiClient.downloadCSVUrl(selectedBatch.batch_id)}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </a>
            </div>
          </div>
        )}
      </Sheet>

      {/* Official Candling Quality Certificate Modal */}
      <CandlingCertificateModal
        isOpen={isCertificateOpen}
        onClose={() => setIsCertificateOpen(false)}
        batch={certificateBatch}
      />

      {/* Deep Batch Analytics & Embryo Mortality Modal */}
      <BatchAnalyticsModal
        isOpen={isAnalyticsOpen}
        batchId={analyticsBatchId}
        onClose={() => {
          setIsAnalyticsOpen(false);
          setAnalyticsBatchId(null);
        }}
      />

      {/* Finalize Day 28 Hatch Modal */}
      <FinalizeHatchModal
        isOpen={isFinalizeOpen}
        batch={finalizeBatch}
        onClose={() => {
          setIsFinalizeOpen(false);
          setFinalizeBatch(null);
        }}
        onSuccess={() => {
          fetchBatches();
        }}
      />
    </div>
  );
};
