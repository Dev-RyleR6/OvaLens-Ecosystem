import React from 'react';
import { 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  Sparkles, 
  Egg, 
  Coins, 
  ShieldAlert, 
  Activity,
  ArrowUpRight
} from 'lucide-react';
import { BatchForecastResponse } from '../types';

interface BatchForecastCardProps {
  forecast: BatchForecastResponse | null;
  isLoading?: boolean;
}

export const BatchForecastCard: React.FC<BatchForecastCardProps> = ({ forecast, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-xl p-5  space-y-4">
        <div className="h-5 bg-slate-100 rounded w-1/3" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-20 bg-slate-50 rounded-lg" />
          <div className="h-20 bg-slate-50 rounded-lg" />
          <div className="h-20 bg-slate-50 rounded-lg" />
        </div>
      </div>
    );
  }

  if (!forecast) return null;

  const isOptimal = forecast.anomaly_status === 'OPTIMAL';
  const isWarning = forecast.anomaly_status === 'WARNING';
  const isCritical = forecast.anomaly_status === 'CRITICAL';

  return (
    <div className="bg-card border border-border rounded-xl p-5  space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 text-agri-green flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-foreground text-sm flex flex-wrap items-center gap-2">
              Day 28 Hatch Yield & Revenue Forecast
              <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                Estimate
              </span>
            </h3>
            <p className="text-[11px] text-slate-500">
              Model estimate using saved scans and fixed breed assumptions; not a measured hatch outcome.
            </p>
          </div>
        </div>

        {/* Anomaly Badge */}
        <div className="flex items-center gap-2 flex-wrap">
          {isOptimal && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold bg-emerald-50 border border-emerald-200 text-emerald-800">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              Optimal Progression
            </span>
          )}
          {isWarning && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold bg-amber-50 border border-amber-200 text-amber-800">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              Incubation Warning
            </span>
          )}
          {isCritical && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold bg-red-50 border border-red-200 text-red-800">
              <ShieldAlert className="w-3.5 h-3.5 text-red-600" />
              Critical Anomaly Detected
            </span>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-3.5">
        {/* Metric 1: Predicted Ducklings */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Projected Hatched</span>
            <Egg className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="flex flex-wrap items-baseline gap-1.5">
            <span className="text-xl font-semibold text-foreground tracking-tight">
              {forecast.predicted_hatched_count.toLocaleString()}
            </span>
            <span className="text-xs text-slate-500 font-semibold">ducklings</span>
          </div>
          <div className="text-[11px] text-emerald-700 font-semibold flex items-center gap-0.5">
            <ArrowUpRight className="w-3 h-3" />
            <span>{forecast.predicted_hatchability_rate}% est. hatchability</span>
          </div>
        </div>

        {/* Metric 2: Detected Fertility */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Detected Fertility</span>
            <Activity className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="flex flex-wrap items-baseline gap-1.5">
            <span className="text-xl font-semibold text-foreground tracking-tight">
              {forecast.detected_fertility_rate}%
            </span>
            <span className="text-[11px] text-slate-400">
              (vs {forecast.breed_baseline_fertility}% baseline)
            </span>
          </div>
          <div className="text-[11px] text-slate-500">
            {forecast.expected_embryo_viability_rate}% viability coefficient
          </div>
        </div>

        {/* Metric 3: Penoy Realized Revenue */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Estimated Penoy value</span>
            <Coins className="w-3.5 h-3.5 text-amber-500" />
          </div>
          <div className="flex flex-wrap items-baseline gap-1.5">
            <span className="text-xl font-semibold text-amber-800 tracking-tight">
              ₱{forecast.penoy_realized_revenue_php.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="text-[11px] text-slate-500">
            Estimate from classifications or breed assumptions
          </div>
        </div>

        {/* Metric 4: Total Projected Revenue */}
        <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200/80 space-y-1">
          <div className="flex items-center justify-between text-xs text-emerald-800 font-medium">
            <span>Total Forecasted Revenue</span>
            <TrendingUp className="w-3.5 h-3.5 text-emerald-700" />
          </div>
          <div className="flex flex-wrap items-baseline gap-1.5">
            <span className="text-xl font-semibold text-emerald-950 tracking-tight">
              ₱{forecast.projected_total_revenue_php.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="text-[11px] text-emerald-700 font-semibold">
            Ducklings: ₱{forecast.projected_duckling_revenue_php.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      {/* Advisory Notes */}
      {forecast.advisory_notes && forecast.advisory_notes.length > 0 && (
        <div className={`p-3 rounded-lg border text-xs leading-relaxed flex items-start gap-2.5 ${
          isCritical 
            ? 'bg-red-50/80 border-red-200 text-red-900' 
            : isWarning 
            ? 'bg-amber-50/80 border-amber-200 text-amber-900' 
            : 'bg-slate-50 border-slate-200 text-slate-700'
        }`}>
          {isCritical ? (
            <ShieldAlert className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          ) : isWarning ? (
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-agri-green shrink-0 mt-0.5" />
          )}
          <div className="space-y-1">
            <span className="font-bold block">Incubation Advisory & Diagnostic Insights:</span>
            <ul className="list-disc list-inside space-y-0.5 text-[11px]">
              {forecast.advisory_notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
