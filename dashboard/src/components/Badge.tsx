import React from 'react';
import { FertilityClass, BatchStage, BatchStatus, DeviceStatus } from '../types';

interface BadgeProps {
  type?: 'fertility' | 'stage' | 'status' | 'device';
  value: FertilityClass | BatchStage | BatchStatus | DeviceStatus | string;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ type = 'status', value }) => {
  if (type === 'fertility') {
    switch (value) {
      case 'FERTILE':
        return (
          <span className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 shrink-0" />
            <span>Fertile</span>
          </span>
        );
      case 'INFERTILE':
        return (
          <span className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-900 border border-amber-300">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-600 shrink-0" />
            <span>Infertile</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">
            {value}
          </span>
        );
    }
  }

  if (type === 'stage') {
    switch (value) {
      case 'SETTING':
        return <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">Day 0 (Setting)</span>;
      case 'DAY_10':
        return <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-900 border border-amber-200">Day 10 (Candling)</span>;
      case 'HATCHED':
      case 'COMPLETED':
        return <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">Day 28 (Hatched)</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">{value}</span>;
    }
  }

  if (type === 'device') {
    const labels: Record<string, string> = { ONLINE: 'App online', SCANNING: 'Scanning', OFFLINE: 'Offline', ERROR: 'Error', STALE: 'Offline · heartbeat expired', UNKNOWN: 'Status unknown' };
    const classes = value === 'ONLINE' || value === 'SCANNING'
      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
      : value === 'ERROR' ? 'bg-red-50 text-red-800 border-red-200' : 'bg-slate-50 text-slate-700 border-slate-200';
    return <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium border whitespace-nowrap ${classes}`}>{labels[value] || value}</span>;
  }

  if (value === 'INCUBATING') {
    return <span className="inline-flex items-center justify-center w-24 py-1 rounded-md text-xs font-semibold bg-maroon-50 text-brand border border-maroon-200">Incubating</span>;
  }
  if (value === 'COMPLETED') {
    return <span className="inline-flex items-center justify-center w-24 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">Completed</span>;
  }

  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">
      {value}
    </span>
  );
};
