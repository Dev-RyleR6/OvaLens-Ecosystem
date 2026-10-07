import React from 'react';
import { RefreshCw, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DataUnavailableStateProps {
  title?: string; description?: string; onRetry?: () => void | Promise<void>;
  isRetrying?: boolean; className?: string; compact?: boolean;
}

export const DataUnavailableState: React.FC<DataUnavailableStateProps> = ({
  title = 'Records unavailable', description = 'We could not load these records. Check your connection and try again.',
  onRetry, isRetrying = false, className, compact = false,
}) => (
  <div role="alert" className={cn('border border-slate-200 rounded-xl bg-card', compact ? 'p-4' : 'p-6 sm:p-8', className)}>
    <div className="flex items-start gap-3"><WifiOff className="w-5 h-5 text-slate-500 shrink-0 mt-1" aria-hidden="true" /><div className="space-y-2"><h2 className="font-semibold text-foreground">{title}</h2><p className="text-slate-600 max-w-prose">{description}</p>{onRetry && <button onClick={() => { void onRetry(); }} disabled={isRetrying} className="inline-flex gap-2 items-center border border-slate-300 rounded-lg px-3 py-2 mt-2"><RefreshCw className="w-4 h-4" />{isRetrying ? 'Trying again…' : 'Try again'}</button>}</div></div>
  </div>
);
export default DataUnavailableState;
