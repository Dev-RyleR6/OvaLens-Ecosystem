import React, { useState } from 'react';
import { MoreHorizontal, Plus, Minus, Users, CheckCircle2 } from 'lucide-react';

interface HatcheryMetricsCardProps {
  totalFertile?: number;
  penoyRevenue?: number;
  energySavedKwh?: number;
  cullRatePct?: number;
}

export const HatcheryMetricsCard: React.FC<HatcheryMetricsCardProps> = ({
  totalFertile = 1812,
  penoyRevenue = 2352,
  energySavedKwh = 45.4,
  cullRatePct = 18,
}) => {
  const [penoyMultiplier, setPenoyMultiplier] = useState(1);

  const displayPenoy = penoyRevenue * penoyMultiplier;
  const displayEnergy = (energySavedKwh * penoyMultiplier).toFixed(1);

  return (
    <div className="bento-card p-5 flex flex-col justify-between h-full">
      {/* Card Header */}
      <div>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">
            Hatchery & Incubation Metrics
          </h3>
          <button className="text-slate-500 hover:text-slate-300 p-1 rounded cursor-pointer">
            <MoreHorizontal className="w-4 h-4" />
          </button>
        </div>

        {/* Hero Figure & Circular Progress Ring */}
        <div className="mt-4 flex items-center justify-between">
          <div>
            <div className="text-3xl font-extrabold text-white tracking-tight font-sans">
              {totalFertile.toLocaleString()}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Viable Day-10 Spider Vein Embryos
            </p>
            <span className="text-[11px] text-emerald-400 font-medium flex items-center gap-1 mt-1">
              <CheckCircle2 className="w-3 h-3" />
              Verified by ONNX Edge Camera
            </span>
          </div>

          {/* Circular Progress Ring (18% Cull / 88.4% Viable) */}
          <div className="relative w-14 h-14 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-[#1F2636]"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className="text-emerald-500"
                strokeDasharray="88, 100"
                strokeWidth="3.5"
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <span className="absolute text-[11px] font-bold text-slate-100 font-sans">
              {100 - cullRatePct}%
            </span>
          </div>
        </div>
      </div>

      {/* Sub-Metrics & Operator Avatars Footer */}
      <div className="mt-5 pt-4 border-t border-[#1F2636] flex items-center justify-between gap-2">
        {/* Sub-Metric 1: Penoy Revenue */}
        <div>
          <span className="text-base font-bold text-amber-300 block leading-tight font-sans">
            ₱{displayPenoy.toLocaleString('en-US', { minimumFractionDigits: 0 })}
          </span>
          <span className="text-[10px] text-slate-400 font-medium">Day-10 Penoy Value</span>
        </div>

        {/* Sub-Metric 2: Energy Saved + Stepper */}
        <div>
          <div className="flex items-center gap-1.5">
            <span className="text-base font-bold text-cyan-300 block leading-tight font-sans">
              {displayEnergy} <span className="text-xs font-normal text-slate-400">kWh</span>
            </span>
            <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-950/70 border border-emerald-500/30 px-1.5 py-0.2 rounded-full">
              24%
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-medium">Power Avoided</span>
        </div>

        {/* Action Controls & Operator Avatars */}
        <div className="flex items-center gap-2">
          {/* Stepper Buttons */}
          <div className="flex items-center gap-1 bg-[#161B27] p-0.5 rounded-lg border border-[#222A3B]">
            <button
              onClick={() => setPenoyMultiplier(prev => Math.max(1, prev - 1))}
              className="p-1 rounded hover:bg-[#1F2636] text-slate-400 hover:text-white cursor-pointer"
              title="Decrease simulation cohort"
            >
              <Minus className="w-3 h-3" />
            </button>
            <button
              onClick={() => setPenoyMultiplier(prev => Math.min(5, prev + 1))}
              className="p-1 rounded hover:bg-[#1F2636] text-slate-400 hover:text-white cursor-pointer"
              title="Increase simulation cohort"
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>

          {/* Avatar Stack */}
          <div className="flex -space-x-1.5 overflow-hidden">
            <div className="inline-block h-6 w-6 rounded-full ring-2 ring-[#121620] bg-emerald-700 text-white text-[9px] font-bold flex items-center justify-center">
              RG
            </div>
            <div className="inline-block h-6 w-6 rounded-full ring-2 ring-[#121620] bg-cyan-700 text-white text-[9px] font-bold flex items-center justify-center">
              JT
            </div>
            <div className="inline-block h-6 w-6 rounded-full ring-2 ring-[#121620] bg-amber-700 text-white text-[9px] font-bold flex items-center justify-center">
              ML
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
