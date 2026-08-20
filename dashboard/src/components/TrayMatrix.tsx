import React, { useState } from 'react';
import { FertilityClass } from '../types';
import { Badge } from './Badge';

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

  // Generate 42 slots (6 rows x 7 cols)
  const slots: TrayEggSlot[] = initialSlots || (() => {
    const list: TrayEggSlot[] = [];
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

  const handleSlotClick = (slot: TrayEggSlot) => {
    setSelectedSlot(slot);
    if (onSelectSlot) onSelectSlot(slot);
  };

  return (
    <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-base font-bold text-[#0F172A]">Incubator Tray Matrix (42-Egg)</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Tray #{trayNumber} • {batchCode} • Slot-by-slot candling classification
          </p>
        </div>

        {/* Status Count Pills */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            {fertileCount} Fertile
          </span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-amber-600" />
            {infertileCount} Penoy
          </span>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-50 text-red-800 border border-red-200 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-red-600" />
            {abnormalCount} Dead
          </span>
        </div>
      </div>

      {/* 6x7 Grid */}
      <div className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
        <div className="grid grid-cols-7 gap-2.5">
          {slots.map((slot) => {
            const isSelected = selectedSlot?.slot_id === slot.slot_id;

            let dotColor = "bg-slate-300";
            if (slot.status === 'FERTILE') dotColor = "bg-emerald-600";
            if (slot.status === 'INFERTILE') dotColor = "bg-amber-500";
            if (slot.status === 'ABNORMAL') dotColor = "bg-red-600";

            return (
              <button
                key={slot.slot_id}
                onClick={() => handleSlotClick(slot)}
                className={`p-2 rounded-lg bg-white border transition-all flex flex-col items-center justify-center aspect-square shadow-xs hover:border-slate-400 ${
                  isSelected ? 'ring-2 ring-[#800000] border-[#800000]' : 'border-slate-200'
                } cursor-pointer`}
                title={`${slot.slot_id}: ${slot.status}`}
              >
                <span className={`w-3.5 h-3.5 rounded-full ${dotColor}`} />
                <span className="text-[10px] text-slate-500 font-semibold mt-1">
                  {slot.slot_id}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected Slot Information */}
      {selectedSlot && (
        <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            <span className="font-bold text-slate-900">Slot {selectedSlot.slot_id}</span>
            {selectedSlot.egg_id && <span className="text-slate-500 font-mono">({selectedSlot.egg_id})</span>}
            <Badge type="fertility" value={selectedSlot.status} />
            {selectedSlot.confidence ? (
              <span className="text-slate-600 font-medium">Confidence: {(selectedSlot.confidence * 100).toFixed(0)}%</span>
            ) : null}
          </div>

          <button
            onClick={() => setSelectedSlot(null)}
            className="text-xs font-semibold text-[#800000] hover:underline cursor-pointer"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
};
