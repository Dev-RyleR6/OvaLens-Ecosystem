import React, { useState } from 'react';
import { Layers, CheckCircle2, AlertCircle, HelpCircle, Eye } from 'lucide-react';
import { FertilityClass } from '../types';

export interface TrayEggSlot {
  slot_id: string; // e.g. "R1-C1"
  row: number;
  col: number;
  egg_id?: string;
  status: FertilityClass | 'EMPTY';
  confidence?: number;
  candled_day?: number;
}

interface TrayMatrixProps {
  batchCode?: string;
  trayNumber?: number;
  slots?: TrayEggSlot[];
  onSelectSlot?: (slot: TrayEggSlot) => void;
}

export const TrayMatrix: React.FC<TrayMatrixProps> = ({
  batchCode = "BATCH-2026-08-KAY-01",
  trayNumber = 1,
  slots: initialSlots,
  onSelectSlot
}) => {
  const [selectedSlot, setSelectedSlot] = useState<TrayEggSlot | null>(null);

  // Generate 42 slots (6 rows x 7 cols) if not provided
  const slots: TrayEggSlot[] = initialSlots || (() => {
    const list: TrayEggSlot[] = [];
    // Seed realistic 42-egg duck incubator tray (e.g. ~88% fertile, ~8% infertile, ~4% abnormal)
    for (let r = 1; r <= 6; r++) {
      for (let c = 1; c <= 7; c++) {
        const slot_id = `R${r}-C${c}`;
        const rand = (r * 7 + c * 13) % 100;
        let status: FertilityClass | 'EMPTY' = 'FERTILE';
        let conf = 0.92 + ((r + c) % 7) * 0.01;

        if (rand < 8) {
          status = 'INFERTILE';
          conf = 0.88 + (r % 5) * 0.02;
        } else if (rand < 13) {
          status = 'ABNORMAL';
          conf = 0.84 + (c % 5) * 0.02;
        } else if (r === 6 && c >= 6) {
          status = 'EMPTY';
          conf = 0;
        }

        list.push({
          slot_id,
          row: r,
          col: c,
          egg_id: status !== 'EMPTY' ? `EGG-${batchCode.slice(-6)}-${r}${c}` : undefined,
          status,
          confidence: Number(conf.toFixed(2)),
          candled_day: 10,
        });
      }
    }
    return list;
  })();

  const fertileCount = slots.filter(s => s.status === 'FERTILE').length;
  const infertileCount = slots.filter(s => s.status === 'INFERTILE').length;
  const abnormalCount = slots.filter(s => s.status === 'ABNORMAL').length;
  const emptyCount = slots.filter(s => s.status === 'EMPTY').length;
  const occupiedCount = slots.length - emptyCount;
  const fertilityRate = occupiedCount > 0 ? ((fertileCount / occupiedCount) * 100).toFixed(1) : '0.0';

  const handleSlotClick = (slot: TrayEggSlot) => {
    setSelectedSlot(slot);
    if (onSelectSlot) onSelectSlot(slot);
  };

  return (
    <div className="panel-scada p-4 space-y-4">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-obsidian-700/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-[#800000]/20 rounded border border-[#800000]/50 text-amber-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
              Physical Incubator Tray Matrix
              <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 bg-obsidian-800 border border-obsidian-600 rounded text-amber-300">
                TRAY #{trayNumber} (42-EGG MATRIX)
              </span>
            </h3>
            <p className="text-[10px] font-mono text-slate-400">
              Batch: <strong className="text-slate-200">{batchCode}</strong> • Day 10 Candling Layout
            </p>
          </div>
        </div>

        {/* Live Slot Health Summary Bar */}
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <div className="px-2 py-1 bg-emerald-950/60 border border-emerald-700/50 rounded flex items-center gap-1.5 text-emerald-300">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>FERTILE: <strong>{fertileCount}</strong></span>
          </div>
          <div className="px-2 py-1 bg-amber-950/60 border border-amber-700/50 rounded flex items-center gap-1.5 text-amber-300">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>PENOY: <strong>{infertileCount}</strong></span>
          </div>
          <div className="px-2 py-1 bg-rose-950/60 border border-rose-700/50 rounded flex items-center gap-1.5 text-rose-300">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
            <span>ABNORMAL: <strong>{abnormalCount}</strong></span>
          </div>
        </div>
      </div>

      {/* 42-Egg Physical Grid (6 Rows x 7 Columns) */}
      <div className="p-3 bg-obsidian-950/90 rounded border border-obsidian-800 relative overflow-hidden">
        {/* Column Headers (C1 to C7) */}
        <div className="grid grid-cols-7 gap-2 mb-1.5 text-center text-[9px] font-mono font-bold text-slate-500">
          <span>COL 1</span>
          <span>COL 2</span>
          <span>COL 3</span>
          <span>COL 4</span>
          <span>COL 5</span>
          <span>COL 6</span>
          <span>COL 7</span>
        </div>

        {/* Grid Matrix */}
        <div className="grid grid-cols-7 gap-2">
          {slots.map((slot) => {
            const isSelected = selectedSlot?.slot_id === slot.slot_id;

            let slotBg = "bg-obsidian-900/60 border-obsidian-800 text-slate-600 hover:border-slate-600";
            let dotColor = "bg-slate-700";

            if (slot.status === 'FERTILE') {
              slotBg = "bg-emerald-950/40 border-emerald-800/60 text-emerald-300 hover:border-emerald-500 hover:bg-emerald-950/80";
              dotColor = "bg-emerald-400 shadow-[0_0_5px_#10B981]";
            } else if (slot.status === 'INFERTILE') {
              slotBg = "bg-amber-950/40 border-amber-800/60 text-amber-300 hover:border-amber-500 hover:bg-amber-950/80";
              dotColor = "bg-amber-400 shadow-[0_0_5px_#F59E0B]";
            } else if (slot.status === 'ABNORMAL') {
              slotBg = "bg-rose-950/40 border-rose-800/60 text-rose-300 hover:border-rose-500 hover:bg-rose-950/80";
              dotColor = "bg-rose-400 shadow-[0_0_5px_#EF4444]";
            }

            return (
              <button
                key={slot.slot_id}
                onClick={() => handleSlotClick(slot)}
                className={`group relative p-2 rounded flex flex-col items-center justify-between aspect-[1/1.2] border transition-all ${slotBg} ${
                  isSelected ? 'ring-2 ring-amber-400 border-amber-400 scale-[1.03] z-10' : ''
                }`}
                title={`Slot ${slot.slot_id} • ${slot.status} (${slot.confidence ? (slot.confidence * 100).toFixed(0) + '%' : 'Empty'})`}
              >
                {/* Slot Coordinate */}
                <span className="text-[9px] font-mono font-semibold text-slate-400 self-start">
                  {slot.slot_id}
                </span>

                {/* Egg Tactile Icon / Status Indicator */}
                {slot.status !== 'EMPTY' ? (
                  <div className="my-auto flex flex-col items-center">
                    <div className="w-5 h-7 rounded-[50%_50%_45%_45%] border border-current/40 flex items-center justify-center shadow-inner relative overflow-hidden">
                      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
                    </div>
                    <span className="text-[8px] font-mono font-bold mt-1 tracking-tighter">
                      {slot.confidence ? `${(slot.confidence * 100).toFixed(0)}%` : ''}
                    </span>
                  </div>
                ) : (
                  <span className="text-[9px] font-mono text-slate-600 my-auto">EMPTY</span>
                )}

                <span className="text-[7px] font-mono uppercase tracking-tight opacity-70">
                  {slot.status === 'FERTILE' ? 'OK' : slot.status === 'INFERTILE' ? 'PENOY' : slot.status === 'ABNORMAL' ? 'REJ' : '--'}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected Slot Detailed Telemetry Drawer */}
      {selectedSlot && (
        <div className="p-3 bg-obsidian-850 border border-obsidian-700 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-mono font-black text-amber-300 text-sm">SLOT {selectedSlot.slot_id}</span>
              <span className="text-slate-400 font-mono text-[10px]">({selectedSlot.egg_id || 'Empty Pocket'})</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                selectedSlot.status === 'FERTILE' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                selectedSlot.status === 'INFERTILE' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                'bg-rose-950 text-rose-300 border border-rose-800'
              }`}>
                {selectedSlot.status}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono">
              Inference Confidence: <strong className="text-slate-200">{selectedSlot.confidence ? (selectedSlot.confidence * 100).toFixed(1) + '%' : 'N/A'}</strong> • 
              Candling Cycle: <strong>Day {selectedSlot.candled_day}</strong> • 
              Action: <strong className={selectedSlot.status === 'FERTILE' ? 'text-emerald-400' : 'text-rose-400'}>
                {selectedSlot.status === 'FERTILE' ? 'RETAIN IN INCUBATOR' : 'DIVERT TO PENOY CULL'}
              </strong>
            </p>
          </div>

          <button
            onClick={() => setSelectedSlot(null)}
            className="px-3 py-1 bg-obsidian-700 hover:bg-obsidian-600 text-slate-200 text-xs font-mono font-semibold rounded border border-obsidian-600 self-end sm:self-auto transition-colors"
          >
            Close Inspector
          </button>
        </div>
      )}
    </div>
  );
};
