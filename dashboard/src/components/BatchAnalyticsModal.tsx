import React, { useState, useEffect } from 'react';
import {
  X,
  TrendingUp,
  Coins,
  Zap,
  Egg,
  Calendar,
  Layers,
  Activity,
  Award,
  CheckCircle2,
  Clock,
  User,
  PieChart as PieIcon,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { apiClient } from '../api/client';
import { BatchAnalyticsResponse } from '../types';

interface BatchAnalyticsModalProps {
  batchId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

const COLORS = ['#357a38', '#d97706', '#dc2626'];

export const BatchAnalyticsModal: React.FC<BatchAnalyticsModalProps> = ({
  batchId,
  isOpen,
  onClose,
}) => {
  const [data, setData] = useState<BatchAnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && batchId) {
      setIsLoading(true);
      apiClient
        .getBatchAnalytics(batchId)
        .then((res) => setData(res))
        .finally(() => setIsLoading(false));
    }
  }, [isOpen, batchId]);

  if (!isOpen || !batchId) return null;

  const pieData = data
    ? [
        { name: 'Fertile (Active)', value: data.fertile_day_10, color: '#357a38' },
        { name: 'Infertile (Penoy)', value: data.infertile_penoy_day_10, color: '#d97706' },
        { name: 'Abnormal (Dead)', value: data.abnormal_day_10, color: '#dc2626' },
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur-xs z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#800000]/10 text-[#800000] flex items-center justify-center font-black">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900">
                  {data?.batch_code || batchId} Analytics
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#800000]/10 text-[#800000] border border-[#800000]/20">
                  {data?.breed || 'KAYUMANGGI'}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                  {data?.incubator_id}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Embryo viability, Day 10 candling breakdown, and financial salvage metrics.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-6">
          {isLoading ? (
            <div className="py-20 text-center text-xs text-slate-500 font-medium">
              Loading deep batch analytics...
            </div>
          ) : data ? (
            <>
              {/* Top KPI Cards Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1">
                  <div className="flex items-center justify-between text-slate-500 text-[11px] font-semibold">
                    <span>Day 10 Fertility</span>
                    <TrendingUp className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div className="text-2xl font-black text-slate-900 tracking-tight">
                    {data.day_10_fertility_rate}%
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {data.fertile_day_10} viable / {data.total_scanned_day_10 || data.initial_egg_count} eggs
                  </p>
                </div>

                <div className="bg-amber-50/50 border border-amber-200 rounded-xl p-4 space-y-1">
                  <div className="flex items-center justify-between text-amber-700 text-[11px] font-semibold">
                    <span>Penoy Salvaged</span>
                    <Coins className="w-4 h-4 text-amber-600" />
                  </div>
                  <div className="text-2xl font-black text-amber-900 tracking-tight">
                    ₱{data.penoy_salvage_value_php.toLocaleString('en-PH', { minimumFractionDigits: 2 })}
                  </div>
                  <p className="text-[10px] text-amber-700">
                    {data.infertile_penoy_day_10} eggs @ ₱14.00/ea
                  </p>
                </div>

                <div className="bg-emerald-50/50 border border-emerald-200 rounded-xl p-4 space-y-1">
                  <div className="flex items-center justify-between text-emerald-700 text-[11px] font-semibold">
                    <span>Power Saved</span>
                    <Zap className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div className="text-2xl font-black text-emerald-900 tracking-tight">
                    ₱{data.electricity_saved_php.toLocaleString('en-PH', { minimumFractionDigits: 2 })}
                  </div>
                  <p className="text-[10px] text-emerald-700">
                    Day 10 early cull savings
                  </p>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1">
                  <div className="flex items-center justify-between text-slate-500 text-[11px] font-semibold">
                    <span>Hatchability Rate</span>
                    <Award className="w-4 h-4 text-[#800000]" />
                  </div>
                  <div className="text-2xl font-black text-slate-900 tracking-tight">
                    {data.actual_hatchability_rate > 0 ? `${data.actual_hatchability_rate}%` : 'Pending'}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {data.hatched_count} hatched / {data.initial_egg_count} set
                  </p>
                </div>
              </div>

              {/* Visual Distribution Charts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Donut Chart */}
                <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-900">
                      Day 10 Class Distribution
                    </h3>
                    <span className="text-[11px] text-slate-500 font-medium">
                      Total: {data.total_scanned_day_10 || data.initial_egg_count} eggs
                    </span>
                  </div>

                  <div className="h-48 w-full flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={45}
                          outerRadius={70}
                          paddingAngle={3}
                        >
                          {pieData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 text-center text-xs">
                    <div>
                      <div className="text-emerald-700 font-bold">{data.fertile_day_10}</div>
                      <div className="text-[10px] text-slate-500 font-medium">Fertile</div>
                    </div>
                    <div>
                      <div className="text-amber-700 font-bold">{data.infertile_penoy_day_10}</div>
                      <div className="text-[10px] text-slate-500 font-medium">Infertile (Penoy)</div>
                    </div>
                    <div>
                      <div className="text-red-700 font-bold">{data.abnormal_day_10}</div>
                      <div className="text-[10px] text-slate-500 font-medium">Abnormal (Dead)</div>
                    </div>
                  </div>
                </div>

                {/* Batch Timeline & Incubation Parameters */}
                <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-3 flex flex-col justify-between">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 pb-2 border-b border-slate-100">
                      Incubation Progress & Lifecycle
                    </h3>
                    <div className="space-y-3 pt-3 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Current Stage:</span>
                        <span className="font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded">
                          {data.current_stage}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Elapsed Time:</span>
                        <span className="font-bold text-slate-800">
                          {data.elapsed_days} / 28 Days
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Set Date:</span>
                        <span className="font-semibold text-slate-800">
                          {new Date(data.set_date).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Target Hatch Date:</span>
                        <span className="font-semibold text-slate-800">
                          {new Date(data.target_hatch_date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-600">
                    <p className="font-bold text-slate-800 mb-0.5">Commercial Recommendation:</p>
                    {data.infertile_penoy_day_10 > 0 ? (
                      <p>
                        Transfer {data.infertile_penoy_day_10} culled penoy eggs immediately to cold room (10-15°C) to maintain market freshness @ ₱14.00.
                      </p>
                    ) : (
                      <p>Continue incubator climate regime (37.5°C / 60% RH) until Day 18 transfer.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Candling Sessions Log */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-3">
                <h3 className="text-xs font-bold text-slate-900">
                  Candling Runs & Conveyor Throughput
                </h3>

                {data.sessions.length === 0 ? (
                  <p className="text-xs text-slate-400 py-4 text-center">
                    No candling runs recorded yet for this batch.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                        <tr>
                          <th className="py-2 px-3 font-semibold">Stage</th>
                          <th className="py-2 px-3 font-semibold">Operator</th>
                          <th className="py-2 px-3 font-semibold text-right">Scanned</th>
                          <th className="py-2 px-3 font-semibold text-right">Fertile</th>
                          <th className="py-2 px-3 font-semibold text-right">Penoy</th>
                          <th className="py-2 px-3 font-semibold text-right">Dead</th>
                          <th className="py-2 px-3 font-semibold text-right">Fertility Rate</th>
                          <th className="py-2 px-3 font-semibold text-right">Avg ONNX Latency</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {data.sessions.map((s) => (
                          <tr key={s.session_id} className="hover:bg-slate-50/50">
                            <td className="py-2 px-3 font-bold text-slate-900">{s.stage}</td>
                            <td className="py-2 px-3 text-slate-600">{s.operator_name}</td>
                            <td className="py-2 px-3 text-right font-semibold text-slate-900">{s.total_scanned}</td>
                            <td className="py-2 px-3 text-right text-emerald-700 font-bold">{s.fertile_count}</td>
                            <td className="py-2 px-3 text-right text-amber-700 font-bold">{s.infertile_count}</td>
                            <td className="py-2 px-3 text-right text-red-700 font-bold">{s.abnormal_count}</td>
                            <td className="py-2 px-3 text-right font-bold text-[#800000]">{s.fertility_rate}%</td>
                            <td className="py-2 px-3 text-right text-slate-500">{s.avg_inference_ms} ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};
