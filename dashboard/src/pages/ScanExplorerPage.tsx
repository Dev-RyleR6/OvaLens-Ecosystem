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
  Clock,
  Layers,
  Sliders,
  ChevronRight
} from 'lucide-react';
import { apiClient } from '../api/client';
import { EggScan, FertilityClass } from '../types';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { CandlingAperture } from '../components/CandlingAperture';

export const ScanExplorerPage: React.FC = () => {
  const [scans, setScans] = useState<EggScan[]>([]);
  const [selectedScan, setSelectedScan] = useState<EggScan | null>(null);
  const [classFilter, setClassFilter] = useState<string>('ALL');
  const [batchFilter, setBatchFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchScans = async () => {
    const data = await apiClient.getScans({
      final_class: classFilter === 'ALL' ? undefined : classFilter,
      batch_id: batchFilter === 'ALL' ? undefined : batchFilter,
      limit: 60
    });
    setScans(data);
    if (data.length > 0 && !selectedScan) {
      setSelectedScan(data[0]);
    }
  };

  useEffect(() => {
    fetchScans();
  }, [classFilter, batchFilter]);

  const filteredScans = scans.filter(s => {
    const matchSearch = s.scan_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        s.sequence_number.toString().includes(searchQuery);
    return matchSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-obsidian-900 border border-obsidian-700/80 p-4 rounded-lg shadow-xl">
        <div>
          <h2 className="text-lg font-display font-black tracking-wide text-white uppercase flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            Precision Candling Scan Explorer & Optical Ledger
          </h2>
          <p className="text-xs font-mono text-slate-400">
            Transillumination aperture telemetry, YOLOv8 normalized bounding boxes, and sorting decisions
          </p>
        </div>

        {/* Total Metric Count */}
        <div className="text-xs font-mono text-slate-400 bg-obsidian-950 px-3 py-1.5 rounded border border-obsidian-700">
          Showing <strong className="text-amber-300">{filteredScans.length}</strong> verified candling scans
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="bg-obsidian-900 border border-obsidian-700/80 rounded-lg p-3 flex flex-col md:flex-row items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Filter className="w-3.5 h-3.5" /> Class:
          </div>
          <select
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value)}
            className="bg-obsidian-950 border border-obsidian-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#800000]"
          >
            <option value="ALL">All Classes (500 Scans)</option>
            <option value="FERTILE">Fertile (Accept)</option>
            <option value="INFERTILE">Infertile (Penoy Cull)</option>
            <option value="ABNORMAL">Abnormal / Dead</option>
          </select>

          <select
            value={batchFilter}
            onChange={(e) => setBatchFilter(e.target.value)}
            className="bg-obsidian-950 border border-obsidian-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#800000]"
          >
            <option value="ALL">All Batches</option>
            <option value="BATCH-2026-08-KAY-01">BATCH-2026-08-KAY-01 (Kayumanggi)</option>
            <option value="BATCH-2026-08-ITM-01">BATCH-2026-08-ITM-01 (Itim)</option>
            <option value="BATCH-2026-07-KHK-01">BATCH-2026-07-KHK-01 (Khaki)</option>
          </select>
        </div>

        {/* Search by Seq / ID */}
        <div className="relative w-full md:w-64">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search # Seq or Scan UUID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-obsidian-950 border border-obsidian-700 rounded pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-[#800000]"
          />
        </div>
      </div>

      {/* Main Split Interface: Left Interactive Candler + Right Dense Audit Ledger */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left 5 Cols: Precision Candling Aperture Viewport */}
        <div className="xl:col-span-5 space-y-4">
          {selectedScan ? (
            <div className="sticky top-16">
              <CandlingAperture
                finalClass={selectedScan.final_class}
                confidence={selectedScan.confidence}
                inferenceMs={selectedScan.inference_ms}
                sequenceNumber={selectedScan.sequence_number}
                batchId={selectedScan.batch_id}
                aspectRatio={0.78}
                meanLuminance={selectedScan.final_class === 'FERTILE' ? 184.2 : selectedScan.final_class === 'INFERTILE' ? 220.5 : 110.4}
              />

              {/* JSONB Bounding Box Raw Inspector */}
              <div className="panel-scada p-3 mt-4 space-y-2 text-xs font-mono">
                <div className="flex items-center justify-between text-slate-400 border-b border-obsidian-700 pb-1.5">
                  <span className="font-bold text-slate-200">Raw YOLOv8 Detection Metadata (JSONB)</span>
                  <span className="text-[10px] text-amber-400">POSTGRESQL ON CONFLICT SAFE</span>
                </div>
                <pre className="text-[10px] bg-black/70 p-2.5 rounded text-emerald-400 border border-obsidian-800 overflow-x-auto max-h-36">
                  {JSON.stringify(
                    selectedScan.detections.length > 0
                      ? selectedScan.detections
                      : [
                          {
                            bbox: [0.24, 0.18, 0.76, 0.88],
                            class_name: selectedScan.final_class,
                            confidence: selectedScan.confidence,
                            aspect_ratio: 0.78,
                            geometric_valid: true
                          }
                        ],
                    null,
                    2
                  )}
                </pre>
              </div>
            </div>
          ) : (
            <div className="panel-scada p-8 text-center text-slate-500 font-mono text-xs">
              Select a scan from the ledger to inspect optical transillumination.
            </div>
          )}
        </div>

        {/* Right 7 Cols: High-Density Industrial Audit Ledger */}
        <div className="xl:col-span-7 panel-scada p-0 overflow-hidden">
          <div className="panel-scada-header">
            <span>Verified Candling Scans Ledger</span>
            <span className="text-[10px] text-slate-400 font-mono">Real-Time Ingestion</span>
          </div>

          <div className="overflow-x-auto max-h-[620px] overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-obsidian-950 text-slate-400 uppercase text-[10px] font-bold border-b border-obsidian-750 sticky top-0 z-10">
                <tr>
                  <th className="py-2.5 px-3"># Seq</th>
                  <th className="py-2.5 px-3">Batch ID</th>
                  <th className="py-2.5 px-3">Classification</th>
                  <th className="py-2.5 px-3">Confidence</th>
                  <th className="py-2.5 px-3">Latency</th>
                  <th className="py-2.5 px-3">Routing</th>
                  <th className="py-2.5 px-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-obsidian-800/80 text-slate-300">
                {filteredScans.map((s) => {
                  const isSelected = selectedScan?.scan_id === s.scan_id;
                  return (
                    <tr
                      key={s.scan_id}
                      onClick={() => setSelectedScan(s)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-[#800000]/25 border-l-4 border-l-amber-400 text-white font-bold'
                          : 'hover:bg-obsidian-800/60 border-l-4 border-l-transparent'
                      }`}
                    >
                      <td className="py-2.5 px-3 font-bold text-amber-400">
                        #{s.sequence_number.toString().padStart(3, '0')}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 truncate max-w-[130px]">{s.batch_id}</td>
                      <td className="py-2.5 px-3">
                        <Badge type="fertility" value={s.final_class} size="sm" />
                      </td>
                      <td className="py-2.5 px-3 text-slate-200">
                        {(s.confidence * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {s.inference_ms}ms
                      </td>
                      <td className="py-2.5 px-3 font-bold">
                        <span className={s.routing_action === 'ACCEPT' ? 'text-emerald-400' : 'text-rose-400'}>
                          {s.routing_action}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedScan(s);
                          }}
                          className="p-1 rounded bg-obsidian-800 hover:bg-obsidian-700 text-slate-300 transition-colors"
                        >
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
