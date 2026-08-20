import React from 'react';
import { BatchStage } from '../types';
import { Check } from 'lucide-react';

interface BatchProgressTimelineProps {
  currentStage: BatchStage;
  setDate: string;
}

export const BatchProgressTimeline: React.FC<BatchProgressTimelineProps> = ({ currentStage }) => {
  const stages = [
    { key: 'SETTING', label: 'Day 0', title: 'Set' },
    { key: 'DAY_10', label: 'Day 10', title: '1st Candle (Penoy)' },
    { key: 'DAY_18', label: 'Day 18', title: 'Hatcher Transfer' },
    { key: 'DAY_25', label: 'Day 25', title: 'Pipping' },
    { key: 'HATCHED', label: 'Day 28', title: 'Hatch' },
  ];

  const getStageIndex = (stage: BatchStage) => {
    switch (stage) {
      case 'SETTING': return 0;
      case 'DAY_10': return 1;
      case 'DAY_18': return 2;
      case 'DAY_25': return 3;
      case 'HATCHED': return 4;
      case 'COMPLETED': return 4;
      default: return 0;
    }
  };

  const currentIndex = getStageIndex(currentStage);

  return (
    <div className="w-full py-3">
      <div className="relative flex items-center justify-between">
        {/* Track Line */}
        <div className="absolute top-3.5 left-3 right-3 h-0.5 -translate-y-1/2 bg-muted z-0" />
        
        {/* Active Fill */}
        <div
          className="absolute top-3.5 left-3 h-0.5 -translate-y-1/2 bg-[#800000] z-0 transition-all duration-300"
          style={{ width: `${Math.max(0, (currentIndex / (stages.length - 1)) * 100)}%` }}
        />

        {stages.map((st, idx) => {
          const isCompleted = idx < currentIndex || currentStage === 'HATCHED' || currentStage === 'COMPLETED';
          const isCurrent = idx === currentIndex && currentStage !== 'HATCHED' && currentStage !== 'COMPLETED';

          let circleStyle = "bg-muted text-muted-foreground border-transparent";
          if (isCompleted) {
            circleStyle = "bg-[#800000] text-white border-[#800000]";
          } else if (isCurrent) {
            circleStyle = "bg-background text-[#800000] border-[#800000] ring-2 ring-[#800000]/20";
          }

          return (
            <div key={st.key} className="relative z-10 flex flex-col items-center">
              <div
                className={`w-7 h-7 rounded-full border flex items-center justify-center text-xs font-semibold transition-all ${circleStyle}`}
              >
                {isCompleted ? <Check className="w-3.5 h-3.5" /> : idx + 1}
              </div>
              <span className="mt-1.5 text-xs font-medium text-foreground">
                {st.label}
              </span>
              <span className="text-[10px] text-muted-foreground hidden sm:block">
                {st.title}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
