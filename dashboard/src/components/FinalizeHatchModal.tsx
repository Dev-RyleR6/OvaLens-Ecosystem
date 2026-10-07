import { CloseButton } from './ui/CloseButton';
import { useDialogAccessibility } from '@/hooks/useDialogAccessibility';
import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Award, CheckCircle2, AlertCircle } from 'lucide-react';
import { apiClient } from '../api/client';
import { BatchSummary } from '../types';
import { useModalAnimation } from '@/hooks/useModalAnimation';
import { cn } from '@/lib/utils';

interface FinalizeHatchModalProps {
  batch: BatchSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const FinalizeHatchModal: React.FC<FinalizeHatchModalProps> = ({
  batch,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const lastBatchRef = React.useRef(batch);
  if (batch) lastBatchRef.current = batch;
  const displayBatch = batch || lastBatchRef.current;

  const [hatchedCount, setHatchedCount] = useState<number>(0);
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const { shouldRender, isClosing } = useModalAnimation(isOpen, 220);
  const dialogRef = useDialogAccessibility(isOpen && shouldRender, () => { if (!isSubmitting) onClose(); }, 'Record hatch results');

  useEffect(() => { if (isOpen) { setHatchedCount(batch?.hatched_count ?? 0); setNotes(''); setError(null); } }, [isOpen, batch?.batch_id, batch?.hatched_count]);

  if (!shouldRender || !displayBatch) return null;

  const initialCount = displayBatch.initial_egg_count;
  const unhatchedCount = Math.max(0, initialCount - Number(hatchedCount || 0));
  const hatchRate = initialCount > 0 ? ((Number(hatchedCount || 0) / initialCount) * 100).toFixed(1) : '0.0';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    if (hatchedCount < 0) {
      setError('Hatched count cannot be negative.');
      return;
    }
    if (hatchedCount > initialCount) {
      setError(`Hatched count cannot exceed initial eggs set (${initialCount}).`);
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await apiClient.finalizeBatchHatch(displayBatch.batch_id, {
        hatched_count: Number(hatchedCount),
        unhatched_count: unhatchedCount,
        notes: notes || undefined,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to finalize hatch trial.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return createPortal(
    <div ref={dialogRef} className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-slate-900/65  transition-opacity",
          isClosing ? "animate-modal-backdrop-exit" : "animate-modal-backdrop"
        )}
        onClick={() => { if (!isSubmitting) onClose(); }}
      />

      <div
        className={cn(
          "bg-card border border-slate-200/90 rounded-2xl shadow-2xl max-w-md w-full min-w-0 max-h-[calc(100dvh-1.5rem)] sm:max-h-[90vh] flex flex-col overflow-hidden z-10 my-auto",
          isClosing ? "animate-modal-content-exit" : "animate-modal-content"
        )}
      >
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-100 flex items-start justify-between gap-2 bg-card flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 shrink-0 rounded-xl bg-[#800000]/10 text-brand flex items-center justify-center font-semibold">
              <Award aria-hidden="true" className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-slate-900">
                Finalize Day 28 Hatch Trial
              </h2>
              <p className="text-xs text-slate-500 break-words">
                Batch: {displayBatch.batch_code} ({displayBatch.breed})
              </p>
            </div>
          </div>

          <CloseButton type="button" aria-label="Close hatch results dialog" disabled={isSubmitting} onClick={() => { if (!isSubmitting) onClose(); }} />
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="min-h-0 overflow-y-auto overscroll-contain p-4 sm:p-5 space-y-4" aria-busy={isSubmitting}>
          {error && (
            <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs font-semibold text-red-700 flex items-center gap-2">
              <AlertCircle aria-hidden="true" className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
            <div className="flex flex-wrap justify-between gap-2 text-slate-600">
              <span>Initial Eggs Set:</span>
              <span className="font-bold text-slate-900">{initialCount} eggs</span>
            </div>
            <div className="flex flex-wrap justify-between gap-2 text-slate-600">
              <span>Day 10 Fertile Active:</span>
              <span className="font-bold text-emerald-700">{displayBatch.fertile_count} eggs</span>
            </div>
            <div className="flex flex-wrap justify-between gap-2 text-slate-600 border-t border-slate-200 pt-1.5">
              <span>Calculated Hatchability:</span>
              <span className="font-bold text-brand">{hatchRate}%</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="finalizehatchmodal-field-1" className="text-xs font-bold text-slate-700">
              Total Hatched Healthy Ducklings *
            </label>
            <input id="finalizehatchmodal-field-1"
              type="number"
              min={0}
              max={initialCount}
              required
              value={hatchedCount}
              onChange={(e) => setHatchedCount(Number(e.target.value))}
              placeholder="e.g. 450"
              className="w-full min-w-0 h-11 px-3 bg-card border border-slate-200 rounded-lg text-sm text-slate-900 font-bold focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="finalizehatchmodal-field-2" className="text-xs font-semibold text-slate-700">
              Unhatched / Dead-in-Shell (Auto-calculated)
            </label>
            <input id="finalizehatchmodal-field-2"
              type="number"
              disabled
              value={unhatchedCount}
              className="w-full min-w-0 h-11 px-3 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-500 font-medium cursor-not-allowed"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="finalizehatchmodal-field-3" className="text-xs font-semibold text-slate-700">
              Hatch Notes / Observation (Optional)
            </label>
            <textarea id="finalizehatchmodal-field-3"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Successful hatch, high duckling vigor, clean shell separation."
              className="w-full min-w-0 p-2.5 bg-card border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          {/* Action Buttons */}
          <div className="page-actions justify-end pt-3 border-t border-slate-100">
            <button
              type="button" disabled={isSubmitting}
              onClick={() => { if (!isSubmitting) onClose(); }}
              className="secondary-action"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="primary-action"
            >
              <CheckCircle2 aria-hidden="true" className="w-4 h-4" />
              {isSubmitting ? 'Finalizing...' : 'Confirm & Complete Batch'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
};
