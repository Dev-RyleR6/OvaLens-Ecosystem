import React from 'react';
import { BatchStage } from '../types';
import { Check } from 'lucide-react';

interface BatchProgressTimelineProps {
  currentStage: BatchStage;
  setDate?: string;
}

export const BatchProgressTimeline: React.FC<BatchProgressTimelineProps> = ({ currentStage }) => {
  const stages = [
    { key: 'SETTING', day: 'Day 0', title: 'Incubator Set', desc: 'Initial tray load' },
    { key: 'DAY_10', day: 'Day 10', title: '1st Candling', desc: 'Penoy market salvage' },
    { key: 'DAY_18', day: 'Day 18', title: 'Hatcher Transfer', desc: 'Stop turning, 75% RH' },
    { key: 'DAY_25', day: 'Day 25', title: 'Pipping Stage', desc: 'Air cell breach' },
    { key: 'HATCHED', day: 'Day 28', title: 'Hatch Harvest', desc: 'Duckling takeoff' },
  ];

  const getStageIndex = (stage: BatchStage) => {
    switch (stage) {
      case 'SETTING': return 0;
      case 'DAY_10': return 1;
      case 'DAY_18': return 2;
      case 'DAY_25': return 3;
      case 'HATCHED':
      case 'COMPLETED': return 4;
      default: return 0;
    }
  };

  const currentIndex = getStageIndex(currentStage);

  return (
    <div className="w-full py-4">
      <div className="relative flex items-center justify-between">
        {/* Background Track Line */}
        <div className="absolute top-4 left-6 right-6 h-1 -translate-y-1/2 bg-slate-200 z-0" />

        {/* Active Track Line */}
        <div
          className="absolute top-4 left-6 h-1 -translate-y-1/2 bg-[#800000] z-0 transition-all duration-300"
          style={{ width: `${(currentIndex / (stages.length - 1)) * 100}%` }}
        />

        {stages.map((st, idx) => {
          const isCompleted = idx < currentIndex || currentStage === 'HATCHED' || currentStage === 'COMPLETED';
          const isCurrent = idx === currentIndex && currentStage !== 'HATCHED' && currentStage !== 'COMPLETED';

          let circleStyle = "bg-white text-slate-400 border-slate-300";
          if (isCompleted) {
            circleStyle = "bg-[#800000] text-white border-[#800000]";
          } else if (isCurrent) {
            circleStyle = "bg-white text-[#800000] border-[#800000] ring-4 ring-maroon-100";
          }

          return (
            <div key={st.key} className="relative z-10 flex flex-col items-center text-center max-w-[90px]">
              <div
                className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-all shadow-xs ${circleStyle}`}
              >
                {isCompleted ? <Check className="w-4 h-4" /> : idx + 1}
              </div>
              <span className="mt-2 text-xs font-bold text-[#0F172A]">
                {st.day}
              </span>
              <span className="text-[11px] font-semibold text-slate-700 leading-tight">
                {st.title}
              </span>
              <span className="text-[10px] text-slate-500 hidden sm:block mt-0.5">
                {st.desc}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
