import React, { useState } from 'react';
import { X, Award, CheckCircle2, AlertCircle } from 'lucide-react';
import { apiClient } from '../api/client';
import { BatchSummary } from '../types';

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
  const [hatchedCount, setHatchedCount] = useState<number>(0);
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !batch) return null;

  const initialCount = batch.initial_egg_count || 500;
  const unhatchedCount = Math.max(0, initialCount - Number(hatchedCount || 0));
  const hatchRate = initialCount > 0 ? ((Number(hatchedCount || 0) / initialCount) * 100).toFixed(1) : '0.0';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
      await apiClient.finalizeBatchHatch(batch.batch_id, {
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#800000]/10 text-[#800000] flex items-center justify-center font-black">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Finalize Day 28 Hatch Trial
              </h2>
              <p className="text-[11px] text-slate-500">
                Batch: {batch.batch_code} ({batch.breed})
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs font-semibold text-red-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
            <div className="flex justify-between text-slate-600">
              <span>Initial Eggs Set:</span>
              <span className="font-bold text-slate-900">{initialCount} eggs</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Day 10 Fertile Active:</span>
              <span className="font-bold text-emerald-700">{batch.fertile_count || batch.initial_egg_count} eggs</span>
            </div>
            <div className="flex justify-between text-slate-600 border-t border-slate-200 pt-1.5">
              <span>Calculated Hatchability:</span>
              <span className="font-bold text-[#800000]">{hatchRate}%</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">
              Total Hatched Healthy Ducklings *
            </label>
            <input
              type="number"
              min={0}
              max={initialCount}
              required
              value={hatchedCount}
              onChange={(e) => setHatchedCount(Number(e.target.value))}
              placeholder="e.g. 450"
              className="w-full h-10 px-3 bg-white border border-slate-200 rounded-lg text-sm text-slate-900 font-bold focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700">
              Unhatched / Dead-in-Shell (Auto-calculated)
            </label>
            <input
              type="number"
              disabled
              value={unhatchedCount}
              className="w-full h-9 px-3 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-500 font-medium cursor-not-allowed"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700">
              Hatch Notes / Observation (Optional)
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Successful hatch, high duckling vigor, clean shell separation."
              className="w-full p-2.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? 'Finalizing...' : 'Confirm & Complete Batch'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
