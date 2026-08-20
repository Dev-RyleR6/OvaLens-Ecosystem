import React from 'react';
import { MoreHorizontal, Sparkles, ShieldCheck, CheckCircle2 } from 'lucide-react';

interface IncubationTrackingCardProps {
  viableCount?: number;
  totalSet?: number;
  currentDay?: number;
  fertilePct?: number;
  penoyPct?: number;
  abnormalPct?: number;
  powerSpentPhp?: number;
  powerBudgetPhp?: number;
}

export const IncubationTrackingCard: React.FC<IncubationTrackingCardProps> = ({
  viableCount = 451,
  totalSet = 500,
  currentDay = 10,
  fertilePct = 90.2,
  penoyPct = 7.4,
  abnormalPct = 2.4,
  powerSpentPhp = 1390,
  powerBudgetPhp = 1600,
}) => {
  return (
    <div className="bento-card p-5 flex flex-col justify-between h-full">
      {/* Card Header */}
      <div>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">
            Incubation Stage & Cull Tracking
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-full">
              +8%
            </span>
            <button className="text-slate-500 hover:text-slate-300 p-1 rounded cursor-pointer">
              <MoreHorizontal className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Large Stage & Viability Metric */}
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl font-extrabold text-white tracking-tight">
            Day {currentDay}: {viableCount}
          </span>
          <span className="text-xs text-slate-400 font-medium">
            / {totalSet} Set ({currentDay} days into cycle)
          </span>
        </div>

        {/* Segmented Progress Bar (Smart Spending Limits in reference) */}
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Developmental Classification Split</span>
            <span className="text-emerald-400 font-bold">{fertilePct}% Viable</span>
          </div>

          <div className="h-2.5 w-full rounded-full bg-[#161B27] flex overflow-hidden p-0.5 border border-[#222A3B]">
            {/* Fertile Segment (Green) */}
            <div
              className="h-full rounded-l-full bg-emerald-500 shadow-[0_0_8px_#10B981]"
              style={{ width: `${fertilePct}%` }}
              title={`Fertile: ${fertilePct}%`}
            />
            {/* Penoy Segment (Amber) */}
            <div
              className="h-full bg-amber-500 shadow-[0_0_8px_#F59E0B]"
              style={{ width: `${penoyPct}%` }}
              title={`Penoy: ${penoyPct}%`}
            />
            {/* Abnormal Segment (Rose) */}
            <div
              className="h-full rounded-r-full bg-rose-500 shadow-[0_0_8px_#EF4444]"
              style={{ width: `${abnormalPct}%` }}
              title={`Abnormal: ${abnormalPct}%`}
            />
          </div>

          {/* Segment Legend */}
          <div className="grid grid-cols-3 gap-1 pt-1 text-[11px] text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-xs bg-emerald-500" />
              Fertile ({fertilePct}%)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-xs bg-amber-500" />
              Penoy ({penoyPct}%)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-xs bg-rose-500" />
              Dead ({abnormalPct}%)
            </span>
          </div>
        </div>
      </div>

      {/* Insight & Verification Pills (Bottom of Card) */}
      <div className="mt-4 pt-3 border-t border-[#1F2636] space-y-2">
        {/* Insight Pill */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-gradient-to-r from-teal-950/60 to-emerald-950/40 border border-teal-500/30 text-xs">
          <div className="flex items-center gap-2 text-teal-300">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span className="font-semibold text-slate-200">Insights:</span>
            <span className="text-slate-300">91.2% Kayumanggi viability</span>
          </div>
          <span className="text-[10px] text-teal-400 font-bold">1st Rank</span>
        </div>

        {/* Verification Pill 1 */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-[#161B27] border border-[#222A3B] text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Verify:</span>
            <span className="text-slate-300">100% Day-10 Penoy recovered</span>
          </div>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        </div>

        {/* Verification Pill 2 */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-[#161B27] border border-[#222A3B] text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Energy:</span>
            <span className="text-slate-300">₱{powerSpentPhp} of ₱{powerBudgetPhp} budget</span>
          </div>
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
        </div>
      </div>
    </div>
  );
};
