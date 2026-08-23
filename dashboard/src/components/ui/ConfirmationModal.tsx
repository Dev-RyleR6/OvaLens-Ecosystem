import React from 'react';
import { AlertTriangle, Info, CheckCircle2, ShieldAlert } from 'lucide-react';
import { Dialog } from './dialog';

export type ConfirmationVariant = 'primary' | 'warning' | 'danger';

interface DiffItem {
  label: string;
  oldValue: string | number;
  newValue: string | number;
}

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmationVariant;
  isLoading?: boolean;
  diffs?: DiffItem[];
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = 'Confirm & Save',
  cancelText = 'Cancel',
  variant = 'primary',
  isLoading = false,
  diffs = [],
}) => {
  const getIcon = () => {
    switch (variant) {
      case 'danger':
        return <ShieldAlert className="w-5 h-5 text-rose-700" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-amber-700" />;
      case 'primary':
      default:
        return <Info className="w-5 h-5 text-[#800000]" />;
    }
  };

  const getConfirmButtonClasses = () => {
    switch (variant) {
      case 'danger':
        return 'bg-rose-600 hover:bg-rose-700 text-white';
      case 'warning':
        return 'bg-amber-600 hover:bg-amber-700 text-white';
      case 'primary':
      default:
        return 'bg-[#800000] hover:bg-[#6B0000] text-white';
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} maxWidth="max-w-md">
      <div className="space-y-4">
        {/* Header Icon + Title */}
        <div className="flex items-start gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
              variant === 'danger'
                ? 'bg-rose-100 border border-rose-200'
                : variant === 'warning'
                ? 'bg-amber-100 border border-amber-200'
                : 'bg-maroon-50 border border-maroon-200'
            }`}
          >
            {getIcon()}
          </div>
          <div>
            <h3 className="text-base font-bold text-[#0F172A]">{title}</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">{description}</p>
          </div>
        </div>

        {/* Change Diff Summary (if provided) */}
        {diffs.length > 0 && (
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
            <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px] block">
              Parameter Changes to Apply
            </span>
            <div className="divide-y divide-slate-200">
              {diffs.map((diff, idx) => (
                <div key={idx} className="py-1.5 flex items-center justify-between">
                  <span className="font-medium text-slate-600">{diff.label}</span>
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-slate-400 line-through">{diff.oldValue}</span>
                    <span className="text-slate-400">→</span>
                    <span className="font-bold text-[#800000]">{diff.newValue}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer disabled:opacity-50"
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 rounded-lg text-xs font-bold shadow-xs transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5 ${getConfirmButtonClasses()}`}
          >
            {isLoading ? (
              <span>Saving...</span>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{confirmText}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </Dialog>
  );
};
