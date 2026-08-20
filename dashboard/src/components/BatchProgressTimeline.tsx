import React from 'react';
import { BatchStage } from '../types';
import { CheckCircle2, Circle, AlertCircle } from 'lucide-react';

interface BatchProgressTimelineProps {
  currentStage: BatchStage;
  setDate: string;
}

export const BatchProgressTimeline: React.FC<BatchProgressTimelineProps> = ({ currentStage, setDate }) => {
  const stages = [
    { key: 'DAY_10', label: 'Day 10', title: '1st Candle (Penoy Cull)', dayOffset: 10, isCulled: true },
    { key: 'DAY_18', label: 'Day 18', title: '2nd Candle & Hatcher Transfer', dayOffset: 18, isCulled: false },
    { key: 'DAY_25', label: 'Day 25', title: 'Pipping Window', dayOffset: 25, isCulled: false },
    { key: 'HATCHED', label: 'Day 28', title: 'Hatch & Harvest', dayOffset: 28, isCulled: false },
  ];

  const getStageIndex = (stage: BatchStage) => {
    switch (stage) {
      case 'SETTING': return -1;
      case 'DAY_10': return 0;
      case 'DAY_18': return 1;
      case 'DAY_25': return 2;
      case 'HATCHED': return 3;
      case 'COMPLETED': return 3;
      default: return -1;
    }
  };

  const currentIndex = getStageIndex(currentStage);

  return (
    <div className="w-full py-2">
      <div className="relative flex items-center justify-between">
        {/* Connecting Track Line */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 -translate-y-1/2 bg-obsidian-700 z-0" />
        
        {/* Active Progress Bar */}
        <div
          className="absolute top-1/2 left-0 h-0.5 -translate-y-1/2 bg-amber-500 z-0 transition-all duration-500"
          style={{ width: `${Math.max(0, (currentIndex / (stages.length - 1)) * 100)}%` }}
        />

        {stages.map((st, idx) => {
          const isCompleted = idx < currentIndex || currentStage === 'HATCHED';
          const isCurrent = idx === currentIndex && currentStage !== 'HATCHED';

          let circleColor = "bg-obsidian-900 border-obsidian-700 text-slate-500";
          if (isCompleted) circleColor = "bg-emerald-950 border-emerald-500 text-emerald-400";
          if (isCurrent) circleColor = "bg-amber-950 border-amber-400 text-amber-300 ring-4 ring-amber-500/20";

          return (
            <div key={st.key} className="relative z-10 flex flex-col items-center group">
              <div
                className={`w-6 h-6 rounded-full border-2 flex items-center justify-center text-[10px] font-mono font-bold transition-all ${circleColor}`}
              >
                {isCompleted ? '✓' : idx + 1}
              </div>
              <span className="mt-1.5 text-[10px] font-mono font-bold text-slate-200">
                {st.label}
              </span>
              <span className="text-[9px] font-mono text-slate-400 text-center max-w-[90px] hidden sm:block">
                {st.title}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
