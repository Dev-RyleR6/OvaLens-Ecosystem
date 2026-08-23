import React from 'react';
import { Layers, Plus, LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: LucideIcon;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Records Found',
  description = 'There are no active records in the PostgreSQL database matching your criteria.',
  icon: Icon = Layers,
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        'bg-white border border-slate-200/80 rounded-2xl p-8 sm:p-12 text-center max-w-md mx-auto my-6 shadow-2xs space-y-4 font-sans',
        className
      )}
    >
      <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-200 text-slate-400 mx-auto flex items-center justify-center shadow-2xs">
        <Icon className="w-6 h-6 text-slate-500" />
      </div>

      <div className="space-y-1">
        <h3 className="text-sm font-bold text-slate-900 tracking-tight">
          {title}
        </h3>
        <p className="text-xs text-slate-500 max-w-xs mx-auto leading-relaxed">
          {description}
        </p>
      </div>

      {actionLabel && onAction && (
        <div className="pt-2">
          <button
            onClick={onAction}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer btn-press"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{actionLabel}</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default EmptyState;
