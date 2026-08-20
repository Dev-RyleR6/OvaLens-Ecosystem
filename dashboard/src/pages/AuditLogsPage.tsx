import React, { useState, useEffect } from 'react';
import {
  FileText,
  Search,
  Filter,
  Shield,
  Clock,
  Terminal,
  ChevronRight,
  User,
  Activity,
  AlertTriangle,
  Info,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { AuditLog } from '../types';
import { Sheet } from '../components/ui/sheet';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = async () => {
    const data = await apiClient.getAuditLogs();
    setLogs(data);
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const filteredLogs = logs.filter((l) => {
    const matchSearch = l.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        l.entity_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (l.operator_name && l.operator_name.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchAction = actionFilter === 'ALL' || l.action === actionFilter;
    return matchSearch && matchAction;
  });

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

        <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
          PostgreSQL WAL Traceability Active
        </span>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search action, entity ID, or operator..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#800000] shadow-xs"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Actions</option>
            <option value="BATCH_STAGE_ADVANCED">Batch Advanced</option>
            <option value="DEVICE_CALIBRATION_UPDATED">Calibration Updated</option>
            <option value="PDF_REPORT_GENERATED">PDF Generated</option>
            <option value="USER_LOGIN_SUCCESS">User Login</option>
            <option value="BATCH_INITIALIZED">Batch Initialized</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Event ID</th>
                <th className="py-3 px-4">Action Type</th>
                <th className="py-3 px-4">Entity</th>
                <th className="py-3 px-4">Actor / Operator</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">IP Address</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLogs.map((log) => (
                <tr
                  key={log.log_id}
                  className="hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => setSelectedLog(log)}
                >
                  <td className="py-3 px-4 font-mono font-bold text-slate-500">#{log.log_id}</td>
                  <td className="py-3 px-4">
                    <span className="font-bold text-[#0F172A] font-mono text-[11px] bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-700 font-mono text-[11px]">{log.entity_id}</td>
                  <td className="py-3 px-4 text-slate-800 font-medium">
                    {log.operator_name || 'Automated Sorter'}
                  </td>
                  <td className="py-3 px-4">
                    {log.severity === 'WARNING' ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                        <AlertTriangle className="w-3 h-3" />
                        Warning
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        <Info className="w-3 h-3 text-slate-500" />
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
                      className="p-1 rounded text-slate-400 hover:text-slate-700"
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
