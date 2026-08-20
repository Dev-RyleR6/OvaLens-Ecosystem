import React, { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  HelpCircle,
  X,
  Filter,
  CheckCircle2,
  AlertCircle,
  Eye,
  Layers,
  Sparkles,
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
  const [viewMode, setViewMode] = useState<'grid' | 'compact'>('grid');
  const [filterClass, setFilterClass] = useState<string>('ALL');
  const [selectedSlot, setSelectedSlot] = useState<TrayEggSlot | null>(null);
  const [showHelpGuide, setShowHelpGuide] = useState(false);

  // Generate deterministic 42 slots per tray
  const traySlots = useMemo(() => {
    const list: TrayEggSlot[] = [];
    for (let r = 1; r <= 6; r++) {
      for (let c = 1; c <= 7; c++) {
        const row_label = ROW_LABELS[r - 1];
        const col_label = `${c}`;
        const slot_id = `${row_label}${col_label}`;
        
        // Pseudo-random deterministic distribution based on tray and coordinates
        const seed = (currentTray * 43 + r * 17 + c * 31) % 100;
        let status: FertilityClass | 'EMPTY' = 'FERTILE';
        let conf = 0.91 + ((r + c + currentTray) % 8) * 0.01;

        if (seed < 8) {
          status = 'INFERTILE';
          conf = 0.88 + (r % 5) * 0.02;
        } else if (seed < 12) {
          status = 'ABNORMAL';
          conf = 0.85 + (c % 4) * 0.02;
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
          luminance_v: 62 + ((r + c * 3) % 20),
          candled_at: new Date(Date.now() - (42 - (r * 7 + c)) * 12000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });
      }
    }
    return list;
  }, [currentTray, batchCode]);

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

  return (
    <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden transition-all duration-200">
      {/* Enterprise Header Bar */}
      <div className="p-4 sm:p-5 border-b border-slate-200 bg-white">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Title & Batch Context */}
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <div className="w-8 h-8 rounded-lg bg-maroon-50 border border-maroon-200 text-[#800000] flex items-center justify-center font-bold">
                <Layers className="w-4 h-4" />
              </div>
              <h3 className="text-base font-bold text-[#0F172A] tracking-tight">
                Industrial Incubation Tray Matrix
              </h3>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                42-Egg Setter Format
              </span>
              <span className="text-xs font-extrabold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                {trayFertilityRate}% Tray Viability
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Active Cohort: <strong>{batchCode}</strong> • Slot-by-slot optical candling and diverter verification
            </p>
          </div>

          {/* Controls: Tray Navigator, View Toggles & Actions */}
          <div className="flex items-center gap-2 flex-wrap justify-between lg:justify-end">
            {/* Tray Selector Stepper */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-1 text-xs">
              <button
                onClick={() => setCurrentTray(prev => Math.max(1, prev - 1))}
                disabled={currentTray === 1}
                className="p-1 rounded hover:bg-white text-slate-600 hover:text-slate-900 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors"
                title="Previous Tray"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2.5 font-bold text-slate-800">
                Tray {currentTray} / {totalTrays}
              </span>
              <button
                onClick={() => setCurrentTray(prev => Math.min(totalTrays, prev + 1))}
                disabled={currentTray === totalTrays}
                className="p-1 rounded hover:bg-white text-slate-600 hover:text-slate-900 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors"
                title="Next Tray"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-1 text-xs">
              <button
                onClick={() => { setViewMode('grid'); setIsCollapsed(false); }}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                  viewMode === 'grid' && !isCollapsed ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                Grid
              </button>
              <button
                onClick={() => { setViewMode('compact'); setIsCollapsed(false); }}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                  viewMode === 'compact' && !isCollapsed ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                Compact Strip
              </button>
            </div>

            {/* Help Guide Button */}
            <button
              onClick={() => setShowHelpGuide(prev => !prev)}
              className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
                showHelpGuide ? 'bg-maroon-50 border-maroon-200 text-[#800000]' : 'border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
              title="Incubation Tray Onboarding & Map Guide"
            >
              <HelpCircle className="w-4 h-4" />
            </button>

            {/* Collapse/Expand Toggle */}
            <button
              onClick={() => setIsCollapsed(prev => !prev)}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer"
              title={isCollapsed ? "Expand Tray Matrix" : "Collapse Tray Matrix"}
            >
              {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Filter Pills & Live Metric Strip */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mt-3.5 pt-3 border-t border-slate-100">
          {/* Biological Class Filter Chips */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1">
              <Filter className="w-3 h-3" /> Filter:
            </span>
            <button
              onClick={() => setFilterClass('ALL')}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer border ${
                filterClass === 'ALL'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              All Slots (42)
            </button>
            <button
              onClick={() => setFilterClass('FERTILE')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer border ${
                filterClass === 'FERTILE'
                  ? 'bg-emerald-700 text-white border-emerald-700'
                  : 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-600" />
              {fertileCount} Fertile
            </button>
            <button
              onClick={() => setFilterClass('INFERTILE')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer border ${
                filterClass === 'INFERTILE'
                  ? 'bg-amber-600 text-white border-amber-600'
                  : 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-amber-600" />
              {infertileCount} Penoy (Salvage)
            </button>
            <button
              onClick={() => setFilterClass('ABNORMAL')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer border ${
                filterClass === 'ABNORMAL'
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-red-50 text-red-800 border-red-200 hover:bg-red-100'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-red-600" />
              {abnormalCount} Dead (Discard)
            </button>
          </div>

          {/* Capacity Counter */}
          <span className="text-xs text-slate-500 font-medium">
            Slot Capacity: <strong className="text-slate-800">{occupiedCount} / 42</strong> eggs loaded
          </span>
        </div>
      </div>

      {/* Onboarding & Industrial Coordinate Guide (Dismissible) */}
      {showHelpGuide && (
        <div className="p-4 bg-amber-50/70 border-b border-amber-200 text-xs text-amber-900 flex items-start justify-between gap-3">
          <div className="space-y-1">
            <h4 className="font-bold flex items-center gap-1.5 text-amber-950">
              <Sparkles className="w-3.5 h-3.5 text-amber-700" />
              <span>Incubation Setter Tray Onboarding & Map Coordinates</span>
            </h4>
            <p className="text-amber-800 leading-relaxed">
              Standard duck egg industrial setter trays feature a <strong>6-Row × 7-Column grid (42 eggs)</strong>. Coordinates run from <code>A1</code> (top-left) to <code>F7</code> (bottom-right). Click any egg slot to inspect optical candling luminance, geometric aspect ratio, YOLOv8 FP16 confidence, and conveyor diverter routing decisions.
            </p>
          </div>
          <button
            onClick={() => setShowHelpGuide(false)}
            className="text-amber-700 hover:text-amber-950 cursor-pointer p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Collapsible Content Area */}
      {!isCollapsed && (
        <div className="p-4 sm:p-5 bg-slate-50/50">
          {/* COMPACT STRIP VIEW */}
          {viewMode === 'compact' ? (
            <div className="p-3 bg-white rounded-xl border border-slate-200">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-2">
                <span>Linear Tray Strip (Slots A1 → F7)</span>
                <span>Click any chip to inspect</span>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {traySlots.map((slot) => {
                  const isDimmed = filterClass !== 'ALL' && slot.status !== filterClass;
                  const isSelected = selectedSlot?.slot_id === slot.slot_id;

                  let badgeColor = "bg-slate-100 text-slate-400 border-slate-200";
                  if (slot.status === 'FERTILE') badgeColor = "bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100";
                  if (slot.status === 'INFERTILE') badgeColor = "bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100";
                  if (slot.status === 'ABNORMAL') badgeColor = "bg-red-50 text-red-800 border-red-300 hover:bg-red-100";

                  return (
                    <button
                      key={slot.slot_id}
                      onClick={() => handleSlotClick(slot)}
                      className={`h-7 px-2 text-[11px] font-bold rounded border transition-all cursor-pointer flex items-center gap-1 ${badgeColor} ${
                        isDimmed ? 'opacity-20' : 'opacity-100'
                      } ${isSelected ? 'ring-2 ring-[#800000] border-[#800000]' : ''}`}
                      title={`${slot.slot_id}: ${slot.status} (${(slot.confidence * 100).toFixed(0)}%)`}
                    >
                      <span>{slot.slot_id}</span>
                      {slot.status === 'FERTILE' && <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />}
                      {slot.status === 'INFERTILE' && <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />}
                      {slot.status === 'ABNORMAL' && <span className="w-1.5 h-1.5 rounded-full bg-red-600" />}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            /* FULL 6x7 EXPANDED MATRIX GRID */
            <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5">
              {/* Column Axis Headers (1 to 7) */}
              <div className="grid grid-cols-7 gap-2 sm:gap-3 mb-2 px-6 sm:px-8 text-center text-xs font-bold text-slate-400">
                <span>Col 1</span>
                <span>Col 2</span>
                <span>Col 3</span>
                <span>Col 4</span>
                <span>Col 5</span>
                <span>Col 6</span>
                <span>Col 7</span>
              </div>

              {/* 6 Rows (A to F) */}
              <div className="space-y-2 sm:space-y-3">
                {ROW_LABELS.map((rowLabel, rIndex) => {
                  const rowSlots = traySlots.filter(s => s.row_label === rowLabel);

                  return (
                    <div key={rowLabel} className="flex items-center gap-2 sm:gap-3">
                      {/* Row Label (A, B, C...) */}
                      <span className="w-4 sm:w-5 text-xs font-bold text-slate-400 text-center flex-shrink-0">
                        {rowLabel}
                      </span>

                      {/* 7 Slot Buttons in Row */}
                      <div className="grid grid-cols-7 gap-2 sm:gap-3 flex-grow">
                        {rowSlots.map((slot) => {
                          const isDimmed = filterClass !== 'ALL' && slot.status !== filterClass;
                          const isSelected = selectedSlot?.slot_id === slot.slot_id;

                          let bgState = "bg-slate-50 border-slate-200 text-slate-400";
                          let dotColor = "bg-slate-300";

                          if (slot.status === 'FERTILE') {
                            bgState = "bg-emerald-50/50 border-emerald-200 hover:border-emerald-400 text-emerald-950";
                            dotColor = "bg-emerald-600";
                          } else if (slot.status === 'INFERTILE') {
                            bgState = "bg-amber-50/50 border-amber-200 hover:border-amber-400 text-amber-950";
                            dotColor = "bg-amber-500";
                          } else if (slot.status === 'ABNORMAL') {
                            bgState = "bg-red-50/50 border-red-200 hover:border-red-400 text-red-950";
                            dotColor = "bg-red-600";
                          }

                          return (
                            <button
                              key={slot.slot_id}
                              onClick={() => handleSlotClick(slot)}
                              className={`relative p-2 rounded-xl border transition-all flex flex-col items-center justify-between aspect-square cursor-pointer shadow-2xs ${bgState} ${
                                isDimmed ? 'opacity-20 scale-95' : 'opacity-100 hover:scale-102'
                              } ${isSelected ? 'ring-2 ring-[#800000] border-[#800000] bg-white shadow-xs' : ''}`}
                              title={`Slot ${slot.slot_id}: ${slot.status} • ${(slot.confidence * 100).toFixed(1)}%`}
                            >
                              {/* Top Coordinate */}
                              <span className="text-[10px] sm:text-[11px] font-bold text-slate-500">
                                {slot.slot_id}
                              </span>

                              {/* Egg Graphic Icon / Status Dot */}
                              <div className="relative flex items-center justify-center my-0.5">
                                <span className={`w-3.5 sm:w-4 h-4 sm:h-5 rounded-full ${dotColor} shadow-xs`} />
                              </div>

                              {/* Confidence Pill */}
                              <span className="text-[9px] sm:text-[10px] font-extrabold text-slate-600">
                                {slot.confidence > 0 ? `${(slot.confidence * 100).toFixed(0)}%` : 'Empty'}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Diagnostic Slot Inspection Drawer (when a slot is clicked) */}
          {selectedSlot && (
            <div className="mt-4 p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-3 animate-in fade-in duration-150">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2.5">
                  <span className="px-2.5 py-1 rounded-md bg-slate-900 text-white text-xs font-mono font-bold">
                    Slot {selectedSlot.slot_id}
                  </span>
                  <span className="text-xs text-slate-600 font-mono">
                    {selectedSlot.egg_id || 'Empty Slot'}
                  </span>
                  <Badge type="fertility" value={selectedSlot.status} />
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Candled at: <strong>{selectedSlot.candled_at}</strong></span>
                  <button
                    onClick={() => setSelectedSlot(null)}
                    className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Slot Diagnostic Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">YOLOv8 FP16 Conf</span>
                  <span className="font-extrabold text-[#0F172A] text-sm mt-0.5 block">
                    {(selectedSlot.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">Aspect Ratio</span>
                  <span className="font-extrabold text-[#0F172A] text-sm mt-0.5 block">
                    {selectedSlot.aspect_ratio} (Valid Egg)
                  </span>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">HSV Luminance (V)</span>
                  <span className="font-extrabold text-[#0F172A] text-sm mt-0.5 block">
                    {selectedSlot.luminance_v} / 255
                  </span>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
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
