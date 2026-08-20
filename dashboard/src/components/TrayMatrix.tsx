import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card';
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

  // Generate 42 slots (6 rows x 7 cols) if not provided
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
  const emptyCount = slots.filter(s => s.status === 'EMPTY').length;

  const handleSlotClick = (slot: TrayEggSlot) => {
    setSelectedSlot(slot);
    if (onSelectSlot) onSelectSlot(slot);
  };

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <CardTitle className="text-base font-semibold">Incubator Tray Matrix</CardTitle>
            <CardDescription className="text-xs">
              Tray #{trayNumber} • {batchCode} • 42 Egg Capacity
            </CardDescription>
          </div>
          
          {/* Status summary pills */}
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 font-medium text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 dark:bg-emerald-400" />
              {fertileCount} Fertile
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 font-medium text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-600 dark:bg-amber-400" />
              {infertileCount} Penoy
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 font-medium text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-600 dark:bg-rose-400" />
              {abnormalCount} Dead
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 6x7 Clean Minimalist Dot Grid */}
        <div className="p-4 bg-muted/40 rounded-lg border">
          <div className="grid grid-cols-7 gap-2 sm:gap-3">
            {slots.map((slot) => {
              const isSelected = selectedSlot?.slot_id === slot.slot_id;

              let dotColor = "bg-muted-foreground/30";
              let hoverBorder = "hover:border-foreground/30";

              if (slot.status === 'FERTILE') {
                dotColor = "bg-emerald-500";
              } else if (slot.status === 'INFERTILE') {
                dotColor = "bg-amber-500";
              } else if (slot.status === 'ABNORMAL') {
                dotColor = "bg-rose-500";
              }

              return (
                <button
                  key={slot.slot_id}
                  onClick={() => handleSlotClick(slot)}
                  className={`group relative p-2 rounded-md bg-background border transition-all flex flex-col items-center justify-center aspect-square ${hoverBorder} ${
                    isSelected ? 'ring-2 ring-primary border-primary' : 'border-border'
                  } cursor-pointer`}
                  title={`${slot.slot_id}: ${slot.status}`}
                >
                  <span className={`w-3.5 h-3.5 rounded-full ${dotColor} transition-transform group-hover:scale-110`} />
                  <span className="text-[9px] text-muted-foreground font-medium mt-1">
                    {slot.slot_id}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Slot Information Bar */}
        {selectedSlot && (
          <div className="p-3 bg-muted/50 rounded-md border flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <span className="font-semibold text-foreground">Slot {selectedSlot.slot_id}</span>
              {selectedSlot.egg_id && <span className="text-muted-foreground">({selectedSlot.egg_id})</span>}
              <Badge type="fertility" value={selectedSlot.status} />
              {selectedSlot.confidence ? (
                <span className="text-muted-foreground">Confidence: {(selectedSlot.confidence * 100).toFixed(0)}%</span>
              ) : null}
            </div>

            <button
              onClick={() => setSelectedSlot(null)}
              className="text-xs text-muted-foreground hover:text-foreground underline cursor-pointer"
            >
              Close
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
