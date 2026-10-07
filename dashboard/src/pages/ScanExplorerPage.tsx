import { useSearchParams } from 'react-router-dom';
import { usePreferences } from '../hooks/usePreferences';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search,
  ChevronRight,
  ChevronLeft,
  ScanLine,
  CheckCircle2,
  AlertTriangle,
  Edit3,
  List,
  LayoutGrid,
  ArrowUpDown,
  Zap,
  RefreshCw,
  Layers,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { EggScan, FertilityClass, BatchSummary, ScanSearchParams } from '../types';
import { Badge } from '../components/Badge';
import { CandlingAperture } from '../components/CandlingAperture';
import { Sheet } from '../components/ui/sheet';
import { HumanInTheLoopOverrideModal } from '../components/HumanInTheLoopOverrideModal';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { EmptyState } from '../components/ui/EmptyState';

type ViewMode = 'TABLE' | 'GRID';
type SortField = 'sequence_number' | 'confidence' | 'inference_ms' | 'scanned_at';
type SortOrder = 'asc' | 'desc';

export const ScanExplorerPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { pollingInterval } = usePreferences();
  const requestRef = useRef<AbortController | null>(null);
  const [totalScans, setTotalScans] = useState(0);
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [scans, setScans] = useState<EggScan[]>([]);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('TABLE');
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  
  // Filters
  const [classFilter, setClassFilter] = useState<string>('ALL');
  const [batchFilter, setBatchFilter] = useState<string>('ALL');
  const [confidenceFilter, setConfidenceFilter] = useState<NonNullable<ScanSearchParams['confidence']>>(() => searchParams.get('review') === '1' ? 'REVIEW' : 'ALL');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Sorting & Pagination
  const [sortField, setSortField] = useState<SortField>('scanned_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Live Auto-Refresh
  const [selectedScan, setSelectedScan] = useState<EggScan | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [isLiveAutoRefresh, setIsLiveAutoRefresh] = useState(false);

  // Human-in-the-Loop Override Prompt Modal State
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [pendingOverrideClass, setPendingOverrideClass] = useState<FertilityClass | null>(null);
  const [overrideToast, setOverrideToast] = useState<string | null>(null);

  const fetchScans = useCallback(async () => {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setIsLoading(true);
    setIsError(false);
    try {
      const page = await apiClient.searchScans({
        final_class: classFilter === 'ALL' ? undefined : classFilter as FertilityClass,
        batch_id: batchFilter === 'ALL' ? undefined : batchFilter,
        confidence: confidenceFilter,
        q: debouncedSearch,
        sort: sortField,
        order: sortOrder,
        limit: rowsPerPage,
        offset: (currentPage - 1) * rowsPerPage,
      }, controller.signal);
      if (controller.signal.aborted) return;
      setScans(page.items);
      setTotalScans(page.total);
      const lastPage = Math.max(1, Math.ceil(page.total / rowsPerPage));
      if (currentPage > lastPage) setCurrentPage(lastPage);
    } catch {
      if (!controller.signal.aborted) setIsError(true);
    } finally {
      if (!controller.signal.aborted) setIsLoading(false);
    }
  }, [classFilter, batchFilter, confidenceFilter, debouncedSearch, sortField, sortOrder, rowsPerPage, currentPage]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const fetchBatches = async () => {
    try {
      const data = await apiClient.getBatches();
      if (Array.isArray(data)) {
        setBatches(data);
      }
    } catch (err) {
      console.error('Error fetching batches:', err);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, []);

  useEffect(() => {
    void fetchScans();
    if (!isLiveAutoRefresh || pollingInterval === 0) return () => requestRef.current?.abort();
    const timer = setInterval(() => { void fetchScans(); }, pollingInterval * 1000);
    return () => { clearInterval(timer); requestRef.current?.abort(); };
  }, [fetchScans, isLiveAutoRefresh, pollingInterval]);

  const handlePromptOverride = (targetClass: FertilityClass) => {
    if (!selectedScan) return;
    setPendingOverrideClass(targetClass);
    setIsOverrideModalOpen(true);
  };

  const handleConfirmOverride = async (targetClass: FertilityClass, reason: string) => {
    if (!selectedScan) return;
    try {
      const updated = await apiClient.overrideScanClassification(selectedScan.scan_id, targetClass, reason);
      setSelectedScan({ ...updated });
      fetchScans();
      setOverrideToast(`Scan #${selectedScan.sequence_number ?? 0} reclassified to ${targetClass}. Logged in Audit Trail.`);
      setTimeout(() => setOverrideToast(null), 4000);
    } catch (err) {
      console.error('Error overriding scan:', err);
      throw err;
    }
  };

  const processedScans = scans;
  const paginatedScans = scans;
  const totalPages = Math.max(1, Math.ceil(totalScans / rowsPerPage));

  const toggleSort = (field: SortField) => {
    setCurrentPage(1);
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  return (
    <div className="space-y-6 pb-8" aria-busy={isLoading}>
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-foreground tracking-tight">
            Candling Scan Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Find Day 10 egg scans, inspect confidence, and record classification corrections.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => { void fetchScans(); }} disabled={isLoading} className="inline-flex items-center gap-2 border border-slate-300 rounded-lg px-3 py-2">
            <RefreshCw className="w-4 h-4" /> {isLoading ? 'Refreshing…' : 'Refresh'}
          </button>
          {/* Live Auto-Refresh Button */}
          <button
            onClick={() => setIsLiveAutoRefresh(prev => !prev)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer ${
              isLiveAutoRefresh
                ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                : 'bg-card border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
            aria-pressed={isLiveAutoRefresh}
            disabled={pollingInterval === 0}
            aria-label="Refresh using the interval selected in Settings" title="Refresh using the interval selected in Settings"
          >
            <span className={`w-2 h-2 rounded-full ${isLiveAutoRefresh ? 'bg-emerald-600 animate-pulse' : 'bg-slate-400'}`} />
            <span>{pollingInterval === 0 ? 'Manual refresh' : isLiveAutoRefresh ? `Auto-refresh: ${pollingInterval}s` : 'Auto-refresh: off'}</span>
          </button>

          <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
            {totalScans.toLocaleString()} scans
          </span>
        </div>
      </div>

      {overrideToast && (
        <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs font-semibold text-amber-900 flex items-center gap-2.5  ">
          <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0 animate-pulse" />
          <span>{overrideToast}</span>
        </div>
      )}

      {/* Enterprise Filter Toolbar */}
      <div className="bg-card border border-border rounded-xl p-4  space-y-3 ">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              aria-label="Search scan number, batch, or scan ID"
              placeholder="Search scan number, batch, or ID"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 pl-9 pr-3 text-xs bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10  transition-all"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 self-end sm:self-auto">
            <button
              onClick={() => setViewMode('TABLE')}
              className={`p-1.5 rounded text-xs font-bold flex items-center gap-1 cursor-pointer transition-all btn-press ${
                viewMode === 'TABLE' ? 'bg-card text-brand ' : 'text-slate-600 hover:text-slate-900'
              }`}
              aria-label="Table View" title="Table View"
            >
              <List className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
            <button
              onClick={() => setViewMode('GRID')}
              className={`p-1.5 rounded text-xs font-bold flex items-center gap-1 cursor-pointer transition-all btn-press ${
                viewMode === 'GRID' ? 'bg-card text-brand ' : 'text-slate-600 hover:text-slate-900'
              }`}
              aria-label="Aperture Grid Cards View" title="Aperture Grid Cards View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Grid</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          <select
            aria-label="Classification"
            value={classFilter}
            onChange={(e) => {
              setClassFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000]  cursor-pointer hover:border-slate-300 transition-colors"
          >
            <option value="ALL">All Classes</option>
            <option value="FERTILE">Fertile (Accept)</option>
            <option value="INFERTILE">Infertile (Penoy)</option>
          </select>

          <select
            aria-label="Batch"
            value={batchFilter}
            onChange={(e) => {
              setBatchFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000]  cursor-pointer hover:border-slate-300 transition-colors"
          >
            <option value="ALL">All Batches</option>
            {batches.map((batch) => (
              <option key={batch.batch_id} value={batch.batch_id}>
                {batch.batch_code}
              </option>
            ))}
          </select>

          <select
            aria-label="Confidence or review threshold"
            value={confidenceFilter}
            onChange={(e) => {
              setConfidenceFilter(e.target.value as NonNullable<ScanSearchParams['confidence']>);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000]  cursor-pointer hover:border-slate-300 transition-colors"
          >
            <option value="ALL">All Confidence Levels</option>
            <option value="HIGH">High Confidence (≥ 90%)</option>
            <option value="MID">Medium confidence (75% to under 90%)</option>
            <option value="REVIEW">Needs inspection (under 75%)</option>
          </select>
        </div>
      </div>

      {/* Main View Container (Table vs. Cards Grid) */}
      {isError && scans.length > 0 && (
        <div role="alert" className="p-4 border border-amber-300 bg-amber-50 rounded-xl text-sm text-amber-900">Refresh failed. Previously loaded records are shown. Use Refresh to retry.</div>
      )}
      {isError && scans.length === 0 ? (
        <DataUnavailableState
          title="Scan Telemetry Offline"
          description="Unable to load real-time candling scans from the PostgreSQL database. Ensure the backend REST service is reachable."
          onRetry={fetchScans}
          isRetrying={isLoading}
        />
      ) : isLoading && scans.length === 0 ? (
        <div role="status" className="py-12 text-center text-slate-600">Loading scan records…</div>
      ) : !isLoading && processedScans.length === 0 ? (
        <EmptyState
          title="No Egg Scans Found"
          description="No individual egg candling records match your filter criteria or have been synced from edge sorter stations."
        />
      ) : viewMode === 'TABLE' ? (
        <div className="bg-card border border-border rounded-xl  overflow-hidden  ">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[680px]">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    tabIndex={0}
                    aria-sort={sortField === 'sequence_number' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSort('sequence_number'); } }}
                    onClick={() => toggleSort('sequence_number')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span># Seq</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Batch ID</th>
                  <th className="py-3 px-4">Classification</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    tabIndex={0}
                    aria-sort={sortField === 'confidence' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSort('confidence'); } }}
                    onClick={() => toggleSort('confidence')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Confidence</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    tabIndex={0}
                    aria-sort={sortField === 'inference_ms' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSort('inference_ms'); } }}
                    onClick={() => toggleSort('inference_ms')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Inference</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Routing</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    tabIndex={0}
                    aria-sort={sortField === 'scanned_at' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSort('scanned_at'); } }}
                    onClick={() => toggleSort('scanned_at')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Timestamp</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedScans.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400">
                      No matching candling scans found.
                    </td>
                  </tr>
                ) : (
                  paginatedScans.map((scan) => (
                    <tr
                      key={scan.scan_id}
                      className="table-row-hover cursor-pointer group" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.currentTarget.click(); } }}
                      onClick={() => {
                        setSelectedScan(scan);
                        setIsSheetOpen(true);
                      }}
                    >
                      <td className="py-3 px-4 font-mono font-bold text-slate-700 group-hover:text-brand transition-colors">
                        #{((scan.sequence_number ?? 0)).toString().padStart(3, '0')}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900">{scan.batch_id || 'N/A'}</td>
                      <td className="py-3 px-4">
                        <Badge type="fertility" value={scan.final_class} />
                        {scan.confidence < 0.75 && <span className="block text-amber-800 mt-1">Needs inspection</span>}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        {((scan.confidence ?? 0) * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4 text-slate-700 font-mono">
                        {(scan.inference_ms ?? 0).toFixed(1)} ms
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`font-bold ${
                            scan.routing_action === 'ACCEPT' ? 'text-emerald-800' : 'text-rose-800'
                          }`}
                        >
                          {scan.routing_action || (scan.final_class === 'FERTILE' ? 'ACCEPT' : 'REJECT')}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500 font-medium">
                        {scan.scanned_at
                          ? new Date(scan.scanned_at).toLocaleString('en-PH', {
                              month: 'short', day: 'numeric', year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })
                          : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          aria-label={`Inspect scan ${scan.sequence_number}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedScan(scan);
                            setIsSheetOpen(true);
                          }}
                          className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 cursor-pointer"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Grid / Aperture Cards View */
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {paginatedScans.length === 0 ? (
            <div className="col-span-full py-12 text-center text-slate-400 bg-card rounded-xl border border-slate-200">
              No matching candling scans found.
            </div>
          ) : (
            paginatedScans.map((scan) => (
              <div
                key={scan.scan_id}
                role="button"
                tabIndex={0}
                aria-label={`Inspect scan ${scan.sequence_number}`}
                onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.currentTarget.click(); } }}
                onClick={() => {
                  setSelectedScan(scan);
                  setIsSheetOpen(true);
                }}
                className="bg-card border border-border rounded-xl p-4  hover:border-[#800000]  transition-all cursor-pointer space-y-3 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="font-mono font-bold text-xs text-slate-700">
                      #{((scan.sequence_number ?? 0)).toString().padStart(3, '0')}
                    </span>
                    <Badge type="fertility" value={scan.final_class} />
                        {scan.confidence < 0.75 && <span className="block text-amber-800 mt-1">Needs inspection</span>}
                  </div>

                  <div className="mt-2">
                    <CandlingAperture
                      imageUrl={scan.thumbnail_url || scan.image_url}
                      finalClass={scan.final_class}
                      confidence={scan.confidence ?? 0}
                      inferenceMs={scan.inference_ms ?? 0}
                    />
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <span className="font-mono">{scan.batch_id || 'N/A'}</span>
                  <span className="font-bold text-slate-700">{((scan.confidence ?? 0) * 100).toFixed(0)}% Conf</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Pagination Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-600 bg-card p-4 rounded-xl border border-border ">
        <div className="flex items-center gap-2 flex-wrap">
          <span>Showing {totalScans === 0 ? 0 : (currentPage - 1) * rowsPerPage + 1}–{Math.min(currentPage * rowsPerPage, totalScans)} of {totalScans.toLocaleString()} scans</span>
          <span>•</span>
          <span>Rows per page:</span>
          <select
            aria-label="Rows per page"
            value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="h-8 px-2 bg-card border border-slate-200 rounded text-slate-700 focus:outline-none focus:border-[#800000] cursor-pointer"
          >
            <option value={8}>8</option>
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            aria-label="Previous page"
            disabled={isLoading || currentPage === 1}
            className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-2 font-bold text-slate-800">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            aria-label="Next page"
            disabled={isLoading || currentPage === totalPages}
            className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Scan Details & Human-in-the-Loop Override Drawer (Sheet) */}
      <Sheet
        isOpen={isSheetOpen}
        onClose={() => setIsSheetOpen(false)}
        title={selectedScan ? `Candling Scan #${selectedScan.sequence_number ?? 0}` : ''}
        description={selectedScan ? `Batch: ${selectedScan.batch_id || 'N/A'} • UUID: ${selectedScan.scan_id}` : ''}
      >
        {selectedScan && (
          <div className="space-y-4 text-xs">
            {/* Visual Candling Aperture */}
            <CandlingAperture
              imageUrl={selectedScan.image_url || selectedScan.thumbnail_url}
              finalClass={selectedScan.final_class}
              confidence={selectedScan.confidence ?? 0}
              inferenceMs={selectedScan.inference_ms ?? 0}
              sequenceNumber={selectedScan.sequence_number ?? 0}
              batchId={selectedScan.batch_id}
              aspectRatio={0.78}
            />

            {/* Decision card */}
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800">Conveyor Routing Action:</span>
                <span
                  className={`font-bold ${
                    (selectedScan.routing_action === 'ACCEPT' || selectedScan.final_class === 'FERTILE') ? 'text-emerald-800' : 'text-rose-800'
                  }`}
                >
                  {(selectedScan.routing_action === 'ACCEPT' || selectedScan.final_class === 'FERTILE') ? 'ACCEPT (Incubation Tray)' : 'REJECT (Diverter Eject)'}
                </span>
              </div>
              <p className="text-slate-600 text-[11px]">
                {selectedScan.final_class === 'FERTILE'
                  ? 'Viable Day 10 embryo verified. Retained for incubation.'
                  : 'Non-fertile Day 10 result. Diverted to Penoy food salvage tray @ ₱14.00.'}
              </p>
            </div>

            {/* Human-in-the-Loop Override Section */}
            <div className="p-3.5 bg-amber-50 border border-amber-300 rounded-lg space-y-2.5">
              <div className="flex items-center gap-1.5 font-bold text-amber-950">
                <Edit3 className="w-4 h-4 text-amber-800" />
                <span>Human-in-the-Loop Override:</span>
              </div>

              <p className="text-[11px] text-amber-900 font-medium">
                If the automated YOLOv8 model made a false classification, re-annotate below. This updates the batch yield and logs an immutable audit event.
              </p>

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => handlePromptOverride('FERTILE')}
                  className={`px-2.5 py-1 text-xs font-bold rounded border transition-colors cursor-pointer ${
                    selectedScan.final_class === 'FERTILE'
                      ? 'bg-emerald-700 text-white border-emerald-800'
                      : 'bg-card text-emerald-800 border-emerald-300 hover:bg-emerald-50'
                  }`}
                >
                  Override to FERTILE
                </button>

                <button
                  type="button"
                  onClick={() => handlePromptOverride('INFERTILE')}
                  className={`px-2.5 py-1 text-xs font-bold rounded border transition-colors cursor-pointer ${
                    selectedScan.final_class === 'INFERTILE'
                      ? 'bg-amber-700 text-white border-amber-800'
                      : 'bg-card text-amber-900 border-amber-300 hover:bg-amber-50'
                  }`}
                >
                  Override to PENOY
                </button>

              </div>
            </div>

            {/* Raw Detections Metadata */}
            <div className="space-y-1.5">
              <span className="font-bold text-slate-800 block">YOLOv8 Detection Telemetry</span>
              <pre className="p-3 rounded-lg bg-slate-900 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-32">
                {JSON.stringify(
                  Array.isArray(selectedScan.detections) && selectedScan.detections.length > 0
                    ? selectedScan.detections
                    : [
                        {
                          bbox: [0.24, 0.18, 0.76, 0.88],
                          class_name: selectedScan.final_class || 'FERTILE',
                          confidence: selectedScan.confidence ?? 0.95,
                          aspect_ratio: 0.78,
                        }
                      ],
                  null,
                  2
                )}
              </pre>
            </div>
          </div>
        )}
      </Sheet>

      {/* Human-in-the-Loop Override Confirmation Modal */}
      <HumanInTheLoopOverrideModal
        isOpen={isOverrideModalOpen}
        scan={selectedScan}
        targetClass={pendingOverrideClass}
        onClose={() => {
          setIsOverrideModalOpen(false);
          setPendingOverrideClass(null);
        }}
        onConfirm={handleConfirmOverride}
      />
    </div>
  );
};
