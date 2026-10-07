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
  highlightColor?: 'maroon' | 'green' | 'amber' | 'blue';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  unit,
  icon: Icon,
  trend,
  highlightColor = 'maroon',
}) => {
  let iconBg = "bg-maroon-50 text-brand border border-maroon-200/60";

  if (highlightColor === 'green') {
    iconBg = "bg-emerald-50 text-emerald-700 border border-emerald-200/60";
  } else if (highlightColor === 'amber') {
    iconBg = "bg-amber-50 text-amber-700 border border-amber-200/60";
  } else if (highlightColor === 'blue') {
    iconBg = "bg-blue-50 text-blue-700 border border-blue-200/60";
  }

  return (
    <div className="bg-card border border-border rounded-xl p-5 min-w-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{title}</p>
          <div className="mt-2 flex flex-wrap items-baseline gap-1.5">
            <span className="text-2xl font-semibold tracking-tight text-foreground break-words tabular-nums">
              {value}
            </span>
            {unit && <span className="text-xs font-semibold text-slate-500">{unit}</span>}
          </div>
        </div>

        {Icon && (
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${iconBg}  shrink-0`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-3.5 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
          {subtitle && <span className="text-slate-600 font-medium text-[11px] break-words">{subtitle}</span>}
          {trend && (
            <span
              className={`font-bold ml-auto flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded ${
                trend.isPositive ? 'text-emerald-700 bg-emerald-50' : 'text-rose-700 bg-rose-50'
              }`}
            >
              {trend.isPositive ? '↑' : '↓'} {trend.value}
              {trend.label && <span className="text-slate-400 font-normal ml-1">({trend.label})</span>}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
