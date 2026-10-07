import { useSearchParams } from 'react-router-dom';
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
  FileText,
  List,
  LayoutGrid,
  ArrowUpDown,
  ChevronDown,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { BatchSummary, DuckBreed, BatchStage, CandlingSession } from '../types';
import { ActionsMenu } from '../components/ActionsMenu';
import { BatchIncubationStatus } from '../components/BatchIncubationStatus';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { Dialog } from '../components/ui/dialog';
import { Sheet } from '../components/ui/sheet';
import { CandlingCertificateModal } from '../components/CandlingCertificateModal';
import { BatchAnalyticsModal } from '../components/BatchAnalyticsModal';
import { FinalizeHatchModal } from '../components/FinalizeHatchModal';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { EmptyState } from '../components/ui/EmptyState';
import { Activity, Trash2, CheckCircle2, RefreshCw } from 'lucide-react';

type ViewMode = 'TABLE' | 'GRID';
type SortField = 'batch_code' | 'set_date' | 'initial_egg_count' | 'fertility_rate';
type SortOrder = 'asc' | 'desc';

export const BatchesPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const requestedBatch = searchParams.get("batch");
  const [actionError, setActionError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [sessionError, setSessionError] = useState(false);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<ViewMode>(() => window.matchMedia('(max-width: 639px)').matches ? 'GRID' : 'TABLE');
  const [filtersExpanded, setFiltersExpanded] = useState(() => window.matchMedia('(min-width: 640px)').matches);
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
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
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
  const [setDate, setSetDate] = useState(() => {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  });
  const [notes, setNotes] = useState('');

  const fetchBatches = async () => {
    setIsLoading(true);
    setIsError(false);
    try {
      const data = await apiClient.getBatches();
      setBatches(data || []);
    } catch (err) {
      console.error('Failed to fetch batches:', err);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, []);

  const handleSelectBatch = async (b: BatchSummary) => {
    setSelectedBatch(b);
    setIsDrawerOpen(true);
    setBatchSessions([]);
    setSessionError(false);
    try { setBatchSessions(await apiClient.getSessions(b.batch_id)); }
    catch { setSessionError(true); }
  };

  const handleOpenCertificate = (b: BatchSummary, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setCertificateBatch(b);
    setIsCertificateOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isCreating) return;
    setIsCreating(true); setActionError(null);
    try {
      await apiClient.createBatch({ batch_code: batchCode, breed, incubator_id: incubatorId, initial_egg_count: Number(initialCount), set_date: new Date(`${setDate}T00:00:00`).toISOString(), notes });
      setIsCreateOpen(false); setBatchCode(''); setNotes('');
      void fetchBatches();
    } catch { setActionError('The batch could not be created. Check that its code is unique and try again. Your entries are retained.'); }
    finally { setIsCreating(false); }
  };

  const getNextStage = (stage: BatchStage): BatchStage | null => {
    switch (stage) {
      case 'SETTING': return 'DAY_10';
      case 'DAY_10': return 'HATCHED';
      case 'HATCHED': return 'COMPLETED';
      default: return null;
    }
  };

  useEffect(() => {
    const requested = batches.find(batch => batch.batch_id === requestedBatch);
    if (requested) void handleSelectBatch(requested);
  }, [requestedBatch, batches]);

  const handleAdvanceStage = async () => {
    if (!selectedBatch) return;
    const next = getNextStage(selectedBatch.current_stage);
    if (!next) return;

    setIsAdvancing(true);
    try {
      const updated = await apiClient.advanceBatchStage(selectedBatch.batch_id, next);
      setSelectedBatch({ ...updated });
      fetchBatches();
    } catch { setActionError('The batch stage could not be updated. Try again.'); } finally {
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
    } catch { setActionError('Milestones could not be checked. Try again.'); } finally {
      setIsCheckingMilestones(false);
    }
  };

  const handleDeleteBatch = async (batchId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete batch '${batchId}'?`)) return;
    try {
      await apiClient.deleteBatch(batchId);
      if (selectedBatch?.batch_id === batchId) setSelectedBatch(null);
      void fetchBatches();
    } catch { setActionError('The batch could not be deleted. Refresh the list and try again.'); }
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

  const allPageSelected = paginatedBatches.length > 0 && paginatedBatches.every(batch => selectedBatchIds.includes(batch.batch_id));
  const somePageSelected = paginatedBatches.some(batch => selectedBatchIds.includes(batch.batch_id));
  const toggleSelectAll = () => {
    const pageIds = paginatedBatches.map(batch => batch.batch_id);
    setSelectedBatchIds(previous => allPageSelected
      ? previous.filter(id => !pageIds.includes(id))
      : [...new Set([...previous, ...pageIds])]);
  };

  const toggleSelectBatch = (id: string) => {
    setSelectedBatchIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  useEffect(() => {
    setCurrentPage(page => Math.min(page, totalPages));
  }, [totalPages]);

  return (
    <div className="batch-workspace min-w-0 space-y-6 pb-8" aria-busy={isLoading}>
      {actionError && !isCreateOpen && <p role="alert" className="p-4 bg-red-50 text-red-800 border border-red-300 rounded-xl">{actionError}</p>}
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1>
            Incubation batches
          </h1>
          <p className="page-description">
            Track incubation batches, Day 10 candling results, hatch outcomes, and printable records.
          </p>
        </div>

        <div className="page-actions">
          <button
            onClick={handleCheckMilestones}
            disabled={isCheckingMilestones}
            className="secondary-action"
            title="Evaluate elapsed incubation days and flag due candling/transfer milestones"
          >
            <RefreshCw aria-hidden="true" className={`w-4 h-4 ${isCheckingMilestones ? 'animate-spin' : ''}`} />
            <span>{isCheckingMilestones ? 'Checking…' : 'Check milestones'}</span>
          </button>

          <button
            onClick={() => { setActionError(null); setIsCreateOpen(true); }}
            className="primary-action"
          >
            <Plus aria-hidden="true" className="w-4 h-4" />
            <span>New batch</span>
          </button>
        </div>
      </div>

      {milestoneMsg && (
        <div role="status" className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-800 flex items-center gap-2">
          <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{milestoneMsg}</span>
        </div>
      )}

      {/* Enterprise Filter Toolbar */}
      <div className="filter-panel batch-filters space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <div className="relative w-full sm:max-w-md">
            <Search aria-hidden="true" className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              aria-label="Search batches"
              placeholder="Search batch code or incubator unit..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full min-w-0 h-11 pl-9 pr-3 text-sm bg-card border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#800000] "
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
              <button
                onClick={() => setViewMode('TABLE')}
                className={`secondary-action ${
                  viewMode === 'TABLE' ? 'bg-card text-brand ' : 'text-slate-500 hover:text-slate-800'
                }`}
                aria-pressed={viewMode === 'TABLE'} aria-label="Table View" title="Table View"
              >
                <List aria-hidden="true" className="w-3.5 h-3.5" />
                <span>Table</span>
              </button>
              <button
                onClick={() => setViewMode('GRID')}
                className={`secondary-action ${
                  viewMode === 'GRID' ? 'bg-card text-brand ' : 'text-slate-500 hover:text-slate-800'
                }`}
                aria-pressed={viewMode === 'GRID'} aria-label="Grid Cards View" title="Grid Cards View"
              >
                <LayoutGrid aria-hidden="true" className="w-3.5 h-3.5" />
                <span>Grid</span>
              </button>
            </div>
          </div>
        </div>

        <details className="batch-filter-disclosure" open={filtersExpanded} onToggle={event => setFiltersExpanded(event.currentTarget.open)}>
          <summary>Filters<ChevronDown aria-hidden="true" className="w-4 h-4" />{[breedFilter, stageFilter, statusFilter].filter(value => value !== 'ALL').length > 0 && <span> · {[breedFilter, stageFilter, statusFilter].filter(value => value !== 'ALL').length} applied</span>}</summary>
          <div className="batch-filter-fields grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <div><label className="batch-filter-label" htmlFor="batch-filter-breed">Breed</label><div className="relative">
            <select id="batch-filter-breed"
              aria-label="Breed" value={breedFilter}
              onChange={(e) => {
                setBreedFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full min-w-0 h-11 pl-3 pr-8 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10  cursor-pointer appearance-none"
            >
              <option value="ALL">All Duck Breeds</option>
              <option value="KAYUMANGGI">IP-Kayumanggi</option>
              <option value="ITIM">IP-Itim</option>
              <option value="KHAKI">IP-Khaki</option>
            </select>
            <ChevronDown aria-hidden="true" className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div></div>

          <div><label className="batch-filter-label" htmlFor="batch-filter-stage">Stage</label><div className="relative">
            <select id="batch-filter-stage"
              aria-label="Incubation stage" value={stageFilter}
              onChange={(e) => {
                setStageFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full min-w-0 h-11 pl-3 pr-8 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10  cursor-pointer appearance-none"
            >
              <option value="ALL">All Incubation Stages</option>
              <option value="SETTING">Setting (Day 0-9)</option>
              <option value="DAY_10">Day 10 (Candling)</option>
              <option value="HATCHED">Hatched</option>
              <option value="COMPLETED">Completed</option>
            </select>
            <ChevronDown aria-hidden="true" className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div></div>

          <div><label className="batch-filter-label" htmlFor="batch-filter-status">Status</label><div className="relative">
            <select id="batch-filter-status"
              aria-label="Batch status" value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full min-w-0 h-11 pl-3 pr-8 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10  cursor-pointer appearance-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="INCUBATING">Incubating</option>
              <option value="CANDLING_DUE">Candling due</option>
              <option value="ARCHIVED">Archived</option>
              <option value="COMPLETED">Completed</option>
            </select>
            <ChevronDown aria-hidden="true" className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div></div>
          </div>
        </details>
      </div>

      <div className="batch-results-heading">
        <p role="status"><strong>{processedBatches.length}</strong> {processedBatches.length === 1 ? 'batch' : 'batches'}
          {selectedBatchIds.length > 0 && <span> · {selectedBatchIds.length} selected</span>}
        </p>
        {(searchQuery || breedFilter !== 'ALL' || stageFilter !== 'ALL' || statusFilter !== 'ALL') &&
          <button className="action-link" onClick={() => {setSearchQuery(''); setBreedFilter('ALL'); setStageFilter('ALL'); setStatusFilter('ALL'); setCurrentPage(1);}}>Clear filters</button>}
      </div>

      {/* View Mode: Table vs Grid */}
      {isError && batches.length === 0 ? (
        <DataUnavailableState
          title="Batches Service Unavailable"
          description="Unable to load incubation cohorts from the PostgreSQL database. Ensure the backend REST service is reachable."
          onRetry={fetchBatches}
          isRetrying={isLoading}
        />
      ) : isLoading && batches.length === 0 ? (
        <div role="status" className="py-12 text-center text-slate-600">Loading batches…</div>
      ) : !isLoading && batches.length === 0 ? (
        <EmptyState
          title="No Incubation Batches Found"
          description="There are currently no active or historical egg batches in the database. Initialize your first incubation batch to begin candling tracking."
          actionLabel="Initialize First Batch"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : processedBatches.length === 0 ? (
        <EmptyState title="No matching batches" description="No batches match your search and filters." actionLabel="Clear filters" onAction={() => {setSearchQuery(''); setBreedFilter('ALL'); setStageFilter('ALL'); setStatusFilter('ALL'); setCurrentPage(1);}} />
      ) : viewMode === 'TABLE' ? (
        <div className="bg-card border border-border rounded-xl  overflow-hidden">
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Incubation batches, scroll horizontally on smaller screens">
            <table className="batch-table w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th scope="col" className="py-3 px-4 w-10 text-center">
                    <label className="inline-flex min-h-11 min-w-11 items-center justify-center">
                      <input type="checkbox" aria-label="Select all batches on this page" checked={allPageSelected}
                        ref={element => { if (element) element.indeterminate = somePageSelected && !allPageSelected; }}
                        onChange={toggleSelectAll} />
                    </label>
                  </th>
                  <th scope="col" className="py-3 px-4" aria-sort={sortField === 'batch_code' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}>
                    <button className="action-link" onClick={() => toggleSort('batch_code')}
                      aria-label={`Sort batch code ${sortField === 'batch_code' && sortOrder === 'desc' ? 'ascending' : 'descending'}`}>
                      <span>Batch / incubator</span><ArrowUpDown aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </th>

                  <th scope="col" className="py-3 px-4" aria-sort={sortField === 'initial_egg_count' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}>
                    <button className="action-link" onClick={() => toggleSort('initial_egg_count')}
                      aria-label={`Sort initial set ${sortField === 'initial_egg_count' && sortOrder === 'desc' ? 'ascending' : 'descending'}`}>
                      <span>Eggs set</span><ArrowUpDown aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </th>
                  <th scope="col" className="py-3 px-4">Incubation</th>
                  <th scope="col" className="py-3 px-4" aria-sort={sortField === 'fertility_rate' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}>
                    <button className="action-link" onClick={() => toggleSort('fertility_rate')}
                      aria-label={`Sort fertility rate ${sortField === 'fertility_rate' && sortOrder === 'desc' ? 'ascending' : 'descending'}`}>
                      <span>Fertility</span><ArrowUpDown aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </th>
                  <th scope="col" className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedBatches.map((b) => {
                  const isSelected = selectedBatchIds.includes(b.batch_id);
                  return (
                    <tr
                      key={b.batch_id}
                      className={`hover:bg-slate-50 transition-colors ${
                        isSelected ? 'bg-maroon-50/30' : ''
                      }`}
                            >
                      <td className="py-3 px-4 text-center" onClick={e => e.stopPropagation()}>
                        <label className="inline-flex min-h-11 min-w-11 items-center justify-center">
                          <input type="checkbox" aria-label={`Select batch ${b.batch_code}`} checked={isSelected} onChange={() => toggleSelectBatch(b.batch_id)} />
                        </label>
                      </td>
                      <td className="py-3 px-4 batch-identity">
                        <button className="action-link text-left" onClick={() => { void handleSelectBatch(b); }} aria-label={`Open batch details for ${b.batch_code}`}>{b.batch_code}</button>
                        <p>{b.breed === 'KAYUMANGGI' ? 'IP-Kayumanggi' : b.breed === 'ITIM' ? 'IP-Itim' : 'IP-Khaki'} · {b.incubator_id}</p>
                        <p>Set {new Date(b.set_date).toLocaleDateString()}{b.elapsed_days !== undefined ? ` · Day ${b.elapsed_days}` : ''}</p>
                      </td>
                      <td className="py-3 px-4 batch-numbers"><strong>{b.initial_egg_count.toLocaleString()}</strong><p>{b.total_scanned.toLocaleString()} scans</p></td>
                      <td className="py-3 px-4">
                        <BatchIncubationStatus batch={b} />
                      </td>
                      <td className="py-3 px-4 batch-numbers">
                        {b.total_scanned > 0 ? <><strong>{b.fertility_rate}%</strong><p>{b.fertile_count.toLocaleString()} fertile</p></> : <span className="text-slate-500">Awaiting scans</span>}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="batch-row-actions">
                          <button onClick={e => handleOpenAnalytics(b, e)} className="secondary-action" aria-label={`Analytics for ${b.batch_code}`}><Activity aria-hidden="true" className="w-4 h-4" />Analytics</button>
                          <ActionsMenu label={`More actions for ${b.batch_code}`} actions={[
                            { label: 'Batch details', icon: <Layers aria-hidden="true" className="w-4 h-4" />, onSelect: () => { void handleSelectBatch(b); } },
                            { label: 'Candling record', icon: <FileText aria-hidden="true" className="w-4 h-4" />, onSelect: () => handleOpenCertificate(b) },
                            ...((b.current_stage === 'HATCHED' || b.current_stage === 'COMPLETED') ? [{ label: 'Record hatch', icon: <CheckCircle2 aria-hidden="true" className="w-4 h-4" />, onSelect: () => handleOpenFinalize(b) }] : []),
                            { label: 'Delete batch', icon: <Trash2 aria-hidden="true" className="w-4 h-4" />, destructive: true, onSelect: () => { void handleDeleteBatch(b.batch_id); } },
                          ]} />
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
        <div className="batch-card-grid">
          {paginatedBatches.map((b) => (
            <div
              key={b.batch_id}
              className="batch-card min-w-0 bg-card border border-border rounded-xl p-5 space-y-4 flex flex-col justify-between"
            >
              <div>
                <div className="flex flex-wrap items-start justify-between gap-2 pb-3 border-b border-slate-100">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Layers aria-hidden="true" className="w-4 h-4 text-brand" />
                      <h3 className="font-semibold text-foreground text-base break-words">{b.batch_code}</h3>
                    </div>
                    <span className="text-sm text-slate-600 mt-1 block">
                      Breed: <strong>{b.breed === 'KAYUMANGGI' ? 'IP-Kayumanggi' : b.breed === 'ITIM' ? 'IP-Itim' : 'IP-Khaki'}</strong> • Incubator: <strong>{b.incubator_id}</strong>
                    </span>
                  </div>
                  <BatchIncubationStatus batch={b} />
                </div>

                {/* Classification Breakdown */}
                <p className="text-sm text-slate-600 mt-3">Set {new Date(b.set_date).toLocaleDateString()}{b.elapsed_days !== undefined ? ` · Day ${b.elapsed_days}` : ''}</p>
                <div className="batch-classification grid grid-cols-2 gap-4 mt-4">
                  <div className="text-agri-green">
                    <span className="text-sm text-slate-600 block">Fertile</span>
                    <span className="text-2xl font-semibold text-agri-green">{b.fertile_count}</span>
                  </div>
                  <div className="text-red-700">
                    <span className="text-sm text-slate-600 block">Penoy</span>
                    <span className="text-2xl font-semibold text-red-700">{b.infertile_count}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 text-xs pt-3 text-slate-600">
                  <span>Initial Egg Set: <strong>{b.initial_egg_count}</strong></span>
                  <span className="font-bold text-emerald-700">{b.total_scanned > 0 ? `${b.fertility_rate}% Fertile` : 'Pending'}</span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="text-slate-500">Day 10 Salvage: <strong>₱{(b.infertile_count * 14.0).toFixed(2)}</strong></span>
                <button
                  onClick={(e) => handleOpenCertificate(b, e)}
                  className="action-link"
                >
                  <FileText aria-hidden="true" className="w-3.5 h-3.5" />
                  <span>Candling record</span>
                </button>
              </div>
              <div className="page-actions">
                <button className="secondary-action" onClick={() => { void handleSelectBatch(b); }} aria-label={`Inspect batch ${b.batch_code}`}><ChevronRight aria-hidden="true" className="w-4 h-4" />Inspect</button>
                <button className="secondary-action" onClick={() => handleOpenAnalytics(b)}><Activity aria-hidden="true" className="w-4 h-4" />Analytics</button>
                {(b.current_stage === 'HATCHED' || b.current_stage === 'COMPLETED') && <button className="secondary-action" onClick={() => handleOpenFinalize(b)}><CheckCircle2 aria-hidden="true" className="w-4 h-4" />Hatch</button>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 pt-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span>Showing {paginatedBatches.length} of {processedBatches.length} batches</span>
          <span>•</span>
          <span>Rows per page:</span>
          <select
            aria-label="Rows per page" value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="h-7 px-2 bg-card border border-slate-200 rounded text-slate-700 font-medium focus:outline-none"
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
            aria-label="Previous page" disabled={currentPage === 1}
            className="secondary-action"
          >
            <ChevronLeft aria-hidden="true" className="w-4 h-4" />
          </button>
          <span className="px-2 font-bold text-slate-800">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            aria-label="Next page" disabled={currentPage === totalPages}
            className="secondary-action"
          >
            <ChevronRight aria-hidden="true" className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* New Batch Modal Dialog */}
      <Dialog
        isOpen={isCreateOpen}
        onClose={() => { if (!isCreating) setIsCreateOpen(false); }}
        title="Set New Incubation Batch"
        description="Register a new 28-day duck egg incubation batch in the hatchery."
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4 text-sm">
          {actionError && <p role="alert" className="text-red-800">{actionError}</p>}
          <div className="space-y-1.5">
            <label htmlFor="batchespage-field-1" className="font-semibold text-xs text-slate-700">Batch Code / Identifier</label>
            <input id="batchespage-field-1"
              required
              placeholder="e.g. BATCH-2026-08-KAY-03"
              value={batchCode}
              onChange={(e) => setBatchCode(e.target.value)}
              className="w-full min-w-0 h-11 px-3 text-xs bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label htmlFor="batchespage-field-2" className="font-semibold text-xs text-slate-700">Duck Breed</label>
              <select id="batchespage-field-2"
                value={breed}
                onChange={(e) => setBreed(e.target.value as DuckBreed)}
                className="w-full min-w-0 h-11 px-3 text-xs bg-card border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:border-[#800000]"
              >
                <option value="KAYUMANGGI">IP-Kayumanggi</option>
                <option value="ITIM">IP-Itim</option>
                <option value="KHAKI">IP-Khaki</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="batchespage-field-3" className="font-semibold text-xs text-slate-700">Incubator Unit</label>
              <input id="batchespage-field-3"
                required
                value={incubatorId}
                onChange={(e) => setIncubatorId(e.target.value)}
                className="w-full min-w-0 h-11 px-3 text-xs bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="batchespage-field-4" className="font-semibold text-xs text-slate-700">Initial Egg Count</label>
            <input id="batchespage-field-4"
              type="number"
              min="1"
              required
              value={initialCount}
              onChange={(e) => setInitialCount(Number(e.target.value))}
              className="w-full min-w-0 h-11 px-3 text-xs bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="batch-set-date" className="font-semibold text-xs text-slate-700">Set Date</label>
            <input id="batch-set-date" type="date" required value={setDate} onChange={event => setSetDate(event.target.value)}
              className="w-full min-w-0 max-w-full px-3 bg-card border border-slate-200 rounded-lg text-slate-800" />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="batchespage-field-5" className="font-semibold text-xs text-slate-700">Source Notes & Farm Origin</label>
            <textarea id="batchespage-field-5"
              rows={3}
              placeholder="Breeder farm source, flock age, initial candling condition..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full min-w-0 px-3 py-2 text-xs bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="page-actions justify-end pt-3 border-t border-slate-200">
            <button
              type="button"
              disabled={isCreating} onClick={() => setIsCreateOpen(false)}
              className="secondary-action"
            >
              Cancel
            </button>
            <button
              type="submit" disabled={isCreating}
              className="primary-action"
            >
              {isCreating ? 'Saving…' : 'Create batch'}
            </button>
          </div>
        </form>
      </Dialog>

      {/* Batch Details Drawer (Sheet) */}
      <Sheet
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedBatch ? `Batch: ${selectedBatch.batch_code}` : ''}
        description="Incubation progress, operator candling shifts, and yield metrics"
      >
        {selectedBatch && (
          <div className="min-w-0 space-y-5 text-sm break-words">
            {sessionError && <p role="alert" className="text-amber-800">Session records could not be loaded. Close and reopen this batch to retry.</p>}
            {actionError && <p role="alert" className="text-red-800">{actionError}</p>}
            {/* Timeline */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <span className="font-bold text-slate-800">28-Day Milestone Progress</span>
                {getNextStage(selectedBatch.current_stage) && (
                  <button
                    onClick={handleAdvanceStage}
                    disabled={isAdvancing}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#800000] hover:bg-[#6B0000] text-white text-[11px] font-bold  cursor-pointer disabled:opacity-50"
                  >
                    <FastForward aria-hidden="true" className="w-3 h-3" />
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
                <span className="text-sm font-bold text-foreground mt-0.5 block">{selectedBatch.breed}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-semibold uppercase block">Incubator Unit</span>
                <span className="text-sm font-bold text-foreground mt-0.5 block">{selectedBatch.incubator_id}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-semibold uppercase block">Initial Egg Set</span>
                <span className="text-sm font-bold text-foreground mt-0.5 block">{selectedBatch.initial_egg_count} eggs</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-semibold uppercase block">Fertility Rate</span>
                <span className="text-sm font-bold text-emerald-700 mt-0.5 block">{selectedBatch.fertility_rate}%</span>
              </div>
            </div>

            {/* Classification Yield Breakdown */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <h4 className="font-bold text-slate-800">Candling Yield Summary</h4>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="text-agri-green">
                  <span className="text-[10px] text-emerald-700 font-semibold block">Fertile</span>
                  <span className="text-2xl font-semibold text-agri-green">{selectedBatch.fertile_count}</span>
                </div>
                <div className="text-red-700">
                  <span className="text-[10px] text-amber-700 font-semibold block">Penoy</span>
                  <span className="text-2xl font-semibold text-red-700">{selectedBatch.infertile_count}</span>
                </div>
              </div>
            </div>

            {/* Candling Sessions Shift Log with Throughput Speed */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-slate-800 flex items-center gap-1.5">
                  <Clock aria-hidden="true" className="w-3.5 h-3.5 text-slate-600" />
                  <span>Operator Candling Sessions & Throughput</span>
                </h4>
                <span className="text-[10px] font-semibold text-slate-500">{batchSessions.length} recorded</span>
              </div>

              {batchSessions.length > 0 ? (
                <div className="space-y-2">
                  {batchSessions.map((s) => (
                    <div key={s.session_id} className="p-2.5 bg-card rounded-lg border border-slate-200 space-y-1.5 ">
                      <div className="flex flex-wrap items-center justify-between gap-2 font-medium">
                        <span className="font-bold text-foreground">{s.stage} Candling Run</span>
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 rounded">
                          <Zap aria-hidden="true" className="w-3 h-3 text-emerald-600" />
                          {s.total_scanned} eggs candled
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
                        <span className="flex items-center gap-1">
                          <User aria-hidden="true" className="w-3 h-3 text-slate-400" />
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
            <div className="page-actions justify-end pt-3 border-t border-slate-200">
              <button
                type="button"
                onClick={() => handleOpenCertificate(selectedBatch)}
                className="secondary-action"
              >
                <FileText aria-hidden="true" className="w-3.5 h-3.5" />
                <span>View candling record</span>
              </button>

              <a
                href={apiClient.downloadCSVUrl(selectedBatch.batch_id)}
                download
                className="secondary-action"
              >
                <Download aria-hidden="true" className="w-3.5 h-3.5" />
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
