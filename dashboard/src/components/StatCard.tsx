import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  unit?: string;
  icon?: LucideIcon;
  trend?: {
    value: number | string;
    isPositive: boolean;
    label?: string;
  };
  accentColor?: 'maroon' | 'green' | 'amber' | 'cyan' | 'red';
  baseline?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  unit,
  icon: Icon,
  trend,
  accentColor = 'maroon',
  baseline,
}) => {
  const accentBorderMap = {
    maroon: 'border-l-[#800000]',
    green: 'border-l-emerald-500',
    amber: 'border-l-amber-500',
    cyan: 'border-l-cyan-500',
    red: 'border-l-rose-500',
  };

  const accentBadgeMap = {
    maroon: 'text-amber-300 bg-[#800000]/20 border-[#800000]/40',
    green: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40',
    amber: 'text-amber-300 bg-amber-950/40 border-amber-800/40',
    cyan: 'text-cyan-300 bg-cyan-950/40 border-cyan-800/40',
    red: 'text-rose-400 bg-rose-950/40 border-rose-800/40',
  };

  return (
    <div className={`bg-obsidian-900 border border-obsidian-700/70 border-l-4 ${accentBorderMap[accentColor]} rounded-lg p-4 shadow-lg relative overflow-hidden transition-all hover:border-obsidian-600`}>
      {/* Top Meta Line */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-display font-bold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {Icon && (
          <div className={`p-1 rounded border ${accentBadgeMap[accentColor]}`}>
            <Icon className="w-3.5 h-3.5" />
          </div>
        )}
      </div>

      {/* Main Metric Figure */}
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className="text-2xl lg:text-3xl font-mono font-black tracking-tight text-white tabular-nums">
          {value}
        </span>
        {unit && (
          <span className="text-xs font-mono font-bold text-slate-400">
            {unit}
          </span>
        )}
      </div>

      {/* Footer Info / Trend / Baseline */}
      <div className="mt-2.5 pt-2 border-t border-obsidian-800/80 flex items-center justify-between text-[10px]">
        {subtitle && (
          <span className="text-slate-400 font-medium truncate">
            {subtitle}
          </span>
        )}
        {trend && (
          <span className={`font-mono font-bold ml-auto flex items-center gap-0.5 ${trend.isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {trend.isPositive ? '↑' : '↓'} {trend.value}
            {trend.label && <span className="text-slate-500 font-normal ml-0.5">({trend.label})</span>}
          </span>
        )}
        {baseline && !trend && (
          <span className="text-slate-500 font-mono ml-auto">
            Base: {baseline}
          </span>
        )}
      </div>
    </div>
  );
};
