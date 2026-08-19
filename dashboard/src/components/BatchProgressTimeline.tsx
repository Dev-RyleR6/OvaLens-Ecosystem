import React from 'react';
import { BatchStage } from '../types';

interface BatchProgressTimelineProps {
  currentStage: BatchStage;
  setDate: string;
}

export const BatchProgressTimeline: React.FC<BatchProgressTimelineProps> = ({ currentStage, setDate }) => {
  const stages: { stage: BatchStage; label: string; day: string }[] = [
    { stage: 'SETTING', label: 'Incubator Set', day: 'Day 0' },
    { stage: 'DAY_10', label: '1st Candling (Penoy Cull)', day: 'Day 10' },
    { stage: 'DAY_18', label: '2nd Candling (Hatcher)', day: 'Day 18' },
    { stage: 'DAY_25', label: 'Final Audit (Pipping)', day: 'Day 25' },
    { stage: 'COMPLETED', label: 'Ducklings Hatched', day: 'Day 28' },
  ];

  const stageOrder: Record<BatchStage, number> = {
    SETTING: 0,
    DAY_10: 1,
    DAY_18: 2,
    DAY_25: 3,
    HATCHED: 4,
    COMPLETED: 4,
  };

  const currentIdx = stageOrder[currentStage] ?? 0;

  return (
    <div className="w-full py-3">
      <div className="flex items-center justify-between relative">
        {/* Connecting Line */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-700 -translate-y-1/2 z-0" />
        <div
          className="absolute top-1/2 left-0 h-0.5 bg-[#800000] -translate-y-1/2 z-0 transition-all duration-500"
          style={{ width: `${(currentIdx / (stages.length - 1)) * 100}%` }}
        />

        {stages.map((s, idx) => {
          const isPassed = idx <= currentIdx;
          const isCurrent = idx === currentIdx;

          return (
            <div key={s.stage} className="flex flex-col items-center relative z-10">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border-2 transition-all duration-300 ${
                  isCurrent
                    ? 'bg-[#800000] border-amber-400 text-white ring-4 ring-[#800000]/30 shadow-md scale-110'
                    : isPassed
                    ? 'bg-[#800000] border-[#800000] text-white'
                    : 'bg-slate-800 border-slate-600 text-slate-400'
                }`}
              >
                {idx + 1}
              </div>
              <span className={`text-[10px] font-semibold mt-1.5 ${isCurrent ? 'text-amber-400 font-bold' : isPassed ? 'text-slate-200' : 'text-slate-500'}`}>
                {s.day}
              </span>
              <span className="text-[9px] text-slate-400 text-center max-w-[70px] leading-tight hidden md:block">
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
