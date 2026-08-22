import React, { useState, useEffect, useMemo } from 'react';
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
  Volume2,
  VolumeX,
  RefreshCw,
  Layers,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { EggScan, FertilityClass, BatchSummary } from '../types';
import { Badge } from '../components/Badge';
import { CandlingAperture } from '../components/CandlingAperture';
import { Sheet } from '../components/ui/sheet';

type ViewMode = 'TABLE' | 'GRID';
type SortField = 'sequence_number' | 'confidence' | 'inference_ms' | 'scanned_at';
type SortOrder = 'asc' | 'desc';

// Acoustic feedback synthesis via HTML5 Web Audio API
const playAcousticFeedback = (isAccept: boolean) => {
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;
    const audioCtx = new AudioContextClass();
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = isAccept ? 'sine' : 'triangle';
    osc.frequency.setValueAtTime(isAccept ? 880 : 330, audioCtx.currentTime); // High pitch for Fertile, low for Cull
    gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.08);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.08);
  } catch (e) {
    // Audio context may be restricted before user gesture
  }
};

export const ScanExplorerPage: React.FC = () => {
  const [scans, setScans] = useState<EggScan[]>([]);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('TABLE');
  const [selectedScan, setSelectedScan] = useState<EggScan | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Filters
  const [classFilter, setClassFilter] = useState<string>('ALL');
  const [batchFilter, setBatchFilter] = useState<string>('ALL');
  const [confidenceFilter, setConfidenceFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Sorting & Pagination
  const [sortField, setSortField] = useState<SortField>('sequence_number');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Live Auto-Refresh & Audio Toggles
  const [isLiveAutoRefresh, setIsLiveAutoRefresh] = useState(false);
  const [isSoundEnabled, setIsSoundEnabled] = useState(true);

  const [overrideToast, setOverrideToast] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState('Visual confirmation by operator');

  const fetchScans = async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.getScans({
        final_class: classFilter === 'ALL' ? undefined : classFilter,
        batch_id: batchFilter === 'ALL' ? undefined : batchFilter,
        limit: 100
      });
      if (Array.isArray(data)) {
        setScans(data);
      } else {
        setScans([]);
      }
    } catch (err) {
      console.error('Error fetching scans:', err);
    } finally {
      setIsLoading(false);
    }
  };

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
    fetchScans();
  }, [classFilter, batchFilter]);

  // Live Ingest Auto-Refresh interval (3s)
  useEffect(() => {
    if (!isLiveAutoRefresh) return;
    const interval = setInterval(() => {
      fetchScans();
    }, 3000);
    return () => clearInterval(interval);
  }, [isLiveAutoRefresh, classFilter, batchFilter]);

  const handleOverride = async (newClass: FertilityClass) => {
    if (!selectedScan) return;
    try {
      const updated = await apiClient.overrideScanClassification(selectedScan.scan_id, newClass, overrideReason);
      setSelectedScan({ ...updated });
      fetchScans();
      if (isSoundEnabled) {
        playAcousticFeedback(newClass === 'FERTILE');
      }
      setOverrideToast(`Scan #${selectedScan.sequence_number ?? 0} reclassified to ${newClass}. Logged in Audit Trail.`);
      setTimeout(() => setOverrideToast(null), 3500);
    } catch (err) {
      console.error('Error overriding scan:', err);
    }
  };

  // Filtered & Sorted Scans
  const processedScans = useMemo(() => {
    let result = Array.isArray(scans) ? [...scans] : [];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          (s.scan_id || '').toLowerCase().includes(q) ||
          (s.sequence_number !== undefined && s.sequence_number !== null && s.sequence_number.toString().includes(q)) ||
          (s.batch_id || '').toLowerCase().includes(q)
      );
    }

    if (confidenceFilter === 'HIGH') {
      result = result.filter((s) => (s.confidence ?? 0) >= 0.90);
    } else if (confidenceFilter === 'MEDIUM') {
      result = result.filter((s) => (s.confidence ?? 0) >= 0.80 && (s.confidence ?? 0) < 0.90);
    } else if (confidenceFilter === 'LOW') {
      result = result.filter((s) => (s.confidence ?? 0) < 0.80);
    }

    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (aVal === undefined || aVal === null) return sortOrder === 'asc' ? 1 : -1;
      if (bVal === undefined || bVal === null) return sortOrder === 'asc' ? -1 : 1;

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
  }, [scans, searchQuery, confidenceFilter, sortField, sortOrder]);

  const paginatedScans = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return processedScans.slice(start, start + rowsPerPage);
  }, [processedScans, currentPage, rowsPerPage]);

  const totalPages = Math.max(1, Math.ceil(processedScans.length / rowsPerPage));

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  // Combine known batch IDs from batch list and scans for dropdown
  const batchOptions = useMemo(() => {
    const set = new Set<string>();
    batches.forEach(b => { if (b.batch_id) set.add(b.batch_id); if (b.batch_code) set.add(b.batch_code); });
    scans.forEach(s => { if (s.batch_id) set.add(s.batch_id); });
    return Array.from(set);
  }, [batches, scans]);

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Candling Scan Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Browse verified duck egg transillumination scans, optical metrics, and human-in-the-loop overrides.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Live Auto-Refresh Button */}
          <button
            onClick={() => setIsLiveAutoRefresh(prev => !prev)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer ${
              isLiveAutoRefresh
                ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
            title="Auto-refresh scan feed every 3 seconds"
          >
            <span className={`w-2 h-2 rounded-full ${isLiveAutoRefresh ? 'bg-emerald-600 animate-pulse' : 'bg-slate-400'}`} />
            <span>{isLiveAutoRefresh ? 'Live Ingest (3s)' : 'Live Ingest: Off'}</span>
          </button>

          {/* Sound Toggle */}
          <button
            onClick={() => setIsSoundEnabled(prev => !prev)}
            className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
              isSoundEnabled ? 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50' : 'bg-slate-100 border-slate-200 text-slate-400'
            }`}
            title={isSoundEnabled ? "Sound Enabled" : "Sound Muted"}
          >
            {isSoundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>

          <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
            {processedScans.length} scans
          </span>
        </div>
      </div>

      {overrideToast && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs font-semibold text-amber-900 flex items-center gap-2 shadow-xs">
          <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0" />
          <span>{overrideToast}</span>
        </div>
      )}

      {/* Enterprise Filter Toolbar */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search # seq, batch, or UUID..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] shadow-xs"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 self-end sm:self-auto">
            <button
              onClick={() => setViewMode('TABLE')}
              className={`p-1.5 rounded text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors ${
                viewMode === 'TABLE' ? 'bg-white text-[#800000] shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Table View"
            >
              <List className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
            <button
              onClick={() => setViewMode('GRID')}
              className={`p-1.5 rounded text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors ${
                viewMode === 'GRID' ? 'bg-white text-[#800000] shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Aperture Grid Cards View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Grid</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          <select
            value={classFilter}
            onChange={(e) => {
              setClassFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Classes</option>
            <option value="FERTILE">Fertile (Accept)</option>
            <option value="INFERTILE">Infertile (Penoy)</option>
            <option value="ABNORMAL">Abnormal (Dead)</option>
          </select>

          <select
            value={batchFilter}
            onChange={(e) => {
              setBatchFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Batches</option>
            {batchOptions.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>

          <select
            value={confidenceFilter}
            onChange={(e) => {
              setConfidenceFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Confidence Scores</option>
            <option value="HIGH">High Confidence (≥ 90%)</option>
            <option value="MEDIUM">Medium Confidence (80% - 89%)</option>
            <option value="LOW">Low Confidence (&lt; 80%)</option>
          </select>
        </div>
      </div>

      {/* View Mode: Table vs Grid */}
      {viewMode === 'TABLE' ? (
        <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
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
                    onClick={() => toggleSort('confidence')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>YOLOv8 FP16 Conf</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => toggleSort('inference_ms')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Inference</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Diverter Action</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
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
                      className="hover:bg-slate-50 transition-colors cursor-pointer"
                      onClick={() => setSelectedScan(scan)}
                    >
                      <td className="py-3 px-4 font-mono font-bold text-slate-700">
                        #{((scan.sequence_number ?? 0)).toString().padStart(3, '0')}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900">{scan.batch_id || 'N/A'}</td>
                      <td className="py-3 px-4">
                        <Badge type="fertility" value={scan.final_class || 'FERTILE'} />
                      </td>
                      <td className="py-3 px-4 font-extrabold text-slate-900">
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
                          ? new Date(scan.scanned_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })
                          : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedScan(scan);
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
            <div className="col-span-full py-12 text-center text-slate-400 bg-white rounded-xl border border-slate-200">
              No matching candling scans found.
            </div>
          ) : (
            paginatedScans.map((scan) => (
              <div
                key={scan.scan_id}
                onClick={() => setSelectedScan(scan)}
                className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-xs hover:border-[#800000] transition-colors cursor-pointer space-y-3 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="font-mono font-bold text-xs text-slate-700">
                      #{((scan.sequence_number ?? 0)).toString().padStart(3, '0')}
                    </span>
                    <Badge type="fertility" value={scan.final_class || 'FERTILE'} />
                  </div>

                  <div className="mt-2">
                    <CandlingAperture
                      finalClass={scan.final_class}
                      confidence={scan.confidence ?? 0.95}
                      inferenceMs={scan.inference_ms ?? 25.0}
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

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 pt-2">
        <div className="flex items-center gap-2">
          <span>Showing {paginatedScans.length} of {processedScans.length} verified scans</span>
          <span>•</span>
          <span>Rows per page:</span>
          <select
            value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="h-8 px-2 bg-white border border-slate-200 rounded text-slate-700 focus:outline-none focus:border-[#800000] cursor-pointer"
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

      {/* Scan Details & Human-in-the-Loop Override Drawer (Sheet) */}
      <Sheet
        isOpen={Boolean(selectedScan)}
        onClose={() => setSelectedScan(null)}
        title={selectedScan ? `Candling Scan #${selectedScan.sequence_number ?? 0}` : ''}
        description={selectedScan ? `Batch: ${selectedScan.batch_id || 'N/A'} • UUID: ${selectedScan.scan_id}` : ''}
      >
        {selectedScan && (
          <div className="space-y-4 text-xs">
            {/* Visual Candling Aperture */}
            <CandlingAperture
              finalClass={selectedScan.final_class}
              confidence={selectedScan.confidence ?? 0.95}
              inferenceMs={selectedScan.inference_ms ?? 25.0}
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
                  ? 'Viable spider embryo network verified. Accepted to Day 18 hatcher tray.'
                  : selectedScan.final_class === 'INFERTILE'
                  ? 'Clear unfertilized yolk. Diverted to Penoy food salvage tray @ ₱14.00.'
                  : 'Dead embryo or corrupted yolk. Culled to prevent incubator burst.'}
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
                  onClick={() => handleOverride('FERTILE')}
                  className={`px-2.5 py-1 text-xs font-bold rounded border transition-colors cursor-pointer ${
                    selectedScan.final_class === 'FERTILE'
                      ? 'bg-emerald-700 text-white border-emerald-800'
                      : 'bg-white text-emerald-800 border-emerald-300 hover:bg-emerald-50'
                  }`}
                >
                  Override to FERTILE
                </button>

                <button
                  type="button"
                  onClick={() => handleOverride('INFERTILE')}
                  className={`px-2.5 py-1 text-xs font-bold rounded border transition-colors cursor-pointer ${
                    selectedScan.final_class === 'INFERTILE'
                      ? 'bg-amber-700 text-white border-amber-800'
                      : 'bg-white text-amber-900 border-amber-300 hover:bg-amber-50'
                  }`}
                >
                  Override to PENOY
                </button>

                <button
                  type="button"
                  onClick={() => handleOverride('ABNORMAL')}
                  className={`px-2.5 py-1 text-xs font-bold rounded border transition-colors cursor-pointer ${
                    selectedScan.final_class === 'ABNORMAL'
                      ? 'bg-rose-700 text-white border-rose-800'
                      : 'bg-white text-rose-800 border-rose-300 hover:bg-rose-50'
                  }`}
                >
                  Override to DEAD
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
    </div>
  );
};
