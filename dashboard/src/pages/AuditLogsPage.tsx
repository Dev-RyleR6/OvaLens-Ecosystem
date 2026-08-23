import React, { useState, useEffect, useMemo } from 'react';
import {
  FileText,
  Search,
  Clock,
  ChevronRight,
  ChevronLeft,
  AlertTriangle,
  Info,
  Shield,
  ShieldAlert,
  ArrowUpDown,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { AuditLog } from '../types';
import { Sheet } from '../components/ui/sheet';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { EmptyState } from '../components/ui/EmptyState';

type SortField = 'log_id' | 'action' | 'created_at';
type SortOrder = 'asc' | 'desc';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [entityFilter, setEntityFilter] = useState<string>('ALL');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  // Sorting & Pagination
  const [sortField, setSortField] = useState<SortField>('log_id');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const fetchLogs = async () => {
    setIsLoading(true);
    setIsError(false);
    try {
      const data = await apiClient.getAuditLogs({ limit: 100 });
      setLogs(data || []);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  // Filtered & Sorted Logs
  const processedLogs = useMemo(() => {
    let result = [...logs];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (l) =>
          l.action.toLowerCase().includes(q) ||
          l.entity_id.toLowerCase().includes(q) ||
          (l.operator_name && l.operator_name.toLowerCase().includes(q))
      );
    }

    if (actionFilter !== 'ALL') {
      result = result.filter((l) => l.action === actionFilter);
    }

    if (severityFilter !== 'ALL') {
      result = result.filter((l) => l.severity === severityFilter);
    }

    if (entityFilter !== 'ALL') {
      result = result.filter((l) => l.entity_type === entityFilter);
    }

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
  }, [logs, searchQuery, actionFilter, severityFilter, entityFilter, sortField, sortOrder]);

  const paginatedLogs = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return processedLogs.slice(start, start + rowsPerPage);
  }, [processedLogs, currentPage, rowsPerPage]);

  const totalPages = Math.ceil(processedLogs.length / rowsPerPage) || 1;

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            System Audit Trail & Security Logs
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable system event logs, operator stage transitions, device calibrations, and security activity.
          </p>
        </div>

        <span className="text-xs font-semibold text-slate-700 bg-slate-100 px-3 py-1 rounded-md border border-slate-200">
          PostgreSQL WAL Traceability Active
        </span>
      </div>

      {/* Enterprise Filter Toolbar */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search action, entity ID, or operator..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#800000] shadow-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-600 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg">
              {processedLogs.length} events logged
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Action Types</option>
            <option value="BATCH_STAGE_ADVANCED">BATCH_STAGE_ADVANCED</option>
            <option value="DEVICE_CALIBRATION_UPDATED">DEVICE_CALIBRATION_UPDATED</option>
            <option value="PDF_REPORT_GENERATED">PDF_REPORT_GENERATED</option>
            <option value="USER_LOGIN_SUCCESS">USER_LOGIN_SUCCESS</option>
            <option value="BATCH_INITIALIZED">BATCH_INITIALIZED</option>
            <option value="MANUAL_CLASSIFICATION_OVERRIDE">MANUAL_CLASSIFICATION_OVERRIDE</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Severities</option>
            <option value="INFO">Info Events</option>
            <option value="WARNING">Warning Events</option>
            <option value="SECURITY">Security Events</option>
          </select>

          <select
            value={entityFilter}
            onChange={(e) => {
              setEntityFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Entity Types</option>
            <option value="BATCH">Batch Entity</option>
            <option value="DEVICE">Device Entity</option>
            <option value="SCAN">Scan Entity</option>
            <option value="AUTH">Auth Entity</option>
            <option value="SYSTEM">System Entity</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      {isError && logs.length === 0 ? (
        <DataUnavailableState
          title="Audit Trail Service Offline"
          description="Unable to connect to the PostgreSQL audit log engine. Ensure the backend REST service is active."
          onRetry={fetchLogs}
          isRetrying={isLoading}
        />
      ) : !isLoading && processedLogs.length === 0 ? (
        <EmptyState
          title="No Audit Records Found"
          description="No security or operational audit records match your filter criteria."
        />
      ) : (
        <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th
                  className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                  onClick={() => toggleSort('log_id')}
                >
                  <div className="flex items-center gap-1.5">
                    <span>Event ID</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th
                  className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                  onClick={() => toggleSort('action')}
                >
                  <div className="flex items-center gap-1.5">
                    <span>Action Type</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="py-3 px-4">Entity</th>
                <th className="py-3 px-4">Actor / Operator</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">IP Address</th>
                <th
                  className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                  onClick={() => toggleSort('created_at')}
                >
                  <div className="flex items-center gap-1.5">
                    <span>Timestamp</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedLogs.map((log) => (
                <tr
                  key={log.log_id}
                  className="hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => setSelectedLog(log)}
                >
                  <td className="py-3 px-4 font-mono font-bold text-slate-500">#{log.log_id}</td>
                  <td className="py-3 px-4">
                    <span className="font-semibold text-[#0F172A] font-mono text-xs bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-700 font-mono text-xs">{log.entity_id}</td>
                  <td className="py-3 px-4 text-slate-800 font-medium">
                    {log.operator_name || 'Automated Sorter'}
                  </td>
                  <td className="py-3 px-4">
                    {log.severity === 'SECURITY' ? (
                      <span className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold text-rose-800 bg-rose-50 w-24 py-1 rounded-md border border-rose-200">
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                        Security
                      </span>
                    ) : log.severity === 'WARNING' ? (
                      <span className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold text-amber-900 bg-amber-50 w-24 py-1 rounded-md border border-amber-200">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                        Warning
                      </span>
                    ) : (
                      <span className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 w-24 py-1 rounded-md border border-slate-200">
                        <Info className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        Info
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-500 text-[11px]">{log.ip_address || '127.0.0.1'}</td>
                  <td className="py-3 px-4 text-slate-500 font-medium">
                    {new Date(log.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="p-1 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 pt-2">
        <div className="flex items-center gap-2">
          <span>Showing {paginatedLogs.length} of {processedLogs.length} events</span>
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

      {/* Log Detail Drawer (Sheet) */}
      <Sheet
        isOpen={Boolean(selectedLog)}
        onClose={() => setSelectedLog(null)}
        title={selectedLog ? `Audit Event #${selectedLog.log_id}` : ''}
        description={selectedLog ? `Action: ${selectedLog.action} • Timestamp: ${new Date(selectedLog.created_at).toISOString()}` : ''}
      >
        {selectedLog && (
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">Action:</span>
                <span className="font-bold text-slate-900 font-mono">{selectedLog.action}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Target Entity:</span>
                <span className="font-bold text-slate-900 font-mono">{selectedLog.entity_id} ({selectedLog.entity_type})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Actor:</span>
                <span className="font-bold text-slate-900">{selectedLog.operator_name || 'Automated Daemon'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">IP Address:</span>
                <span className="font-mono text-slate-900">{selectedLog.ip_address || '127.0.0.1'}</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="font-bold text-slate-800 block">Event Payload (JSON)</span>
              <pre className="p-3 bg-slate-900 text-emerald-400 font-mono text-xs rounded-lg overflow-x-auto max-h-56">
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Sheet>
    </div>
  );
};
