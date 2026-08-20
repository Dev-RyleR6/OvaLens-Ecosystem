import React, { useState } from 'react';
import { Search, Filter, ChevronRight, Eye } from 'lucide-react';
import { EggScan, FertilityClass } from '../../types';

interface ScanLedgerCardProps {
  scans?: EggScan[];
  onSelectScan?: (scan: EggScan) => void;
}

export const ScanLedgerCard: React.FC<ScanLedgerCardProps> = ({
  scans = [],
  onSelectScan,
}) => {
  const [search, setSearch] = useState('');
  const [filterTab, setFilterTab] = useState<'ALL' | 'FERTILE' | 'INFERTILE' | 'ABNORMAL'>('ALL');

  // Fallback sample scans if none provided
  const displayScans: EggScan[] = scans.length > 0 ? scans : [
    { scan_id: '1', session_id: 'sess-01', sequence_number: 1, batch_id: 'KAY-01', final_class: 'FERTILE' as FertilityClass, confidence: 0.954, inference_ms: 24, routing_action: 'ACCEPT' as const, scanned_at: new Date().toISOString(), detections: [] },
    { scan_id: '2', session_id: 'sess-01', sequence_number: 2, batch_id: 'KAY-01', final_class: 'INFERTILE' as FertilityClass, confidence: 0.912, inference_ms: 26, routing_action: 'REJECT' as const, scanned_at: new Date().toISOString(), detections: [] },
    { scan_id: '3', session_id: 'sess-02', sequence_number: 3, batch_id: 'ITM-01', final_class: 'FERTILE' as FertilityClass, confidence: 0.968, inference_ms: 22, routing_action: 'ACCEPT' as const, scanned_at: new Date().toISOString(), detections: [] },
    { scan_id: '4', session_id: 'sess-03', sequence_number: 4, batch_id: 'KHK-01', final_class: 'ABNORMAL' as FertilityClass, confidence: 0.884, inference_ms: 28, routing_action: 'REJECT' as const, scanned_at: new Date().toISOString(), detections: [] },
    { scan_id: '5', session_id: 'sess-01', sequence_number: 5, batch_id: 'KAY-01', final_class: 'FERTILE' as FertilityClass, confidence: 0.942, inference_ms: 25, routing_action: 'ACCEPT' as const, scanned_at: new Date().toISOString(), detections: [] },
  ];

  const filtered = displayScans.filter((s) => {
    const matchClass = filterTab === 'ALL' || s.final_class === filterTab;
    const matchSearch = s.sequence_number.toString().includes(search) ||
                        s.batch_id.toLowerCase().includes(search.toLowerCase());
    return matchClass && matchSearch;
  });

  return (
    <div className="bento-card p-5 flex flex-col justify-between h-full">
      {/* Search Bar & Filter Icon */}
      <div>
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search candling records..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-8 pl-8 pr-3 text-xs bg-[#161B27] border border-[#222A3B] rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 transition-colors"
            />
          </div>
          <button className="p-2 bg-[#161B27] border border-[#222A3B] rounded-xl text-slate-400 hover:text-slate-200 cursor-pointer">
            <Filter className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Filter Pill Tabs */}
        <div className="flex items-center gap-1.5 mt-3 overflow-x-auto pb-1 text-xs">
          <button
            onClick={() => setFilterTab('ALL')}
            className={`px-3 py-1 rounded-full font-medium transition-all cursor-pointer whitespace-nowrap ${
              filterTab === 'ALL'
                ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200 bg-[#161B27] border border-[#222A3B]'
            }`}
          >
            All Records
          </button>
          <button
            onClick={() => setFilterTab('FERTILE')}
            className={`px-3 py-1 rounded-full font-medium transition-all cursor-pointer whitespace-nowrap ${
              filterTab === 'FERTILE'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200 bg-[#161B27] border border-[#222A3B]'
            }`}
          >
            Fertile
          </button>
          <button
            onClick={() => setFilterTab('INFERTILE')}
            className={`px-3 py-1 rounded-full font-medium transition-all cursor-pointer whitespace-nowrap ${
              filterTab === 'INFERTILE'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200 bg-[#161B27] border border-[#222A3B]'
            }`}
          >
            Penoy Cull
          </button>
          <button
            onClick={() => setFilterTab('ABNORMAL')}
            className={`px-3 py-1 rounded-full font-medium transition-all cursor-pointer whitespace-nowrap ${
              filterTab === 'ABNORMAL'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200 bg-[#161B27] border border-[#222A3B]'
            }`}
          >
            Abnormal
          </button>
        </div>

        {/* Compact Table Header */}
        <div className="grid grid-cols-12 text-[11px] font-semibold text-slate-500 uppercase tracking-wider mt-3 px-2 pb-1.5 border-b border-[#1F2636]">
          <span className="col-span-4">Batch / Seq</span>
          <span className="col-span-4 text-center">Confidence</span>
          <span className="col-span-4 text-right">Status</span>
        </div>

        {/* Compact Rows */}
        <div className="space-y-1 mt-1.5 max-h-48 overflow-y-auto pr-1">
          {filtered.map((scan) => {
            let statusBadge = "bg-emerald-950/70 text-emerald-400 border-emerald-500/30";
            let statusText = "Fertile";

            if (scan.final_class === 'INFERTILE') {
              statusBadge = "bg-amber-950/70 text-amber-300 border-amber-500/30";
              statusText = "Penoy";
            } else if (scan.final_class === 'ABNORMAL') {
              statusBadge = "bg-rose-950/70 text-rose-400 border-rose-500/30";
              statusText = "Dead";
            }

            return (
              <div
                key={scan.scan_id}
                onClick={() => onSelectScan && onSelectScan(scan)}
                className="grid grid-cols-12 items-center p-2 rounded-xl bg-[#161B27]/60 hover:bg-[#161B27] border border-transparent hover:border-[#222A3B] transition-all cursor-pointer text-xs"
              >
                <div className="col-span-4">
                  <span className="font-semibold text-slate-200 block truncate">#{scan.sequence_number.toString().padStart(3, '0')}</span>
                  <span className="text-[10px] text-slate-500">{scan.batch_id}</span>
                </div>
                <div className="col-span-4 text-center">
                  <span className="font-bold text-white">{(scan.confidence * 100).toFixed(1)}%</span>
                  <span className="text-[10px] text-slate-500 block">{scan.inference_ms}ms</span>
                </div>
                <div className="col-span-4 text-right">
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${statusBadge}`}>
                    {statusText}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-3 pt-2 border-t border-[#1F2636] flex items-center justify-between text-[11px] text-slate-400">
        <span>Verified by Edge Camera Node</span>
        <span className="text-emerald-400 font-medium">{filtered.length} scans matched</span>
      </div>
    </div>
  );
};
