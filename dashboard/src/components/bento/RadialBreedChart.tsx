import React, { useState } from 'react';
import { ChevronDown, TrendingUp } from 'lucide-react';
import { ResponsiveContainer, RadialBarChart, RadialBar, Tooltip } from 'recharts';

interface RadialBreedChartProps {
  kayumanggiPct?: number;
  itimPct?: number;
  khakiPct?: number;
  projectedGrowthPhp?: number;
}

export const RadialBreedChart: React.FC<RadialBreedChartProps> = ({
  kayumanggiPct = 91.2,
  itimPct = 87.5,
  khakiPct = 84.8,
  projectedGrowthPhp = 12500,
}) => {
  const [period, setPeriod] = useState<'Monthly' | 'Batch'>('Monthly');

  const radialData = [
    { name: 'Khaki Campbell', value: khakiPct, fill: '#06B6D4' },
    { name: 'Itim (Native)', value: itimPct, fill: '#10B981' },
    { name: 'Kayumanggi', value: kayumanggiPct, fill: '#F59E0B' },
  ];

  return (
    <div className="bento-card p-5 flex flex-col justify-between h-full">
      {/* Card Header */}
      <div>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">
            Smart Breed & Viability Breakdown
          </h3>
          
          {/* Period Dropdown */}
          <div className="relative inline-block">
            <button
              onClick={() => setPeriod(prev => prev === 'Monthly' ? 'Batch' : 'Monthly')}
              className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 bg-[#161B27] px-2.5 py-1 rounded-lg border border-[#222A3B] transition-colors cursor-pointer"
            >
              <span>{period}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>
          </div>
        </div>

        {/* Concentric Radial Ring Chart + Legend */}
        <div className="mt-2 grid grid-cols-12 items-center gap-2">
          {/* Radial Chart Visual */}
          <div className="col-span-7 h-32 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                cx="50%"
                cy="50%"
                innerRadius="35%"
                outerRadius="100%"
                barSize={7}
                data={radialData}
                startAngle={90}
                endAngle={-270}
              >
                <RadialBar
                  background={{ fill: '#161B27' }}
                  dataKey="value"
                  cornerRadius={10}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#121620',
                    borderColor: '#1F2636',
                    borderRadius: '0.75rem',
                    fontSize: '11px',
                    color: '#fff'
                  }}
                  formatter={(val: any, name: any) => [`${val}% Viability`, name]}
                />
              </RadialBarChart>
            </ResponsiveContainer>
          </div>

          {/* Legend Items */}
          <div className="col-span-5 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                Kayumanggi
              </span>
              <span className="font-bold text-white">40%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Itim (Native)
              </span>
              <span className="font-bold text-white">35%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                Khaki Campbell
              </span>
              <span className="font-bold text-white">25%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Glowing Survival Waveform Footer */}
      <div className="mt-2 pt-3 border-t border-[#1F2636] flex items-center justify-between">
        <div>
          <span className="text-xs text-slate-400 block font-medium">Hatch Harvest Projected</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-sm font-bold text-white">
              ₱{projectedGrowthPhp.toLocaleString()}
            </span>
            <span className="text-[10px] font-semibold text-emerald-400">
              +6.2% growth
            </span>
          </div>
        </div>

        {/* Glowing SVG Multi-Color Waveform */}
        <div className="w-28 h-8">
          <svg viewBox="0 0 120 30" className="w-full h-full filter drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]">
            <path
              d="M 0,20 Q 20,28 40,15 T 80,5 T 120,22"
              fill="none"
              stroke="#10B981"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <path
              d="M 0,25 Q 30,10 60,18 T 120,12"
              fill="none"
              stroke="#06B6D4"
              strokeWidth="1.5"
              strokeLinecap="round"
              opacity="0.8"
            />
          </svg>
        </div>
      </div>
    </div>
  );
};
