import React, { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  X,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
  Flame,
  LayoutGrid,
  Rows,
  SlidersHorizontal,
  Download,
  Play,
  RotateCcw,
  Info,
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
  const [viewMode, setViewMode] = useState<'setter' | 'heatmap' | 'rack' | 'compact'>('setter');
  const [filterClass, setFilterClass] = useState<string>('ALL');
  const [selectedSlot, setSelectedSlot] = useState<TrayEggSlot | null>(null);
  const [hoveredSlot, setHoveredSlot] = useState<TrayEggSlot | null>(null);
  const [showHelpGuide, setShowHelpGuide] = useState(false);
  const [showConfidence, setShowConfidence] = useState(true);
  const [showCoordinates, setShowCoordinates] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationIndex, setSimulationIndex] = useState(-1);

  // Generate deterministic 42 slots per tray
  const traySlots = useMemo(() => {
    const list: TrayEggSlot[] = [];
    for (let r = 1; r <= 6; r++) {
      for (let c = 1; c <= 7; c++) {
        const row_label = ROW_LABELS[r - 1];
        const col_label = `${c}`;
        const slot_id = `${row_label}${col_label}`;
        
        // Deterministic pseudo-distribution
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

  // Rack health summary for all 12 trays
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

  // Run conveyor sorting simulation through the 42 slots
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
    }, 120);
  };

  // Export JSON/CSV map of current tray
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
    <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden transition-all duration-200">
      {/* Enterprise Top Control Bar */}
      <div className="p-4 sm:p-5 border-b border-slate-200 bg-white">
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
          {/* Title & Institutional Badge */}
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <div className="w-8 h-8 rounded-lg bg-maroon-50 border border-maroon-200 text-[#800000] flex items-center justify-center font-bold">
                <Layers className="w-4 h-4" />
              </div>
              <h3 className="text-base font-bold text-[#0F172A] tracking-tight">
                Industrial Incubation Tray Matrix
              </h3>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                42-Egg Setter Caddy
              </span>
              <span className="text-xs font-extrabold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                {trayFertilityRate}% Tray Viability
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Active Cohort: <strong>{batchCode}</strong> • Setter Cabinet Unit A1 • Synchronized with Edge CV Conveyor
            </p>
          </div>

          {/* Controls: Multi-Tray Nav, 4 Enterprise Views & Actions */}
          <div className="flex items-center gap-2 flex-wrap justify-between xl:justify-end">
            {/* Tray Selector Stepper */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-1 text-xs">
              <button
                onClick={() => setCurrentTray(prev => Math.max(1, prev - 1))}
                disabled={currentTray === 1 || isSimulating}
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
                disabled={currentTray === totalTrays || isSimulating}
                className="p-1 rounded hover:bg-white text-slate-600 hover:text-slate-900 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed transition-colors"
                title="Next Tray"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* 4 Enterprise View Modes Switcher */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-1 text-xs">
              <button
                onClick={() => { setViewMode('setter'); setIsCollapsed(false); }}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 ${
                  viewMode === 'setter' && !isCollapsed ? 'bg-white text-[#800000] shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Physical Egg Setter Cradle View"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span>Setter Grid</span>
              </button>

              <button
                onClick={() => { setViewMode('heatmap'); setIsCollapsed(false); }}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 ${
                  viewMode === 'heatmap' && !isCollapsed ? 'bg-white text-amber-700 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Optical Candling Transillumination Heatmap"
              >
                <Flame className="w-3.5 h-3.5" />
                <span>Heatmap</span>
              </button>

              <button
                onClick={() => { setViewMode('rack'); setIsCollapsed(false); }}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 ${
                  viewMode === 'rack' && !isCollapsed ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
                title="12-Tray Incubation Cabinet Overview"
              >
                <Rows className="w-3.5 h-3.5" />
                <span>Rack (12 Trays)</span>
              </button>

              <button
                onClick={() => { setViewMode('compact'); setIsCollapsed(false); }}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                  viewMode === 'compact' && !isCollapsed ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Condensed Linear Chip Strip"
              >
                Compact
              </button>
            </div>

            {/* Quick Action Tools */}
            <div className="flex items-center gap-1">
              <button
                onClick={runSimulation}
                disabled={isSimulating}
                className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer disabled:opacity-50"
                title="Simulate Conveyor Optical Sorting Sweep"
              >
                <Play className={`w-4 h-4 ${isSimulating ? 'text-emerald-700 animate-pulse' : ''}`} />
              </button>

              <button
                onClick={exportTrayMap}
                className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer"
                title="Export Tray CSV Map"
              >
                <Download className="w-4 h-4" />
              </button>

              <button
                onClick={() => setShowHelpGuide(prev => !prev)}
                className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
                  showHelpGuide ? 'bg-maroon-50 border-maroon-200 text-[#800000]' : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
                title="Incubation Tray Onboarding & Map Guide"
              >
                <HelpCircle className="w-4 h-4" />
              </button>

              <button
                onClick={() => setIsCollapsed(prev => !prev)}
                className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer"
                title={isCollapsed ? "Expand Tray Matrix" : "Collapse Tray Matrix"}
              >
                {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>

        {/* Filters, Legend & Display Toggles Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mt-3.5 pt-3 border-t border-slate-100">
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
              {fertileCount} Fertile (Accept)
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

          {/* Quick Display Switches */}
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <label className="flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showConfidence}
                onChange={(e) => setShowConfidence(e.target.checked)}
                className="rounded border-slate-300 text-[#800000] focus:ring-[#800000] cursor-pointer"
              />
              <span>Show Conf %</span>
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showCoordinates}
                onChange={(e) => setShowCoordinates(e.target.checked)}
                className="rounded border-slate-300 text-[#800000] focus:ring-[#800000] cursor-pointer"
              />
              <span>Coordinates</span>
            </label>
          </div>
        </div>
      </div>

      {/* Onboarding Guide Accordion */}
      {showHelpGuide && (
        <div className="p-4 bg-amber-50/80 border-b border-amber-200 text-xs text-amber-900 flex items-start justify-between gap-3">
          <div className="space-y-1.5">
            <h4 className="font-bold flex items-center gap-1.5 text-amber-950">
              <Sparkles className="w-4 h-4 text-amber-700" />
              <span>Incubation Setter Tray Onboarding & Industrial Coordinate Standard</span>
            </h4>
            <p className="text-amber-800 leading-relaxed">
              Standard commercial duck egg setter caddies feature a <strong>6-Row × 7-Column grid (42 eggs)</strong>. Coordinates map from <code>A1</code> (top-left) to <code>F7</code> (bottom-right). A 500-egg cohort utilizes 12 stacked setter trays inside Incubation Cabinet A1. Click any egg cradle to inspect optical candling strobe penetration, vascular network verification, and automated diverter action.
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
          {/* VIEW MODE 1: PHYSICAL SETTER CRADLE VIEW (6x7 Grid with Egg Contour & Axis Highlights) */}
          {viewMode === 'setter' && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-6 shadow-xs">
              {/* Column Axis Headers (1 to 7) */}
              <div className="grid grid-cols-7 gap-2 sm:gap-3 mb-2 px-6 sm:px-8 text-center text-xs font-bold">
                {[1, 2, 3, 4, 5, 6, 7].map((c) => {
                  const isColHovered = hoveredSlot?.col === c;
                  return (
                    <span
                      key={c}
                      className={`transition-colors py-0.5 rounded ${
                        isColHovered ? 'text-[#800000] bg-maroon-50 font-extrabold' : 'text-slate-400'
                      }`}
                    >
                      Col {c}
                    </span>
                  );
                })}
              </div>

              {/* 6 Rows (A to F) */}
              <div className="space-y-2 sm:space-y-3">
                {ROW_LABELS.map((rowLabel, rIndex) => {
                  const rowSlots = traySlots.filter(s => s.row_label === rowLabel);
                  const isRowHovered = hoveredSlot?.row_label === rowLabel;

                  return (
                    <div key={rowLabel} className="flex items-center gap-2 sm:gap-3">
                      {/* Row Label (A, B, C...) */}
                      <span
                        className={`w-5 text-xs font-bold text-center flex-shrink-0 transition-colors py-1 rounded ${
                          isRowHovered ? 'text-[#800000] bg-maroon-50 font-extrabold' : 'text-slate-400'
                        }`}
                      >
                        {rowLabel}
                      </span>

                      {/* 7 Slot Cradle Buttons in Row */}
                      <div className="grid grid-cols-7 gap-2 sm:gap-3 flex-grow">
                        {rowSlots.map((slot, sIndex) => {
                          const flatIndex = rIndex * 7 + sIndex;
                          const isDimmed = filterClass !== 'ALL' && slot.status !== filterClass;
                          const isSelected = selectedSlot?.slot_id === slot.slot_id;
                          const isSimActive = isSimulating && simulationIndex === flatIndex;

                          let cradleBg = "bg-slate-50 border-slate-200";
                          let eggFill = "fill-slate-300";
                          let dotBg = "bg-slate-400";
                          let glowEffect = "";

                          if (slot.status === 'FERTILE') {
                            cradleBg = "bg-emerald-50/40 border-emerald-200 hover:border-emerald-500 hover:bg-emerald-50/80";
                            eggFill = "fill-emerald-600";
                            dotBg = "bg-emerald-600";
                            glowEffect = "shadow-[0_0_8px_rgba(21,128,61,0.25)]";
                          } else if (slot.status === 'INFERTILE') {
                            cradleBg = "bg-amber-50/40 border-amber-200 hover:border-amber-500 hover:bg-amber-50/80";
                            eggFill = "fill-amber-500";
                            dotBg = "bg-amber-500";
                            glowEffect = "shadow-[0_0_8px_rgba(217,119,6,0.25)]";
                          } else if (slot.status === 'ABNORMAL') {
                            cradleBg = "bg-red-50/40 border-red-200 hover:border-red-500 hover:bg-red-50/80";
                            eggFill = "fill-red-600";
                            dotBg = "bg-red-600";
                            glowEffect = "shadow-[0_0_8px_rgba(220,38,38,0.25)]";
                          }

                          return (
                            <button
                              key={slot.slot_id}
                              onClick={() => handleSlotClick(slot)}
                              onMouseEnter={() => setHoveredSlot(slot)}
                              onMouseLeave={() => setHoveredSlot(null)}
                              className={`relative p-2 rounded-xl border transition-all flex flex-col items-center justify-between aspect-square cursor-pointer ${cradleBg} ${
                                isDimmed ? 'opacity-15 scale-95' : 'opacity-100 hover:scale-102'
                              } ${isSelected ? 'ring-2 ring-[#800000] border-[#800000] bg-white shadow-md z-10' : ''} ${
                                isSimActive ? 'ring-3 ring-emerald-500 bg-emerald-100 scale-105 z-20' : ''
                              }`}
                              title={`Slot ${slot.slot_id}: ${slot.status} • ${(slot.confidence * 100).toFixed(1)}%`}
                            >
                              {/* Top Coordinate */}
                              {showCoordinates && (
                                <span className="text-[10px] sm:text-[11px] font-bold text-slate-500">
                                  {slot.slot_id}
                                </span>
                              )}

                              {/* Physical Egg Silhouette Graphic */}
                              <div className="relative flex items-center justify-center my-0.5">
                                <svg viewBox="0 0 100 130" className={`w-5 sm:w-6 h-6 sm:h-7 ${glowEffect}`}>
                                  <path
                                    d="M 50,5 C 75,5 95,45 95,85 C 95,115 75,128 50,128 C 25,128 5,115 5,85 C 5,45 25,5 50,5 Z"
                                    className={eggFill}
                                  />
                                </svg>
                              </div>

                              {/* Confidence Score Pill */}
                              {showConfidence && (
                                <span className="text-[9px] sm:text-[10px] font-extrabold text-slate-700">
                                  {slot.confidence > 0 ? `${(slot.confidence * 100).toFixed(0)}%` : 'Empty'}
                                </span>
                              )}
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

          {/* VIEW MODE 2: OPTICAL TRANSILLUMINATION HEATMAP VIEW */}
          {viewMode === 'heatmap' && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 text-xs text-slate-600">
                <span className="font-semibold flex items-center gap-1.5">
                  <Flame className="w-4 h-4 text-amber-600" />
                  <span>Optical Candling Strobe Luminance Spectrum (HSV Value $V \in [0, 255]$)</span>
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400">Dense / Dead Embryo (V &lt; 45)</span>
                  <div className="w-24 h-2.5 rounded-full bg-gradient-to-r from-red-800 via-amber-500 to-yellow-300" />
                  <span className="text-[10px] text-slate-400">Clear Penoy Yolk (V &gt; 80)</span>
                </div>
              </div>

              {/* Heatmap Grid */}
              <div className="grid grid-cols-7 gap-2 sm:gap-3">
                {traySlots.map((slot) => {
                  const isSelected = selectedSlot?.slot_id === slot.slot_id;

                  // Color gradient interpolation based on HSV luminance
                  let heatBg = "bg-amber-500 text-amber-950";
                  if (slot.luminance_v < 45) heatBg = "bg-red-800 text-red-100";
                  else if (slot.luminance_v < 60) heatBg = "bg-orange-600 text-orange-100";
                  else if (slot.luminance_v < 75) heatBg = "bg-amber-400 text-amber-950";
                  else heatBg = "bg-yellow-300 text-yellow-950";

                  return (
                    <button
                      key={slot.slot_id}
                      onClick={() => handleSlotClick(slot)}
                      className={`p-3 rounded-lg border border-black/10 transition-all flex flex-col items-center justify-between aspect-square cursor-pointer shadow-2xs ${heatBg} ${
                        isSelected ? 'ring-3 ring-slate-900 scale-105 z-10' : 'hover:scale-102'
                      }`}
                    >
                      <span className="text-[10px] font-mono font-bold opacity-80">{slot.slot_id}</span>
                      <span className="text-xs font-black tracking-tight">{slot.luminance_v}</span>
                      <span className="text-[9px] font-bold opacity-75">{slot.status.slice(0, 4)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* VIEW MODE 3: 12-TRAY CABINET RACK OVERVIEW */}
          {viewMode === 'rack' && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 text-xs">
                <span className="font-bold text-[#0F172A]">Incubation Cabinet A1 — 12 Stacked Setter Trays (504 Eggs Total)</span>
                <span className="text-slate-500">Click any tray to load and inspect</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {rackSummary.map((tray) => {
                  const isActive = currentTray === tray.trayNumber;

                  return (
                    <button
                      key={tray.trayNumber}
                      onClick={() => { setCurrentTray(tray.trayNumber); setViewMode('setter'); }}
                      className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                        isActive
                          ? 'border-[#800000] bg-maroon-50/40 ring-2 ring-[#800000]/20 shadow-xs'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-[#0F172A]">Tray #{tray.trayNumber}</span>
                        <span className="text-xs font-extrabold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          {tray.viability}%
                        </span>
                      </div>

                      <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden mb-2">
                        <div className="h-full bg-emerald-600 rounded-full" style={{ width: `${tray.viability}%` }} />
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-500">
                        <span>{tray.fertile} Fertile</span>
                        <span>{tray.penoy} Penoy</span>
                        <span>{tray.abnormal} Dead</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* VIEW MODE 4: COMPACT STRIP VIEW */}
          {viewMode === 'compact' && (
            <div className="p-3.5 bg-white rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-2.5">
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
          )}

          {/* Diagnostic Slot Inspection Sheet / Popover (when any slot is clicked) */}
          {selectedSlot && (
            <div className="mt-4 p-4 sm:p-5 bg-white rounded-xl border border-slate-200 shadow-xs space-y-3.5 animate-in fade-in duration-150">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="px-2.5 py-1 rounded-md bg-slate-900 text-white text-xs font-mono font-bold">
                    Slot {selectedSlot.slot_id}
                  </span>
                  <span className="text-xs text-slate-600 font-mono font-semibold">
                    {selectedSlot.egg_id || 'Empty Slot'}
                  </span>
                  <Badge type="fertility" value={selectedSlot.status} />
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">
                    Candled at: <strong>{selectedSlot.candled_at}</strong>
                  </span>
                  <button
                    onClick={() => setSelectedSlot(null)}
                    className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Slot Diagnostic Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">YOLOv8 FP16 Conf</span>
                  <span className="font-black text-[#0F172A] text-sm mt-0.5 block">
                    {(selectedSlot.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">Aspect Ratio</span>
                  <span className="font-black text-[#0F172A] text-sm mt-0.5 block">
                    {selectedSlot.aspect_ratio} (Valid Egg)
                  </span>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">HSV Luminance (V)</span>
                  <span className="font-black text-[#0F172A] text-sm mt-0.5 block">
                    {selectedSlot.luminance_v} / 255
                  </span>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">Conveyor Diverter</span>
                  <span className={`font-black text-sm mt-0.5 block ${
                    selectedSlot.status === 'FERTILE' ? 'text-emerald-700' : 'text-rose-700'
                  }`}>
                    {selectedSlot.status === 'FERTILE' ? 'ACCEPT (Incubate)' : selectedSlot.status === 'INFERTILE' ? 'DIVERT (Penoy)' : 'DIVERT (Discard)'}
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
