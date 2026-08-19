import React from 'react';
import { FertilityClass, BatchStage, BatchStatus, DeviceStatus } from '../types';

interface BadgeProps {
  type: 'fertility' | 'stage' | 'status' | 'device';
  value: string;
}

export const Badge: React.FC<BadgeProps> = ({ type, value }) => {
  if (type === 'fertility') {
    const val = value as FertilityClass;
    if (val === 'FERTILE') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-400"></span>
          FERTILE
        </span>
      );
    }
    if (val === 'INFERTILE') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-800/60">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-amber-400"></span>
          INFERTILE (PENOY)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950/80 text-red-400 border border-red-800/60">
        <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-red-400"></span>
        ABNORMAL / DEAD
      </span>
    );
  }

  if (type === 'stage') {
    const val = value as BatchStage;
    const colors: Record<BatchStage, string> = {
      SETTING: 'bg-blue-950 text-blue-400 border-blue-800',
      DAY_10: 'bg-amber-950 text-amber-400 border-amber-800',
      DAY_18: 'bg-purple-950 text-purple-400 border-purple-800',
      DAY_25: 'bg-indigo-950 text-indigo-400 border-indigo-800',
      HATCHED: 'bg-emerald-950 text-emerald-400 border-emerald-800',
      COMPLETED: 'bg-slate-800 text-slate-300 border-slate-700',
    };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium border ${colors[val] || 'bg-slate-800 text-slate-300 border-slate-700'}`}>
        {val.replace('_', ' ')}
      </span>
    );
  }

  if (type === 'status') {
    const val = value as BatchStatus;
    if (val === 'INCUBATING') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/70 text-blue-400 border border-blue-800/50">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-blue-400 animate-pulse"></span>
          INCUBATING
        </span>
      );
    }
    if (val === 'COMPLETED') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/70 text-emerald-400 border border-emerald-800/50">
          COMPLETED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
        {val}
      </span>
    );
  }

  if (type === 'device') {
    const val = value as DeviceStatus;
    if (val === 'ONLINE') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
          <span className="w-2 h-2 mr-1.5 rounded-full bg-emerald-400 animate-ping"></span>
          ONLINE
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
        <span className="w-2 h-2 mr-1.5 rounded-full bg-slate-500"></span>
        OFFLINE
      </span>
    );
  }

  return <span className="text-xs text-slate-400">{value}</span>;
};
