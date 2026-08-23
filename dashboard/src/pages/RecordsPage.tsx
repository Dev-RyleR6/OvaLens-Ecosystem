import React, { useState, useEffect, useMemo } from 'react';
import {
  Archive,
  Search,
  Download,
  Calendar,
  Layers,
  Coins,
  CheckCircle2,
  TrendingUp,
  LayoutGrid,
  List,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Award,
  Clock,
  User,
  Zap,
  SlidersHorizontal,
  CheckSquare,
  Square,
  FileSpreadsheet,
} from 'lucide-react';
import { apiClient } from '../api/client';
import {
  BatchSummary,
  PenoySalvageRecord,
  HistoricalRecordSummary,
  CandlingSession,
  DuckBreed,
} from '../types';
import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';
import { CandlingCertificateModal } from '../components/CandlingCertificateModal';
import { Sheet } from '../components/ui/sheet';

type ViewMode = 'TABLE' | 'GRID';
type TabType = 'BATCHES' | 'SALVAGE' | 'SESSIONS';
type SortField = 'batch_code' | 'set_date' | 'initial_egg_count' | 'fertility_rate' | 'hatchability_rate';
type SortOrder = 'asc' | 'desc';

export const RecordsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('BATCHES');
  const [viewMode, setViewMode] = useState<ViewMode>('TABLE');
  const [summary, setSummary] = useState<HistoricalRecordSummary | null>(null);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [salvageRecords, setSalvageRecords] = useState<PenoySalvageRecord[]>([]);
  const [sessions, setSessions] = useState<CandlingSession[]>([]);

  // Enterprise Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [breedFilter, setBreedFilter] = useState<string>('ALL');
  const [fertilityFilter, setFertilityFilter] = useState<string>('ALL');
  const [dateRangePreset, setDateRangePreset] = useState<string>('ALL_TIME');
  
  // Sorting & Pagination States
  const [sortField, setSortField] = useState<SortField>('set_date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Selection for Bulk Actions
  const [selectedBatchIds, setSelectedBatchIds] = useState<string[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isCertificateOpen, setIsCertificateOpen] = useState(false);
  const [certificateBatch, setCertificateBatch] = useState<BatchSummary | null>(null);

  useEffect(() => {
    const fetchRecords = async () => {
      try {
        const [bData, sessData] = await Promise.all([
          apiClient.getBatches(),
          apiClient.getSessions(),
        ]);
        setBatches(bData || []);
        setSessions(sessData || []);
      } catch (err) {
        console.error("Error fetching records:", err);
      }
    };
    fetchRecords();
  }, []);

  // Filtered and Sorted Batches
  const processedBatches = useMemo(() => {
    let result = [...batches];

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (b) =>
          b.batch_code.toLowerCase().includes(q) ||
          b.breed.toLowerCase().includes(q) ||
          b.incubator_id.toLowerCase().includes(q)
      );
    }

    // Breed filter
    if (breedFilter !== 'ALL') {
      result = result.filter((b) => b.breed === breedFilter);
    }

    // Fertility rate filter
    if (fertilityFilter === 'HIGH') {
      result = result.filter((b) => b.fertility_rate >= 90);
    } else if (fertilityFilter === 'STANDARD') {
      result = result.filter((b) => b.fertility_rate >= 80 && b.fertility_rate < 90);
    } else if (fertilityFilter === 'LOW') {
      result = result.filter((b) => b.fertility_rate > 0 && b.fertility_rate < 80);
    }

    // Sorting
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
  }, [batches, searchQuery, breedFilter, fertilityFilter, sortField, sortOrder]);

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

  const handleOpenCertificate = (b: BatchSummary, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setCertificateBatch(b);
    setIsCertificateOpen(true);
  };

  const handleExportBulkCSV = () => {
    const toExport = selectedBatchIds.length > 0
      ? batches.filter((b) => selectedBatchIds.includes(b.batch_id))
      : batches;

    const csvContent =
      "data:text/csv;charset=utf-8," +
      "BatchCode,Breed,Incubator,InitialSet,Fertile,Penoy,Dead,FertilityRate,HatchabilityRate,SetDate\n" +
      toExport
        .map(
          (b) =>
            `${b.batch_code},${b.breed},${b.incubator_id},${b.initial_egg_count},${b.fertile_count},${b.infertile_count},${b.abnormal_count},${b.fertility_rate}%,${b.hatchability_rate}%,${b.set_date}`
        )
        .join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `OvaLens_Records_Export_${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Candling & Hatchery Historical Records
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Enterprise archives of past candling cohorts, commercial Penoy food salvage, and operator shift sessions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {selectedBatchIds.length > 0 && (
            <span className="text-xs font-semibold text-slate-700 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
              {selectedBatchIds.length} batches selected
            </span>
          )}

          <button
            onClick={handleExportBulkCSV}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>
              {selectedBatchIds.length > 0
                ? `Export Selected (${selectedBatchIds.length})`
                : "Export All Archives (CSV)"}
            </span>
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

      {/* Enterprise Control Toolbar: Tabs, Views, and Filters */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-xs space-y-3.5">
        {/* Top Strip: Tabs & View Mode */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
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
              Shift Logs ({sessions.length})
            </button>
          </div>

          {/* View Switcher (Table vs Grid) */}
          {activeTab === 'BATCHES' && (
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 self-end sm:self-auto">
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
                title="Grid / Cards View"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span>Grid</span>
              </button>
            </div>
          )}
        </div>

        {/* Filter & Search Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 text-xs">
          {/* Search Box */}
          <div className="sm:col-span-5 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by batch code, breed, or incubator unit..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 pl-9 pr-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000] shadow-xs"
            />
          </div>

          {/* Breed Facet Filter */}
          <div className="sm:col-span-3">
            <select
              value={breedFilter}
              onChange={(e) => {
                setBreedFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
            >
              <option value="ALL">All Duck Breeds</option>
              <option value="KAYUMANGGI">Kayumanggi</option>
              <option value="ITIM">Itim (Native)</option>
              <option value="KHAKI">Khaki Campbell</option>
            </select>
          </div>

          {/* Fertility Rate Threshold Filter */}
          <div className="sm:col-span-4">
            <select
              value={fertilityFilter}
              onChange={(e) => {
                setFertilityFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
            >
              <option value="ALL">All Fertility Yields</option>
              <option value="HIGH">High Yield (≥ 90% Fertile)</option>
              <option value="STANDARD">Standard Yield (80% - 89%)</option>
              <option value="LOW">Below Standard (&lt; 80%)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tab 1: Batch Candling Archives */}
      {activeTab === 'BATCHES' && (
        <>
          {viewMode === 'TABLE' ? (
            /* Enterprise Table View */
            <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4 w-10 text-center">
                        <button
                          onClick={toggleSelectAll}
                          className="text-slate-400 hover:text-slate-700 cursor-pointer"
                        >
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
                      <th className="py-3 px-4">Breed</th>
                      <th
                        className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                        onClick={() => toggleSort('set_date')}
                      >
                        <div className="flex items-center gap-1.5">
                          <span>Set Date</span>
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                        onClick={() => toggleSort('initial_egg_count')}
                      >
                        <div className="flex items-center gap-1.5">
                          <span>Initial Eggs</span>
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        </div>
                      </th>
                      <th className="py-3 px-4">Fertile</th>
                      <th className="py-3 px-4">Penoy (₱14)</th>
                      <th className="py-3 px-4">Dead</th>
                      <th
                        className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                        onClick={() => toggleSort('fertility_rate')}
                      >
                        <div className="flex items-center gap-1.5">
                          <span>Fertility %</span>
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                        onClick={() => toggleSort('hatchability_rate')}
                      >
                        <div className="flex items-center gap-1.5">
                          <span>Hatch %</span>
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        </div>
                      </th>
                      <th className="py-3 px-4 text-right">Certificate & Actions</th>
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
                          onClick={() => {
                            setSelectedBatch(b);
                            setIsDrawerOpen(true);
                          }}
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
                            <span className="text-[10px] text-slate-400 font-mono block mt-0.5">{b.incubator_id}</span>
                          </td>
                          <td className="py-3 px-4 font-semibold text-slate-700">{b.breed}</td>
                          <td className="py-3 px-4 text-slate-500 font-medium">{new Date(b.set_date).toLocaleDateString()}</td>
                          <td className="py-3 px-4 text-slate-800 font-bold">{b.initial_egg_count}</td>
                          <td className="py-3 px-4 text-emerald-700 font-bold">{b.fertile_count}</td>
                          <td className="py-3 px-4 text-amber-700 font-bold">{b.infertile_count}</td>
                          <td className="py-3 px-4 text-red-700 font-bold">{b.abnormal_count}</td>
                          <td className="py-3 px-4 font-extrabold text-slate-900">
                            {b.fertility_rate > 0 ? (
                              <span className={b.fertility_rate >= 90 ? 'text-emerald-700' : 'text-slate-800'}>
                                {b.fertility_rate}%
                              </span>
                            ) : (
                              'Pending'
                            )}
                          </td>
                          <td className="py-3 px-4 font-bold text-slate-900">
                            {b.hatchability_rate > 0 ? `${b.hatchability_rate}%` : '—'}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                              <button
                                onClick={(e) => handleOpenCertificate(b, e)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold rounded bg-maroon-50 hover:bg-maroon-100 text-[#800000] border border-maroon-200 transition-colors cursor-pointer"
                                title="View Quality Certificate"
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
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            /* Enterprise Grid / Card View */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {paginatedBatches.map((b) => (
                <div
                  key={b.batch_id}
                  onClick={() => {
                    setSelectedBatch(b);
                    setIsDrawerOpen(true);
                  }}
                  className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs hover:border-[#800000] hover-lift transition-all cursor-pointer space-y-4 flex flex-col justify-between"
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

                    {/* Stats */}
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
                      <span>Fertility Rate:</span>
                      <strong className="text-emerald-700 text-sm">{b.fertility_rate}%</strong>
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

          {/* Enterprise Pagination Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 pt-2">
            <div className="flex items-center gap-2">
              <span>Showing {paginatedBatches.length} of {processedBatches.length} records</span>
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
        </>
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
                {salvageRecords.map((sal) => (
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
                {sessions.map((sess) => (
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

      {/* Batch Inspection Sheet Drawer */}
      <Sheet
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedBatch ? `Batch Record: ${selectedBatch.batch_code}` : ''}
        description="Historical incubation and candling performance record"
      >
        {selectedBatch && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-2 bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div>
                <span className="text-slate-500 block">Breed:</span>
                <strong className="text-slate-900">{selectedBatch.breed}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Incubator:</span>
                <strong className="text-slate-900">{selectedBatch.incubator_id}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Initial Egg Set:</span>
                <strong className="text-slate-900">{selectedBatch.initial_egg_count} eggs</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Fertility Rate:</span>
                <strong className="text-emerald-700">{selectedBatch.fertility_rate}%</strong>
              </div>
            </div>

            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg space-y-1">
              <span className="font-bold text-emerald-950 block">Classification Breakdown</span>
              <p className="text-[11px] text-emerald-800">
                • <strong>{selectedBatch.fertile_count}</strong> Fertile Embryos (Transferred to Day 18 Hatcher)<br/>
                • <strong>{selectedBatch.infertile_count}</strong> Penoy Salvaged (@ ₱14.00 = ₱{(selectedBatch.infertile_count * 14.0).toFixed(2)})<br/>
                • <strong>{selectedBatch.abnormal_count}</strong> Abnormal/Dead Culled
              </p>
            </div>

            <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-200">
              <button
                onClick={() => handleOpenCertificate(selectedBatch)}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-bold rounded-lg bg-[#800000] text-white hover:bg-[#6B0000] transition-colors cursor-pointer"
              >
                <Award className="w-3.5 h-3.5" />
                <span>Open Certificate</span>
              </button>
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
    </div>
  );
};
