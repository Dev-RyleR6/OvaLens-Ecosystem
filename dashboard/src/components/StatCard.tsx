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
  let iconBg = "bg-maroon-50 text-[#800000]";
  if (highlightColor === 'green') iconBg = "bg-emerald-50 text-emerald-700";
  if (highlightColor === 'amber') iconBg = "bg-amber-50 text-amber-700";
  if (highlightColor === 'blue') iconBg = "bg-blue-50 text-blue-700";

  return (
    <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs hover:border-slate-300 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-bold tracking-tight text-[#0F172A]">
              {value}
            </span>
            {unit && <span className="text-xs font-medium text-slate-500">{unit}</span>}
          </div>
        </div>

        {Icon && (
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${iconBg}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          {subtitle && <span className="text-slate-600 font-medium">{subtitle}</span>}
          {trend && (
            <span
              className={`font-semibold ml-auto flex items-center gap-0.5 ${
                trend.isPositive ? 'text-emerald-700' : 'text-rose-700'
              }`}
            >
              {trend.isPositive ? '↑' : '↓'} {trend.value}
              {trend.label && <span className="text-slate-500 font-normal ml-1">({trend.label})</span>}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
