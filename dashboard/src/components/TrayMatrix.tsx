import React, { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Download,
  Play,
  X,
} from 'lucide-react';
import { FertilityClass } from '../types';
import { Badge } from './Badge';

export interface TrayEggSlot {
  slot_id: string; // e.g. "A1", "B4"
  row: number; // 1-6
  col: number; // 1-7
  row_label: string; // A-F
  col_label: string; // 1-7
  egg_id?: string;
  status: FertilityClass | 'EMPTY';
  confidence: number;
  aspect_ratio: number;
  luminance_v: number;
  candled_at: string;
}

interface TrayMatrixProps {
  batchCode?: string;
  totalTrays?: number;
  initialTray?: number;
  trayNumber?: number;
  onSlotSelect?: (slot: TrayEggSlot) => void;
}

const ROW_LABELS = ['A', 'B', 'C', 'D', 'E', 'F'];

export const TrayMatrix: React.FC<TrayMatrixProps> = ({
  batchCode = "BATCH-2026-08-KAY-01",
  totalTrays = 12,
  initialTray = 1,
  trayNumber,
  onSlotSelect
}) => {
  const [currentTray, setCurrentTray] = useState(trayNumber || initialTray);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [filterClass, setFilterClass] = useState<string>('ALL');
  const [selectedSlot, setSelectedSlot] = useState<TrayEggSlot | null>(null);
  const [hoveredSlot, setHoveredSlot] = useState<TrayEggSlot | null>(null);
  const [showRackView, setShowRackView] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationIndex, setSimulationIndex] = useState(-1);

  // Generate 42 deterministic slots per tray
  const traySlots = useMemo(() => {
    const list: TrayEggSlot[] = [];
    for (let r = 1; r <= 6; r++) {
      for (let c = 1; c <= 7; c++) {
        const row_label = ROW_LABELS[r - 1];
        const col_label = `${c}`;
        const slot_id = `${row_label}${col_label}`;
        
        const seed = (currentTray * 47 + r * 19 + c * 31) % 100;
        let status: FertilityClass | 'EMPTY' = 'FERTILE';
        let conf = 0.91 + ((r + c + currentTray) % 8) * 0.01;

        if (seed < 8) {
          status = 'INFERTILE';
          conf = 0.87 + (r % 5) * 0.02;
        } else if (seed < 12) {
          status = 'ABNORMAL';
          conf = 0.84 + (c % 4) * 0.02;
        } else if (currentTray === 12 && r === 6 && c >= 5) {
          status = 'EMPTY';
          conf = 0;
        }

        list.push({
          slot_id,
          row: r,
          col: c,
          row_label,
          col_label,
          egg_id: status !== 'EMPTY' ? `EGG-${batchCode.slice(-6)}-T${currentTray}-${slot_id}` : undefined,
          status,
          confidence: Number(conf.toFixed(3)),
          aspect_ratio: Number((0.74 + ((r * c) % 10) * 0.01).toFixed(2)),
          luminance_v: status === 'FERTILE' ? 55 + ((r + c * 3) % 18) : status === 'INFERTILE' ? 82 + ((r + c) % 12) : 38 + ((r * c) % 15),
          candled_at: new Date(Date.now() - (42 - (r * 7 + c)) * 12000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });
      }
    }
    return list;
  }, [currentTray, batchCode]);

  // Rack health summary for 12 trays
  const rackSummary = useMemo(() => {
    return Array.from({ length: totalTrays }, (_, i) => {
      const tNum = i + 1;
      const rate = 88.0 + ((tNum * 7) % 6) * 0.7;
      return {
        trayNumber: tNum,
        viability: Number(rate.toFixed(1)),
        fertile: Math.round(42 * (rate / 100)),
        penoy: Math.round(42 * 0.08),
        abnormal: Math.round(42 * 0.04),
      };
    });
  }, [totalTrays]);

  const fertileCount = traySlots.filter(s => s.status === 'FERTILE').length;
  const infertileCount = traySlots.filter(s => s.status === 'INFERTILE').length;
  const abnormalCount = traySlots.filter(s => s.status === 'ABNORMAL').length;
  const emptyCount = traySlots.filter(s => s.status === 'EMPTY').length;
  const occupiedCount = 42 - emptyCount;
  const trayFertilityRate = occupiedCount > 0 ? ((fertileCount / occupiedCount) * 100).toFixed(1) : '0.0';

  const handleSlotClick = (slot: TrayEggSlot) => {
    setSelectedSlot(slot);
    if (onSlotSelect) onSlotSelect(slot);
  };

  const runSimulation = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setSimulationIndex(0);
    let idx = 0;
    const interval = setInterval(() => {
      idx++;
      if (idx >= 42) {
        clearInterval(interval);
        setIsSimulating(false);
        setSimulationIndex(-1);
      } else {
        setSimulationIndex(idx);
        setSelectedSlot(traySlots[idx]);
      }
    }, 110);
  };

  const exportTrayMap = () => {
    const csvContent = "data:text/csv;charset=utf-8," +
      "Slot,Row,Col,Egg_ID,Classification,Confidence,Aspect_Ratio,HSV_Luminance\n" +
      traySlots.map(s => `${s.slot_id},${s.row},${s.col},${s.egg_id || 'EMPTY'},${s.status},${s.confidence},${s.aspect_ratio},${s.luminance_v}`).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Tray_${currentTray}_${batchCode}_Map.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden hover:border-slate-300 transition-colors">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 border-b border-slate-100">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#800000]">Incubation Tray</span>
              <span className="text-slate-300">•</span>
              <h3 className="text-sm font-bold text-[#0F172A]">
                Tray #{currentTray} of {totalTrays} (42-Egg Setter Caddy)
              </h3>
              <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                {trayFertilityRate}% Viable
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Batch: <strong>{batchCode}</strong> • Setter Cabinet A1 • Conveyor Diverter Synced
            </p>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2 flex-wrap justify-between lg:justify-end">
            {/* Tray Stepper */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-0.5 text-xs">
              <button
                onClick={() => setCurrentTray(prev => Math.max(1, prev - 1))}
                disabled={currentTray === 1 || isSimulating}
                className="p-1 rounded hover:bg-white text-slate-600 hover:text-slate-900 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors"
                title="Previous Tray"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="px-2 font-bold text-slate-800">
                Tray {currentTray} / {totalTrays}
              </span>
              <button
                onClick={() => setCurrentTray(prev => Math.min(totalTrays, prev + 1))}
                disabled={currentTray === totalTrays || isSimulating}
                className="p-1 rounded hover:bg-white text-slate-600 hover:text-slate-900 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors"
                title="Next Tray"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Toggle Rack View */}
            <button
              onClick={() => setShowRackView(prev => !prev)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                showRackView
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
              }`}
            >
              {showRackView ? 'Hide Cabinet Rack' : 'View All 12 Trays'}
            </button>

            {/* Simulation Run Button */}
            <button
              onClick={runSimulation}
              disabled={isSimulating}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer disabled:opacity-50"
              title="Simulate Conveyor Optical Sorting"
            >
              <Play className={`w-3.5 h-3.5 ${isSimulating ? 'text-emerald-700 animate-pulse' : 'text-slate-500'}`} />
              <span>{isSimulating ? 'Simulating...' : 'Test Diverter'}</span>
            </button>

            {/* Export CSV */}
            <button
              onClick={exportTrayMap}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer"
              title="Export Tray CSV Data"
            >
              <Download className="w-3.5 h-3.5" />
            </button>

            {/* Collapse Toggle */}
            <button
              onClick={() => setIsCollapsed(prev => !prev)}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 transition-colors cursor-pointer"
              title={isCollapsed ? "Expand Matrix" : "Collapse Matrix"}
            >
              {isCollapsed ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Filter Strip */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mt-3 pt-3 border-t border-slate-100">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider mr-1">Filter:</span>
            <button
              onClick={() => setFilterClass('ALL')}
              className={`px-2.5 py-0.5 rounded text-xs font-semibold transition-colors cursor-pointer border ${
                filterClass === 'ALL'
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              All (42)
            </button>
            <button
              onClick={() => setFilterClass('FERTILE')}
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold transition-colors cursor-pointer border ${
                filterClass === 'FERTILE'
                  ? 'bg-emerald-700 text-white border-emerald-700'
                  : 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              {fertileCount} Fertile (Accept)
            </button>
            <button
              onClick={() => setFilterClass('INFERTILE')}
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold transition-colors cursor-pointer border ${
                filterClass === 'INFERTILE'
                  ? 'bg-amber-600 text-white border-amber-600'
                  : 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
              {infertileCount} Penoy (Salvage)
            </button>
            <button
              onClick={() => setFilterClass('ABNORMAL')}
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold transition-colors cursor-pointer border ${
                filterClass === 'ABNORMAL'
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-red-50 text-red-800 border-red-200 hover:bg-red-100'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-red-600" />
              {abnormalCount} Dead (Discard)
            </button>
          </div>

          <span className="text-xs text-slate-500 font-medium">
            {occupiedCount} / 42 loaded in setter
          </span>
        </div>
      </div>

      {/* 12-Tray Cabinet Rack Drawer */}
      {showRackView && !isCollapsed && (
        <div className="p-4 bg-slate-50 border-b border-slate-200">
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-xs font-bold text-slate-800">
              Incubator Cabinet A1 Rack (12 Trays • 504 Eggs)
            </span>
            <span className="text-[11px] text-slate-500">Click any tray to switch</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
            {rackSummary.map((t) => {
              const isActive = currentTray === t.trayNumber;
              return (
                <button
                  key={t.trayNumber}
                  onClick={() => setCurrentTray(t.trayNumber)}
                  className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer hover-lift ${
                    isActive
                      ? 'bg-white border-[#800000] ring-2 ring-[#800000]/20 shadow-xs'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-slate-800">Tray {t.trayNumber}</span>
                    <span className="font-extrabold text-emerald-700">{t.viability}%</span>
                  </div>
                  <div className="h-1 w-full bg-slate-100 rounded-full overflow-hidden mb-1">
                    <div className="h-full bg-emerald-600 rounded-full" style={{ width: `${t.viability}%` }} />
                  </div>
                  <div className="text-[10px] text-slate-500 flex justify-between">
                    <span>{t.fertile} viable</span>
                    <span>{t.penoy + t.abnormal} cull</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Collapsible Grid Body */}
      {!isCollapsed && (
        <div className="p-4 sm:p-5 bg-white space-y-4">
          {/* Column Axis Labels */}
          <div className="grid grid-cols-7 gap-2 sm:gap-2.5 pl-6 sm:pl-7 text-center text-xs font-bold">
            {[1, 2, 3, 4, 5, 6, 7].map((c) => {
              const isColHovered = hoveredSlot?.col === c;
              return (
                <span
                  key={c}
                  className={`py-0.5 rounded transition-colors ${
                    isColHovered ? 'text-[#800000] font-black' : 'text-slate-400'
                  }`}
                >
                  Col {c}
                </span>
              );
            })}
          </div>

          {/* 6 Rows (A to F) */}
          <div className="space-y-2 sm:space-y-2.5">
            {ROW_LABELS.map((rowLabel, rIndex) => {
              const rowSlots = traySlots.filter(s => s.row_label === rowLabel);
              const isRowHovered = hoveredSlot?.row_label === rowLabel;

              return (
                <div key={rowLabel} className="flex items-center gap-2 sm:gap-2.5">
                  {/* Row Label (A-F) */}
                  <span
                    className={`w-4 sm:w-5 text-xs font-bold text-center flex-shrink-0 transition-colors ${
                      isRowHovered ? 'text-[#800000] font-black' : 'text-slate-400'
                    }`}
                  >
                    {rowLabel}
                  </span>

                  {/* 7 Slot Cradles in Row */}
                  <div className="grid grid-cols-7 gap-2 sm:gap-2.5 flex-grow">
                    {rowSlots.map((slot, sIndex) => {
                      const flatIndex = rIndex * 7 + sIndex;
                      const isDimmed = filterClass !== 'ALL' && slot.status !== filterClass;
                      const isSelected = selectedSlot?.slot_id === slot.slot_id;
                      const isSimActive = isSimulating && simulationIndex === flatIndex;

                      let cellBg = "bg-slate-50 border-slate-200 text-slate-500";
                      let dotBg = "bg-slate-400";

                      if (slot.status === 'FERTILE') {
                        cellBg = "bg-emerald-50/60 border-emerald-200 hover:border-emerald-500 text-emerald-950";
                        dotBg = "bg-emerald-600";
                      } else if (slot.status === 'INFERTILE') {
                        cellBg = "bg-amber-50/60 border-amber-200 hover:border-amber-500 text-amber-950";
                        dotBg = "bg-amber-500";
                      } else if (slot.status === 'ABNORMAL') {
                        cellBg = "bg-red-50/60 border-red-200 hover:border-red-500 text-red-950";
                        dotBg = "bg-red-600";
                      }

                      return (
                        <button
                          key={slot.slot_id}
                          onClick={() => handleSlotClick(slot)}
                          onMouseEnter={() => setHoveredSlot(slot)}
                          onMouseLeave={() => setHoveredSlot(null)}
                          className={`p-2 rounded-xl border transition-all duration-150 flex flex-col items-center justify-between aspect-square cursor-pointer ${cellBg} ${
                            isDimmed ? 'opacity-20 scale-95' : 'opacity-100 hover:scale-105 hover:shadow-xs'
                          } ${isSelected ? 'ring-2 ring-[#800000] border-[#800000] bg-white shadow-xs scale-105' : ''} ${
                            isSimActive ? 'ring-3 ring-emerald-500 bg-emerald-100 scale-110 shadow-sm' : ''
                          }`}
                          title={`Slot ${slot.slot_id}: ${slot.status} • ${(slot.confidence * 100).toFixed(1)}%`}
                        >
                          <span className="text-[10px] font-bold text-slate-500">
                            {slot.slot_id}
                          </span>

                          <span className={`w-3.5 h-3.5 rounded-full ${dotBg} transition-transform group-hover:scale-110`} />

                          <span className="text-[10px] font-extrabold text-slate-700">
                            {slot.confidence > 0 ? `${(slot.confidence * 100).toFixed(0)}%` : '—'}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Diagnostic Inspection Sheet */}
          {selectedSlot && (
            <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200 space-y-3 mt-2 animate-slide-up">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-200">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="px-2.5 py-0.5 rounded-md bg-slate-900 text-white text-xs font-mono font-bold">
                    Slot {selectedSlot.slot_id}
                  </span>
                  <span className="text-xs text-slate-600 font-mono">
                    {selectedSlot.egg_id || 'Empty Slot'}
                  </span>
                  <Badge type="fertility" value={selectedSlot.status} />
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Scanned at <strong>{selectedSlot.candled_at}</strong></span>
                  <button
                    onClick={() => setSelectedSlot(null)}
                    className="p-1 rounded-md hover:bg-slate-200 text-slate-400 hover:text-slate-700 cursor-pointer transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">YOLOv8 FP16 Conf</span>
                  <span className="font-extrabold text-slate-900 text-sm mt-0.5 block">
                    {(selectedSlot.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">Aspect Ratio</span>
                  <span className="font-extrabold text-slate-900 text-sm mt-0.5 block">
                    {selectedSlot.aspect_ratio} (Normal Oval)
                  </span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">HSV Luminance (V)</span>
                  <span className="font-extrabold text-slate-900 text-sm mt-0.5 block">
                    {selectedSlot.luminance_v} / 255
                  </span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">Conveyor Diverter</span>
                  <span className={`font-extrabold text-sm mt-0.5 block ${
                    selectedSlot.status === 'FERTILE' ? 'text-emerald-700' : 'text-rose-700'
                  }`}>
                    {selectedSlot.status === 'FERTILE' ? 'ACCEPT (Tray)' : selectedSlot.status === 'INFERTILE' ? 'DIVERT (Penoy)' : 'DIVERT (Discard)'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
