import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  colorScheme?: 'maroon' | 'green' | 'amber' | 'blue';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  colorScheme = 'maroon'
}) => {
  const iconBgMap = {
    maroon: 'bg-[#800000]/20 text-[#EAB308] border-[#800000]/40',
    green: 'bg-emerald-950/40 text-emerald-400 border-emerald-800/40',
    amber: 'bg-amber-950/40 text-amber-400 border-amber-800/40',
    blue: 'bg-blue-950/40 text-blue-400 border-blue-800/40',
  };

  return (
    <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden transition-all duration-200 hover:border-slate-700 hover:shadow-xl">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</p>
          <h3 className="text-2xl font-bold text-slate-100 mt-1">{value}</h3>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-lg border ${iconBgMap[colorScheme]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
      {trend && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          <span className={trend.isPositive ? 'text-emerald-400 font-medium' : 'text-red-400 font-medium'}>
            {trend.value}
          </span>
          <span className="text-slate-500">vs last milestone</span>
        </div>
      )}
    </div>
  );
};
