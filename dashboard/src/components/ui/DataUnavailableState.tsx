import React from 'react';
import { WifiOff, RefreshCw, AlertCircle, ServerCrash } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DataUnavailableStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void | Promise<void>;
  isRetrying?: boolean;
  className?: string;
  compact?: boolean;
}

export const DataUnavailableState: React.FC<DataUnavailableStateProps> = ({
  title = 'Service Data Unavailable',
  description = 'Unable to fetch real-time data from the FastAPI backend. Verify that the PostgreSQL database and backend server are running.',
  onRetry,
  isRetrying = false,
  className,
  compact = false,
}) => {
  if (compact) {
    return (
      <div
        className={cn(
          'p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-3 text-xs text-slate-600',
          className
        )}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <div className="truncate">
            <span className="font-semibold text-slate-800">{title}: </span>
            <span className="text-slate-500">{description}</span>
          </div>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold shadow-2xs transition-all flex items-center gap-1.5 flex-shrink-0 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={cn('w-3 h-3', isRetrying && 'animate-spin')} />
            <span>{isRetrying ? 'Retrying...' : 'Retry'}</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'bg-white border border-slate-200/90 rounded-2xl p-8 text-center max-w-lg mx-auto my-8 shadow-xs space-y-4 font-sans',
        className
      )}
    >
      <div className="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 text-amber-700 mx-auto flex items-center justify-center shadow-2xs">
        <WifiOff className="w-6 h-6" />
      </div>

      <div className="space-y-1.5">
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 inline-block">
          503 Telemetry Offline • Service Unreachable
        </span>
        <h3 className="text-base font-bold text-slate-900 tracking-tight">
          {title}
        </h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
          {description}
        </p>
      </div>

      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-left text-xs font-mono space-y-1 text-slate-600">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Endpoint:</span>
          <span className="font-semibold text-slate-800">/api/v1/*</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Database:</span>
          <span className="font-semibold text-slate-800">PostgreSQL (ovalens_db:5432)</span>
        </div>
      </div>

      {onRetry && (
        <div className="pt-2">
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isRetrying && 'animate-spin')} />
            <span>{isRetrying ? 'Attempting Reconnection...' : 'Retry Connection'}</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default DataUnavailableState;
