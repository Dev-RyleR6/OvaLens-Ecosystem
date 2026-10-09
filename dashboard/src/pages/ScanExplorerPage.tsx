import { useSearchParams } from 'react-router-dom';
import { usePreferences } from '../hooks/usePreferences';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  Edit3,
  List,
  LayoutGrid,
  ArrowUpDown,
  RefreshCw,
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

const scanLabel = (scan: EggScan) => Number.isFinite(scan.sequence_number)
  ? `Scan #${scan.sequence_number}`
  : `Scan ${scan.scan_id}`;

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
      setOverrideToast(`${scanLabel(selectedScan)} reclassified to ${targetClass}. Logged in Audit Trail.`);
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
    <div className="min-w-0 space-y-6 pb-8" aria-busy={isLoading}>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1>
            Candling Scan Explorer
          </h1>
          <p className="page-description">
            Find Day 10 egg scans, inspect confidence, and record classification corrections.
          </p>
        </div>

        <div className="page-actions">
          <button onClick={() => { void fetchScans(); }} disabled={isLoading} className="secondary-action">
            <RefreshCw aria-hidden="true" className="w-4 h-4" /> {isLoading ? 'Refreshing…' : 'Refresh'}
          </button>
          {/* Live Auto-Refresh Button */}
          <button
            onClick={() => setIsLiveAutoRefresh(prev => !prev)}
            className={`secondary-action ${
              isLiveAutoRefresh
                ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                : 'bg-card border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
            aria-pressed={isLiveAutoRefresh}
            disabled={pollingInterval === 0}
            aria-label="Refresh using the interval selected in Settings" title="Refresh using the interval selected in Settings"
          >
            <RefreshCw aria-hidden="true" className="w-4 h-4" />
            <span>{pollingInterval === 0 ? 'Manual refresh' : isLiveAutoRefresh ? `Auto-refresh: ${pollingInterval}s` : 'Auto-refresh: off'}</span>
          </button>

          <span className="text-sm text-slate-600 tabular-nums">
            {totalScans.toLocaleString()} scans
          </span>
        </div>
      </div>

      {overrideToast && (
        <div role="status" className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-800 flex items-center gap-2.5">
          <CheckCircle2 aria-hidden="true" className="w-4 h-4 shrink-0" />
          <span>{overrideToast}</span>
        </div>
      )}

      {/* Enterprise Filter Toolbar */}
      <div className="filter-panel space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <div className="relative w-full sm:w-80">
            <Search aria-hidden="true" className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              aria-label="Search scan number, batch, or scan ID"
              placeholder="Search scan number, batch, or ID"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full min-w-0 h-11 pl-9 pr-3 text-xs bg-card border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10  transition-all"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 self-end sm:self-auto">
            <button
              onClick={() => setViewMode('TABLE')}
              className={`secondary-action ${
                viewMode === 'TABLE' ? 'bg-card text-brand ' : 'text-slate-600 hover:text-slate-900'
              }`}
              aria-pressed={viewMode === 'TABLE'} aria-label="Table View" title="Table View"
            >
              <List aria-hidden="true" className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
            <button
              onClick={() => setViewMode('GRID')}
              className={`secondary-action ${
                viewMode === 'GRID' ? 'bg-card text-brand ' : 'text-slate-600 hover:text-slate-900'
              }`}
              aria-pressed={viewMode === 'GRID'} aria-label="Aperture Grid Cards View" title="Aperture Grid Cards View"
            >
              <LayoutGrid aria-hidden="true" className="w-3.5 h-3.5" />
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
            className="min-w-0 w-full h-11 px-3 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000]  cursor-pointer hover:border-slate-300 transition-colors"
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
            className="min-w-0 w-full h-11 px-3 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000]  cursor-pointer hover:border-slate-300 transition-colors"
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
            className="min-w-0 w-full h-11 px-3 bg-card border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000]  cursor-pointer hover:border-slate-300 transition-colors"
          >
            <option value="ALL">All Confidence Levels</option>
            <option value="HIGH">High Confidence (≥ 90%)</option>
            <option value="MID">Medium confidence (75% to under 90%)</option>
            <option value="REVIEW">Needs manual review</option>
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
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Candling scans, scroll horizontally on smaller screens">
            <table className="w-full text-left text-xs min-w-[1080px]">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                  <th scope="col" className="py-3 px-4" aria-sort={sortField === 'sequence_number' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}>
                    <button className="action-link" onClick={() => toggleSort('sequence_number')}
                      aria-label={`Sort sequence ${sortField === 'sequence_number' && sortOrder === 'desc' ? 'ascending' : 'descending'}`}>
                      <span># Seq</span><ArrowUpDown aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </th>
                  <th scope="col" className="py-3 px-4">Batch ID</th>
                  <th scope="col" className="py-3 px-4">Classification</th>
                  <th scope="col" className="py-3 px-4" aria-sort={sortField === 'confidence' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}>
                    <button className="action-link" onClick={() => toggleSort('confidence')}
                      aria-label={`Sort confidence ${sortField === 'confidence' && sortOrder === 'desc' ? 'ascending' : 'descending'}`}>
                      <span>Confidence</span><ArrowUpDown aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </th>
                  <th scope="col" className="py-3 px-4" aria-sort={sortField === 'inference_ms' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}>
                    <button className="action-link" onClick={() => toggleSort('inference_ms')}
                      aria-label={`Sort inference ${sortField === 'inference_ms' && sortOrder === 'desc' ? 'ascending' : 'descending'}`}>
                      <span>Inference</span><ArrowUpDown aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </th>
                  <th scope="col" className="py-3 px-4">Routing</th>
                  <th scope="col" className="py-3 px-4" aria-sort={sortField === 'scanned_at' ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'}>
                    <button className="action-link" onClick={() => toggleSort('scanned_at')}
                      aria-label={`Sort timestamp ${sortField === 'scanned_at' && sortOrder === 'desc' ? 'ascending' : 'descending'}`}>
                      <span>Timestamp</span><ArrowUpDown aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </th>
                  <th scope="col" className="py-3 px-4 text-right">Inspect</th>
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
                      className="table-row-hover cursor-pointer group"
                      onClick={() => {
                        setSelectedScan(scan);
                        setIsSheetOpen(true);
                      }}
                    >
                      <td className="py-3 px-4 font-mono font-bold text-slate-700 group-hover:text-brand transition-colors">
                        {Number.isFinite(scan.sequence_number) ? `#${scan.sequence_number!.toString().padStart(3, '0')}` : '—'}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900">{scan.batch_id || 'N/A'}</td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Badge type="fertility" value={scan.final_class} />
                          {scan.routing_action === 'MANUAL_REVIEW' && <Badge value="MANUAL_REVIEW" size="sm" />}
                          {Number.isFinite(scan.confidence) && scan.confidence < 0.75 && <span className="status-badge status-neutral">Low confidence</span>}
                          {scan.is_overridden && <Badge value="OVERRIDDEN" size="sm" />}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        {Number.isFinite(scan.confidence) ? `${(scan.confidence * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-3 px-4 text-slate-700 font-mono">
                        {Number.isFinite(scan.inference_ms) ? `${scan.inference_ms.toFixed(1)} ms` : '—'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`status-badge ${scan.routing_action === 'MANUAL_REVIEW' ? 'status-warning' : scan.routing_action === 'ACCEPT' ? 'status-success' : scan.routing_action === 'REJECT' ? 'status-danger' : 'status-neutral'}`}>
                          {scan.routing_action === 'MANUAL_REVIEW' ? 'REVIEW' : scan.routing_action || 'Unavailable'}
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
                          aria-label={`Inspect ${scanLabel(scan)}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedScan(scan);
                            setIsSheetOpen(true);
                          }}
                          className="secondary-action"
                        >
                          <ChevronRight aria-hidden="true" className="w-4 h-4" />
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
        <div className="scan-grid">
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
                aria-label={`Inspect ${scanLabel(scan)}`}
                onKeyDown={(event) => { if (event.target === event.currentTarget && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); event.currentTarget.click(); } }}
                onClick={() => {
                  setSelectedScan(scan);
                  setIsSheetOpen(true);
                }}
                className="min-w-0 bg-card border border-border rounded-xl p-4 hover:border-[#800000] transition-colors cursor-pointer space-y-3 flex flex-col justify-between"
              >
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
                    <span className="font-mono font-bold text-xs text-slate-700">
                      {Number.isFinite(scan.sequence_number) ? `#${scan.sequence_number!.toString().padStart(3, '0')}` : '—'}
                    </span>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge type="fertility" value={scan.final_class} />
                      {scan.routing_action === 'MANUAL_REVIEW' && <Badge value="MANUAL_REVIEW" size="sm" />}
                      {Number.isFinite(scan.confidence) && scan.confidence < 0.75 && <span className="status-badge status-neutral">Low confidence</span>}
                      {scan.is_overridden && <Badge value="OVERRIDDEN" size="sm" />}
                    </div>
                  </div>

                  <div className="mt-2">
                    <CandlingAperture
                      imageUrl={scan.thumbnail_url || scan.image_url}
                      finalClass={scan.final_class}
                      confidence={Number.isFinite(scan.confidence) ? scan.confidence : undefined}
                      inferenceMs={Number.isFinite(scan.inference_ms) ? scan.inference_ms : undefined}
                    />
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                  <span className="min-w-0 break-all">{scan.batch_id || 'N/A'}</span>
                  <span className="font-bold text-slate-700">Confidence: {Number.isFinite(scan.confidence) ? `${(scan.confidence * 100).toFixed(0)}%` : '—'}</span>
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
            className="secondary-action"
          >
            <ChevronLeft aria-hidden="true" className="w-4 h-4" />
          </button>
          <span className="px-2 font-bold text-slate-800">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            aria-label="Next page"
            disabled={isLoading || currentPage === totalPages}
            className="secondary-action"
          >
            <ChevronRight aria-hidden="true" className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Scan Details & Human-in-the-Loop Override Drawer (Sheet) */}
      <Sheet
        isOpen={isSheetOpen}
        onClose={() => setIsSheetOpen(false)}
        title={selectedScan ? `Candling ${scanLabel(selectedScan)}` : ''}
        description={selectedScan ? `Batch: ${selectedScan.batch_id || 'N/A'} • UUID: ${selectedScan.scan_id}` : ''}
      >
        {selectedScan && (
          <div className="min-w-0 space-y-4 text-sm break-words">
            {/* Visual Candling Aperture */}
            <CandlingAperture
              imageUrl={selectedScan.image_url || selectedScan.thumbnail_url}
              finalClass={selectedScan.final_class}
              confidence={Number.isFinite(selectedScan.confidence) ? selectedScan.confidence : undefined}
              inferenceMs={Number.isFinite(selectedScan.inference_ms) ? selectedScan.inference_ms : undefined}
              sequenceNumber={selectedScan.sequence_number}
              batchId={selectedScan.batch_id}
              aspectRatio={selectedScan.aspect_ratio}
            />

            {/* Decision card */}
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-bold text-slate-800">Conveyor Routing Action:</span>
                <span
                  className={`font-bold ${
                    selectedScan.routing_action === 'MANUAL_REVIEW' ? 'text-amber-800' : selectedScan.routing_action === 'ACCEPT' ? 'text-emerald-800' : selectedScan.routing_action === 'REJECT' ? 'text-rose-800' : 'text-slate-600'
                  }`}
                >
                  {selectedScan.routing_action === 'MANUAL_REVIEW' ? 'MANUAL REVIEW (Operator Inspection)' : selectedScan.routing_action === 'ACCEPT' ? 'ACCEPT (Incubation Tray)' : selectedScan.routing_action === 'REJECT' ? 'REJECT (Diverter Eject)' : 'Routing unavailable'}
                </span>
              </div>
              <p className="text-slate-600 text-[11px]">
                {selectedScan.routing_action === 'MANUAL_REVIEW'
                  ? 'The saved routing action requests operator inspection.'
                  : selectedScan.routing_action === 'ACCEPT'
                  ? 'The saved routing action requests retention for incubation.'
                  : selectedScan.routing_action === 'REJECT'
                  ? 'The saved routing action requests diversion to the Penoy salvage tray.'
                  : 'No conveyor routing action was recorded for this scan.'}
              </p>
              {selectedScan.is_overridden && (
                <div className="mt-2 pt-2 border-t border-slate-200 text-[11px] text-purple-900 font-medium">
                  <span className="font-bold">Human Override:</span> {selectedScan.override_reason || 'Override reason unavailable'}
                </div>
              )}
            </div>

            {/* Human-in-the-Loop Override Section */}
            <div className="p-3.5 bg-amber-50 border border-amber-300 rounded-lg space-y-2.5">
              <div className="flex items-center gap-1.5 font-bold text-amber-950">
                <Edit3 aria-hidden="true" className="w-4 h-4 text-amber-800" />
                <span>Human-in-the-Loop Override:</span>
              </div>

              <p className="text-[11px] text-amber-900 font-medium">
                If the automated YOLOv8 model made a false classification, re-annotate below. This updates the batch yield and logs an immutable audit event.
              </p>

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => handlePromptOverride('FERTILE')}
                  className={`secondary-action ${
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
                  className={`secondary-action ${
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
              {Array.isArray(selectedScan.detections) && selectedScan.detections.length > 0 ? (
                <pre className="p-3 rounded-lg bg-slate-900 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-32">
                  {JSON.stringify(selectedScan.detections, null, 2)}
                </pre>
              ) : (
                <p className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-600">Detection telemetry unavailable. No raw detections were recorded for this scan.</p>
              )}
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
