import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Grid,
  List,
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Zap,
  Clock
} from 'lucide-react';
import { apiClient } from '../api/client';
import { EggScan, FertilityClass } from '../types';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';

export const ScanExplorerPage: React.FC = () => {
  const [scans, setScans] = useState<EggScan[]>([]);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [classFilter, setClassFilter] = useState<string>('ALL');
  const [batchFilter, setBatchFilter] = useState<string>('ALL');
  const [selectedScan, setSelectedScan] = useState<EggScan | null>(null);

  const fetchScans = async () => {
    const data = await apiClient.getScans({
      final_class: classFilter === 'ALL' ? undefined : classFilter,
      batch_id: batchFilter === 'ALL' ? undefined : batchFilter,
      limit: 60
    });
    setScans(data);
  };

  useEffect(() => {
    fetchScans();
  }, [classFilter, batchFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Candling Scan Explorer</h2>
          <p className="text-xs text-slate-400">High-resolution egg inspection records, bounding boxes, and routing metrics</p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 p-1 bg-[#1E293B] border border-slate-800 rounded-lg">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              viewMode === 'grid' ? 'bg-[#800000] text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Grid className="w-3.5 h-3.5" /> Grid
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`p-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              viewMode === 'table' ? 'bg-[#800000] text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <List className="w-3.5 h-3.5" /> Table
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5" /> Filter By:
          </div>
          <select
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value)}
            className="bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#800000]"
          >
            <option value="ALL">All Classes</option>
            <option value="FERTILE">Fertile (Accept)</option>
            <option value="INFERTILE">Infertile (Penoy Cull)</option>
            <option value="ABNORMAL">Abnormal / Dead</option>
          </select>

          <select
            value={batchFilter}
            onChange={(e) => setBatchFilter(e.target.value)}
            className="bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#800000]"
          >
            <option value="ALL">All Batches</option>
            <option value="BATCH-2026-08-KAY-01">BATCH-2026-08-KAY-01 (Kayumanggi)</option>
            <option value="BATCH-2026-08-ITM-01">BATCH-2026-08-ITM-01 (Itim)</option>
            <option value="BATCH-2026-07-KHK-01">BATCH-2026-07-KHK-01 (Khaki)</option>
          </select>
        </div>

        <div className="text-xs text-slate-400">
          Showing <strong className="text-slate-200">{scans.length}</strong> egg scans
        </div>
      </div>

      {/* Grid View */}
      {viewMode === 'grid' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {scans.map((scan) => (
            <div
              key={scan.scan_id}
              onClick={() => setSelectedScan(scan)}
              className="bg-[#1E293B] border border-slate-800 rounded-xl p-4 shadow-lg hover:border-slate-700 cursor-pointer transition-all hover:scale-[1.01] space-y-3"
            >
              {/* Synthetic Candling Preview Frame */}
              <div className="w-full h-36 bg-slate-950 rounded-lg border border-slate-800 relative overflow-hidden flex items-center justify-center">
                {/* Candling Amber Glow */}
                <div
                  className={`w-28 h-36 rounded-full blur-md opacity-70 ${
                    scan.final_class === 'FERTILE'
                      ? 'bg-amber-600/80'
                      : scan.final_class === 'INFERTILE'
                      ? 'bg-amber-400/90'
                      : 'bg-red-900/80'
                  }`}
                />
                {/* Embryo Spider Webbing Silhouette if Fertile */}
                {scan.final_class === 'FERTILE' && (
                  <div className="absolute w-8 h-8 rounded-full bg-red-950 border border-red-800 shadow-inner" />
                )}

                {/* Bounding Box HUD */}
                <div className="absolute inset-4 border border-dashed border-amber-300/60 rounded-lg flex items-start justify-between p-1.5">
                  <span className="text-[9px] font-mono font-bold bg-slate-900/90 text-amber-300 px-1 py-0.5 rounded">
                    {(scan.confidence * 100).toFixed(1)}%
                  </span>
                  <span className="text-[9px] font-mono text-slate-400 bg-slate-900/80 px-1 py-0.5 rounded">
                    {scan.inference_ms}ms
                  </span>
                </div>

                <div className="absolute bottom-2 left-2">
                  <span className="text-[10px] font-mono font-bold bg-slate-900/90 text-slate-300 px-1.5 py-0.5 rounded">
                    #{scan.sequence_number.toString().padStart(3, '0')}
                  </span>
                </div>
              </div>

              {/* Card Meta */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <Badge type="fertility" value={scan.final_class} />
                  <span className="text-[10px] font-semibold text-slate-400">{scan.routing_action}</span>
                </div>
                <p className="text-[11px] text-slate-400 truncate">{scan.batch_id}</p>
                <p className="text-[10px] text-slate-500">{new Date(scan.scanned_at).toLocaleString()}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <div className="bg-[#1E293B] border border-slate-800 rounded-xl shadow-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4"># Seq</th>
                  <th className="py-3 px-4">Batch ID</th>
                  <th className="py-3 px-4">Classification</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Inference Latency</th>
                  <th className="py-3 px-4">Routing Action</th>
                  <th className="py-3 px-4">Scanned At</th>
                  <th className="py-3 px-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-medium text-slate-300 font-mono">
                {scans.map((s) => (
                  <tr key={s.scan_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-amber-400">#{s.sequence_number.toString().padStart(3, '0')}</td>
                    <td className="py-3 px-4 text-slate-200">{s.batch_id}</td>
                    <td className="py-3 px-4"><Badge type="fertility" value={s.final_class} /></td>
                    <td className="py-3 px-4 text-slate-200">{(s.confidence * 100).toFixed(1)}%</td>
                    <td className="py-3 px-4 text-slate-400">{s.inference_ms}ms</td>
                    <td className="py-3 px-4 font-sans font-bold">
                      <span className={s.routing_action === 'ACCEPT' ? 'text-emerald-400' : 'text-red-400'}>
                        {s.routing_action}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-sans">{new Date(s.scanned_at).toLocaleString()}</td>
                    <td className="py-3 px-4 text-right font-sans">
                      <button
                        onClick={() => setSelectedScan(s)}
                        className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors inline-flex items-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scan Detail Inspector Modal */}
      {selectedScan && (
        <Modal
          isOpen={Boolean(selectedScan)}
          onClose={() => setSelectedScan(null)}
          title={`Scan Inspector — #${selectedScan.sequence_number.toString().padStart(3, '0')} (${selectedScan.final_class})`}
        >
          <div className="space-y-4 text-xs">
            {/* Visual Box Frame */}
            <div className="w-full h-52 bg-slate-950 rounded-xl border border-slate-700 relative overflow-hidden flex items-center justify-center">
              <div
                className={`w-36 h-48 rounded-full blur-md opacity-80 ${
                  selectedScan.final_class === 'FERTILE' ? 'bg-amber-600' : 'bg-amber-400'
                }`}
              />
              <div className="absolute inset-6 border-2 border-dashed border-amber-300 rounded-lg flex items-start justify-between p-2">
                <span className="bg-slate-900/90 text-amber-300 text-xs font-mono font-bold px-2 py-0.5 rounded">
                  {selectedScan.final_class} ({(selectedScan.confidence * 100).toFixed(1)}%)
                </span>
                <span className="bg-slate-900/90 text-slate-300 text-xs font-mono px-2 py-0.5 rounded">
                  {selectedScan.inference_ms}ms
                </span>
              </div>
            </div>

            {/* Attributes Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Scan ID (UUIDv4)</p>
                <p className="font-mono text-slate-200 text-[11px] mt-0.5 truncate">{selectedScan.scan_id}</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Batch Identifier</p>
                <p className="font-bold text-slate-200 mt-0.5">{selectedScan.batch_id}</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Inference Latency</p>
                <p className="font-bold text-emerald-400 text-sm mt-0.5">{selectedScan.inference_ms} ms</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Mechanical Routing</p>
                <p className="font-bold text-slate-200 text-sm mt-0.5">{selectedScan.routing_action}</p>
              </div>
            </div>

            {/* Raw JSON Bounding Box Data */}
            <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
              <p className="text-slate-400 font-semibold">Normalized Detection Metadata (JSONB)</p>
              <pre className="text-[10px] text-slate-300 font-mono bg-black/40 p-2 rounded overflow-x-auto">
                {JSON.stringify(selectedScan.detections, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
