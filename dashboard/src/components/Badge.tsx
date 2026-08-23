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
          <span className="inline-flex items-center gap-2 w-32 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 shrink-0" />
            <span>Fertile</span>
          </span>
        );
      case 'INFERTILE':
        return (
          <span className="inline-flex items-center gap-2 w-32 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-900 border border-amber-300">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-600 shrink-0" />
            <span>Infertile</span>
          </span>
        );
      case 'ABNORMAL':
        return (
          <span className="inline-flex items-center gap-2 w-32 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-600 shrink-0" />
            <span>Abnormal</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center w-32 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">
            {value}
          </span>
        );
    }
  }

  if (type === 'stage') {
    switch (value) {
      case 'SETTING':
        return <span className="inline-flex items-center w-36 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">Day 0 (Setting)</span>;
      case 'DAY_10':
        return <span className="inline-flex items-center w-36 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-900 border border-amber-200">Day 10 (1st Candle)</span>;
      case 'DAY_18':
        return <span className="inline-flex items-center w-36 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">Day 18 (Transfer)</span>;
      case 'DAY_25':
        return <span className="inline-flex items-center w-36 px-2.5 py-1 rounded-md text-xs font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200">Day 25 (Pipping)</span>;
      case 'HATCHED':
      case 'COMPLETED':
        return <span className="inline-flex items-center w-36 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">Day 28 (Hatched)</span>;
      default:
        return <span className="inline-flex items-center w-36 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">{value}</span>;
    }
  }

  if (type === 'device') {
    if (value === 'ONLINE') {
      return (
        <span className="inline-flex items-center gap-2 w-20 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 shrink-0" />
          <span>Online</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-2 w-20 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
        <span className="w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
        <span>Offline</span>
      </span>
    );
  }

  if (value === 'INCUBATING') {
    return <span className="inline-flex items-center justify-center w-24 py-1 rounded-md text-xs font-semibold bg-maroon-50 text-[#800000] border border-maroon-200">Incubating</span>;
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
