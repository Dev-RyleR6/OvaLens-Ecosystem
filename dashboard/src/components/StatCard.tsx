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
  let iconBg = "bg-maroon-50/80 text-[#800000] border-maroon-100 group-hover:bg-[#800000] group-hover:text-white";
  let topAccent = "bg-[#800000]";
  let borderHover = "hover:border-maroon-200";

  if (highlightColor === 'green') {
    iconBg = "bg-emerald-50 text-emerald-700 border-emerald-100 group-hover:bg-emerald-600 group-hover:text-white";
    topAccent = "bg-emerald-600";
    borderHover = "hover:border-emerald-200";
  } else if (highlightColor === 'amber') {
    iconBg = "bg-amber-50 text-amber-700 border-amber-100 group-hover:bg-amber-600 group-hover:text-white";
    topAccent = "bg-amber-600";
    borderHover = "hover:border-amber-200";
  } else if (highlightColor === 'blue') {
    iconBg = "bg-blue-50 text-blue-700 border-blue-100 group-hover:bg-blue-600 group-hover:text-white";
    topAccent = "bg-blue-600";
    borderHover = "hover:border-blue-200";
  }

  return (
    <div className={`group relative bg-white border border-[#E2E8F0] ${borderHover} rounded-xl p-5 shadow-xs hover-lift transition-all duration-200 overflow-hidden`}>
      {/* Subtle Top Accent Line */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${topAccent} opacity-80`} />

      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{title}</p>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold tracking-tight text-[#0F172A]">
              {value}
            </span>
            {unit && <span className="text-xs font-semibold text-slate-500">{unit}</span>}
          </div>
        </div>

        {Icon && (
          <div className={`w-10 h-10 rounded-xl border flex items-center justify-center transition-all duration-200 ${iconBg}`}>
            <Icon className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          {subtitle && <span className="text-slate-600 font-medium text-[11px]">{subtitle}</span>}
          {trend && (
            <span
              className={`font-bold ml-auto flex items-center gap-0.5 text-xs ${
                trend.isPositive ? 'text-emerald-700' : 'text-rose-700'
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
