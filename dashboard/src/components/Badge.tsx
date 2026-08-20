import React from 'react';
import { FertilityClass, BatchStage, BatchStatus, DeviceStatus } from '../types';

interface BadgeProps {
  type: 'fertility' | 'stage' | 'status' | 'device';
  value: FertilityClass | BatchStage | BatchStatus | DeviceStatus | string;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ type, value, size = 'md' }) => {
  const isSm = size === 'sm';
  const sizeClasses = isSm ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  if (type === 'fertility') {
    switch (value) {
      case 'FERTILE':
        return (
          <span className={`inline-flex items-center gap-1.5 font-mono font-bold tracking-wider rounded border bg-emerald-950/70 border-emerald-500/50 text-emerald-400 ${sizeClasses}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#10B981]" />
            FERTILE (ACCEPT)
          </span>
        );
      case 'INFERTILE':
        return (
          <span className={`inline-flex items-center gap-1.5 font-mono font-bold tracking-wider rounded border bg-amber-950/70 border-amber-500/50 text-amber-300 ${sizeClasses}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_#F59E0B]" />
            INFERTILE (PENOY)
          </span>
        );
      case 'ABNORMAL':
        return (
          <span className={`inline-flex items-center gap-1.5 font-mono font-bold tracking-wider rounded border bg-rose-950/70 border-rose-500/50 text-rose-300 ${sizeClasses}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shadow-[0_0_6px_#EF4444]" />
            ABNORMAL (DEAD)
          </span>
        );
      default:
        return (
          <span className={`inline-flex items-center gap-1 font-mono font-semibold rounded border bg-slate-900 border-slate-700 text-slate-400 ${sizeClasses}`}>
            {value}
          </span>
        );
    }
  }

  if (type === 'stage') {
    switch (value) {
      case 'DAY_10':
        return (
          <span className={`inline-flex items-center gap-1.5 font-mono font-semibold rounded border bg-amber-950/50 border-amber-600/40 text-amber-300 ${sizeClasses}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-led-pulse" />
            DAY 10 (1ST CANDLE)
          </span>
        );
      case 'DAY_18':
        return (
          <span className={`inline-flex items-center gap-1.5 font-mono font-semibold rounded border bg-cyan-950/50 border-cyan-600/40 text-cyan-300 ${sizeClasses}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            DAY 18 (TRANSFER)
          </span>
        );
      case 'DAY_25':
        return (
          <span className={`inline-flex items-center gap-1.5 font-mono font-semibold rounded border bg-indigo-950/50 border-indigo-600/40 text-indigo-300 ${sizeClasses}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
            DAY 25 (PIPPING)
          </span>
        );
      case 'HATCHED':
        return (
          <span className={`inline-flex items-center gap-1.5 font-mono font-bold rounded border bg-emerald-950/70 border-emerald-500/50 text-emerald-300 ${sizeClasses}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            HATCHED (DAY 28)
          </span>
        );
      default:
        return (
          <span className={`inline-flex items-center gap-1 font-mono rounded border bg-slate-900 border-slate-700 text-slate-400 ${sizeClasses}`}>
            {value}
          </span>
        );
    }
  }

  if (type === 'device') {
    if (value === 'ONLINE') {
      return (
        <span className={`inline-flex items-center gap-1.5 font-mono font-bold rounded border bg-emerald-950/80 border-emerald-500/60 text-emerald-400 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-led-pulse shadow-[0_0_6px_#10B981]" />
          TELEMETRY ACTIVE
        </span>
      );
    }
    return (
      <span className={`inline-flex items-center gap-1.5 font-mono font-semibold rounded border bg-slate-900 border-slate-700 text-slate-400 ${sizeClasses}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
        OFFLINE
      </span>
    );
  }

  // Generic status
  if (value === 'INCUBATING') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-mono font-semibold rounded border bg-amber-950/60 border-amber-600/50 text-amber-300 ${sizeClasses}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-led-pulse" />
        INCUBATING
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1 font-mono rounded border bg-slate-900 border-slate-700 text-slate-300 ${sizeClasses}`}>
      {value}
    </span>
  );
};
