import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Microscope,
  Zap,
  Activity,
  Layers,
  CheckCircle2,
  TrendingUp,
  Database,
  Server,
  Download,
  UploadCloud,
  Check,
  Flame,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  AreaChart,
  Area,
} from 'recharts';

import { StatCard } from '../components/StatCard';
import { apiClient } from '../api/client';
import { ModelCheckpoint, TrainingLossEpoch, ModelOpsSummary } from '../types';

export const ModelsPage: React.FC = () => {
  const [summary, setSummary] = useState<ModelOpsSummary | null>(null);
  const [checkpoints, setCheckpoints] = useState<ModelCheckpoint[]>([]);
  const [lossData, setLossData] = useState<TrainingLossEpoch[]>([]);
  const [deploySuccess, setDeploySuccess] = useState<string | null>(null);

  const fetchModelData = async () => {
    const [summaryData, checkpointsData, lossCurve] = await Promise.all([
      apiClient.getModelOpsSummary(),
      apiClient.getModelCheckpoints(),
      apiClient.getTrainingLoss(),
    ]);
    setSummary(summaryData);
    setCheckpoints(checkpointsData);
    setLossData(lossCurve);
  };

  useEffect(() => {
    fetchModelData();
  }, []);

  const handleDeploy = async (checkpoint: ModelCheckpoint) => {
    await apiClient.deployModelCheckpoint(checkpoint.model_id);
    setDeploySuccess(`Model ${checkpoint.version_tag} successfully deployed to all active Edge Sorter Nodes.`);
    fetchModelData();
    setTimeout(() => setDeploySuccess(null), 4000);
  };

  if (!summary) return null;

  return (
    <div className="space-y-6 pb-8">
      {/* Institutional Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
              AI Vision Models & MLOps Registry
            </h1>
            <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-maroon-50 text-[#800000] border border-maroon-200">
              Admin & Evaluation
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            YOLOv8 ONNX FP16 candling classification architecture, 100-epoch convergence, 3-class confusion matrix, and edge benchmarks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
            <span>Active Model: <strong>{summary.active_model_version}</strong></span>
          </div>
        </div>
      </div>

      {deploySuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-2 shadow-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
          <span>{deploySuccess}</span>
        </div>
      )}

      {/* Model Performance KPI Ribbon */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="mAP@0.5 Score"
          value={`${(summary.overall_map50 * 100).toFixed(1)}%`}
          subtitle="Mean Average Precision @ IoU 0.50"
          icon={Microscope}
          highlightColor="maroon"
        />
        <StatCard
          title="Classification Precision"
          value={`${(summary.overall_precision * 100).toFixed(1)}%`}
          subtitle="True Positive / Total Predicted"
          icon={CheckCircle2}
          highlightColor="green"
        />
        <StatCard
          title="Embryo Detection Recall"
          value={`${(summary.overall_recall * 100).toFixed(1)}%`}
          subtitle="True Positive / Actual Ground Truth"
          icon={Activity}
          highlightColor="blue"
        />
        <StatCard
          title="Training Dataset"
          value={summary.total_training_images.toLocaleString()}
          unit="frames"
          subtitle="Transillumination Duck Egg Images"
          icon={Database}
          highlightColor="amber"
        />
        <StatCard
          title="RPi5 Edge Latency"
          value={`${summary.avg_latency_ms}`}
          unit="ms"
          subtitle="ONNX FP16 Single-Frame Pass"
          icon={Zap}
          highlightColor="green"
        />
      </div>

      {/* Confusion Matrix & Hardware Runtime Benchmark */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 6 Cols: 3-Class Confusion Matrix */}
        <div className="lg:col-span-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    3-Class Normalized Confusion Matrix
                  </h3>
                  <p className="text-xs text-slate-500">
                    Validation dataset evaluation ($N = 4,850$ frames)
                  </p>
                </div>
                <span className="text-[11px] font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  Normalized %
                </span>
              </div>

              {/* Confusion Matrix Grid */}
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-xs text-center border-collapse">
                  <thead>
                    <tr>
                      <th className="p-2 text-left text-[11px] font-bold text-slate-400 uppercase">Actual \ Pred</th>
                      <th className="p-2 text-[11px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-t">
                        FERTILE
                      </th>
                      <th className="p-2 text-[11px] font-bold text-amber-800 bg-amber-50 border border-amber-200 rounded-t">
                        PENOY
                      </th>
                      <th className="p-2 text-[11px] font-bold text-rose-800 bg-rose-50 border border-rose-200 rounded-t">
                        ABNORMAL
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {/* Row 1: Actual FERTILE */}
                    <tr>
                      <td className="p-2.5 text-left font-bold text-emerald-950 bg-emerald-50/50 border border-emerald-200 font-mono text-[11px]">
                        FERTILE
                      </td>
                      <td className="p-2.5 bg-emerald-600 text-white font-extrabold text-sm border border-emerald-700 shadow-2xs">
                        96.4%
                        <span className="block text-[10px] font-normal text-emerald-100">(2,700)</span>
                      </td>
                      <td className="p-2.5 bg-amber-50 text-amber-900 font-semibold border border-amber-200">
                        2.1%
                        <span className="block text-[10px] text-amber-600">(59)</span>
                      </td>
                      <td className="p-2.5 bg-rose-50 text-rose-900 font-semibold border border-rose-200">
                        1.5%
                        <span className="block text-[10px] text-rose-600">(41)</span>
                      </td>
                    </tr>

                    {/* Row 2: Actual INFERTILE */}
                    <tr>
                      <td className="p-2.5 text-left font-bold text-amber-950 bg-amber-50/50 border border-amber-200 font-mono text-[11px]">
                        INFERTILE (Penoy)
                      </td>
                      <td className="p-2.5 bg-emerald-50 text-emerald-900 font-semibold border border-emerald-200">
                        3.2%
                        <span className="block text-[10px] text-emerald-600">(46)</span>
                      </td>
                      <td className="p-2.5 bg-amber-500 text-white font-extrabold text-sm border border-amber-600 shadow-2xs">
                        94.8%
                        <span className="block text-[10px] font-normal text-amber-100">(1,375)</span>
                      </td>
                      <td className="p-2.5 bg-rose-50 text-rose-900 font-semibold border border-rose-200">
                        2.0%
                        <span className="block text-[10px] text-rose-600">(29)</span>
                      </td>
                    </tr>

                    {/* Row 3: Actual ABNORMAL */}
                    <tr>
                      <td className="p-2.5 text-left font-bold text-rose-950 bg-rose-50/50 border border-rose-200 font-mono text-[11px]">
                        ABNORMAL (Dead)
                      </td>
                      <td className="p-2.5 bg-emerald-50 text-emerald-900 font-semibold border border-emerald-200">
                        4.2%
                        <span className="block text-[10px] text-emerald-600">(25)</span>
                      </td>
                      <td className="p-2.5 bg-amber-50 text-amber-900 font-semibold border border-amber-200">
                        3.7%
                        <span className="block text-[10px] text-amber-600">(22)</span>
                      </td>
                      <td className="p-2.5 bg-rose-600 text-white font-extrabold text-sm border border-rose-700 shadow-2xs">
                        92.1%
                        <span className="block text-[10px] font-normal text-rose-100">(553)</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
              <span>Overall Accuracy: <strong className="text-slate-900">95.4%</strong></span>
              <span className="text-emerald-700 font-semibold">Low false-reject rate (2.1%)</span>
            </div>
          </div>
        </div>

        {/* Right 6 Cols: Hardware Optimization & Runtime Latency Benchmark */}
        <div className="lg:col-span-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    PyTorch FP32 vs ONNX Runtime FP16 Benchmark
                  </h3>
                  <p className="text-xs text-slate-500">Raspberry Pi 5 (Cortex-A76 @ 2.4GHz) Hardware Execution</p>
                </div>
                <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  -64% Latency
                </span>
              </div>

              {/* Latency Comparison Card */}
              <div className="mt-4 space-y-3">
                <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-700">PyTorch FP32 (Unquantized best.pt)</span>
                    <span className="font-mono font-bold text-slate-800">68.4 ms (14.6 FPS)</span>
                  </div>
                  <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                    <div className="bg-slate-400 h-full rounded-full" style={{ width: '100%' }} />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-500">
                    <span>Memory: 24.8 MB</span>
                    <span>High thermal dissipation</span>
                  </div>
                </div>

                <div className="p-3.5 rounded-lg bg-emerald-50/60 border border-emerald-200 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-emerald-950">ONNX Runtime FP16 (Quantized Edge Slim)</span>
                    <span className="font-mono font-extrabold text-emerald-800 text-sm">24.6 ms (40.6 FPS)</span>
                  </div>
                  <div className="w-full bg-emerald-100 h-2.5 rounded-full overflow-hidden">
                    <div className="bg-emerald-600 h-full rounded-full" style={{ width: '36%' }} />
                  </div>
                  <div className="flex justify-between text-[11px] text-emerald-700 font-semibold">
                    <span>Memory: 12.1 MB (-51%)</span>
                    <span>3 Warmup Dummy Passes L2/L3 Cache</span>
                  </div>
                </div>
              </div>

              {/* Hardware Throughput Feasibility Note */}
              <div className="mt-3 p-3 rounded-lg bg-blue-50/60 border border-blue-200 text-xs text-blue-900 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-blue-950">
                  <ShieldCheck className="w-4 h-4 text-blue-700" />
                  <span>Industrial SLA Compliance</span>
                </div>
                <p className="text-[11px] text-blue-800 leading-snug">
                  At <strong>12.5 cm/s</strong> conveyor velocity and <strong>25 cm</strong> travel distance (travel time: 2,000 ms), the <strong>24.6 ms</strong> ONNX inference easily satisfies physical pneumatic sorting timing.
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
              <span>Conveyor Headroom: <strong className="text-slate-900">81.3x margin</strong></span>
              <span className="text-emerald-700 font-semibold">Real-Time Ready</span>
            </div>
          </div>
        </div>
      </div>

      {/* 100-Epoch Training & Validation Loss Curve */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-[#0F172A]">
              100-Epoch Training Loss & mAP Convergence
            </h3>
            <p className="text-xs text-slate-500">
              Bounding Box Loss, Classification Loss, and mAP@0.5 Progression
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 text-slate-600">
              <span className="w-2.5 h-2.5 rounded-full bg-[#800000]" />
              Train Box Loss
            </span>
            <span className="flex items-center gap-1 text-slate-600">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-600" />
              Validation Loss
            </span>
            <span className="flex items-center gap-1 text-slate-600">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
              mAP@0.50
            </span>
          </div>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={lossData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorMap" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#15803D" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#15803D" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="epoch" tick={{ fontSize: 11, fill: '#64748B' }} unit=" ep" />
              <YAxis tick={{ fontSize: 11, fill: '#64748B' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E2E8F0', fontSize: '11px' }}
              />
              <Area type="monotone" dataKey="map50" name="mAP@0.5" stroke="#15803D" strokeWidth={2} fillOpacity={1} fill="url(#colorMap)" />
              <Line type="monotone" dataKey="train_box_loss" name="Train Box Loss" stroke="#800000" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="val_box_loss" name="Val Box Loss" stroke="#2563EB" strokeWidth={2} strokeDasharray="4 4" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model Checkpoints Registry Table */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-[#0F172A]">
              Model Checkpoint Registry & Edge Deployment
            </h3>
            <p className="text-xs text-slate-500">
              Deploy trained ONNX weight models directly to active conveyor sorting stations.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Model Checkpoint</th>
                <th className="py-3 px-4">Architecture</th>
                <th className="py-3 px-4">Format</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">mAP@0.5</th>
                <th className="py-3 px-4">Edge Latency</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {checkpoints.map((cp) => (
                <tr key={cp.model_id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-[#0F172A]">
                    {cp.version_tag}
                  </td>
                  <td className="py-3 px-4 text-slate-700 font-medium">{cp.architecture}</td>
                  <td className="py-3 px-4">
                    <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700">
                      {cp.format}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-600">{cp.file_size_mb} MB</td>
                  <td className="py-3 px-4 font-bold text-emerald-800">{(cp.map50 * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 font-mono font-semibold text-slate-800">{cp.avg_latency_ms} ms</td>
                  <td className="py-3 px-4">
                    {cp.is_active ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                        Active on {cp.deployed_stations.length} Nodes
                      </span>
                    ) : (
                      <span className="text-slate-400 font-medium text-xs">Staging</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {cp.is_active ? (
                      <span className="text-xs font-semibold text-emerald-700">Currently Deployed</span>
                    ) : (
                      <button
                        onClick={() => handleDeploy(cp)}
                        className="px-3 py-1 text-xs font-bold text-white bg-[#800000] hover:bg-[#6B0000] rounded-lg shadow-xs transition-colors cursor-pointer"
                      >
                        Deploy to Nodes
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
