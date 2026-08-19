import React, { useState, useEffect } from 'react';
import {
  Coins,
  TrendingUp,
  Zap,
  Award,
  Layers,
  Calculator,
  Info,
  CheckCircle
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend
} from 'recharts';

import { StatCard } from '../components/StatCard';
import { apiClient } from '../api/client';
import { EconomicYield, AnalyticsOverview } from '../types';

export const AnalyticsPage: React.FC = () => {
  const [economic, setEconomic] = useState<EconomicYield | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);

  // Dynamic Calculator state
  const [customEggs, setCustomEggs] = useState(168);
  const [customPrice, setCustomPrice] = useState(14.00);

  useEffect(() => {
    const fetchData = async () => {
      const [eData, oData] = await Promise.all([
        apiClient.getEconomicYield(),
        apiClient.getOverview()
      ]);
      setEconomic(eData);
      setOverview(oData);
    };
    fetchData();
  }, []);

  // 28-day duck mortality / candling milestone curve
  const milestoneData = [
    { day: 'Day 0 (Set)', viable: 100, culled: 0 },
    { day: 'Day 10 (Penoy)', viable: 91.2, culled: 8.8 },
    { day: 'Day 18 (Hatcher)', viable: 88.5, culled: 11.5 },
    { day: 'Day 25 (Pipping)', viable: 87.1, culled: 12.9 },
    { day: 'Day 28 (Hatch)', viable: 86.8, culled: 13.2 },
  ];

  // Calculated dynamic economic yield
  const dynamicSalvage = customEggs * customPrice;
  const dynamicKwhSaved = customEggs * 18 * 0.015; // 0.015 kWh/egg/day
  const dynamicEnergyPhp = dynamicKwhSaved * 12.0; // ₱12.00 / kWh
  const dynamicTotalBenefit = dynamicSalvage + dynamicEnergyPhp;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100">Hatchery Economics & Analytics</h2>
        <p className="text-xs text-slate-400">Day 10 Penoy salvage revenue optimization, mortality curves, and breed metrics</p>
      </div>

      {/* Economic KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Penoy Salvaged"
          value={economic ? `${economic.penoy_culled_day_10} eggs` : '---'}
          subtitle="Culled on Day 10 candling"
          icon={Coins}
          colorScheme="amber"
        />
        <StatCard
          title="Penoy Salvage Revenue"
          value={economic ? `₱${economic.salvage_revenue_php.toFixed(2)}` : '---'}
          subtitle={`@ ₱${economic ? economic.penoy_unit_price_php : 14}/egg market rate`}
          icon={TrendingUp}
          colorScheme="green"
        />
        <StatCard
          title="Incubator Energy Saved"
          value={economic ? `${economic.incubator_energy_saved_kwh.toFixed(1)} kWh` : '---'}
          subtitle={`₱${economic ? economic.energy_savings_php.toFixed(2) : '0'} power cost avoided`}
          icon={Zap}
          colorScheme="blue"
        />
        <StatCard
          title="Net Economic Gain"
          value={economic ? `₱${economic.total_economic_benefit_php.toFixed(2)}` : '---'}
          subtitle="Revenue + Energy Saved"
          icon={Award}
          colorScheme="maroon"
        />
      </div>

      {/* Interactive Economic Salvage Calculator */}
      <div className="bg-gradient-to-r from-slate-900 to-[#1E293B] border border-amber-500/30 rounded-xl p-6 shadow-xl space-y-4">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-amber-400" />
          <h3 className="text-base font-bold text-slate-100">Interactive Day-10 Penoy Salvage Estimator</h3>
        </div>
        <p className="text-xs text-slate-300">
          Simulate revenue recovered from unfertilized eggs culled at Day 10 vs leaving them in the incubator until Day 28:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Infertile Eggs Culled (Day 10):</label>
            <input
              type="number"
              min="0"
              value={customEggs}
              onChange={(e) => setCustomEggs(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-amber-300 font-bold focus:outline-none focus:border-amber-400"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Penoy Market Price per Egg (PHP):</label>
            <input
              type="number"
              step="0.50"
              min="1"
              value={customPrice}
              onChange={(e) => setCustomPrice(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-amber-300 font-bold focus:outline-none focus:border-amber-400"
            />
          </div>

          <div className="p-3.5 bg-[#800000]/30 rounded-lg border border-[#800000]/60 flex flex-col justify-center">
            <span className="text-[11px] font-semibold text-amber-300 uppercase tracking-wide">Calculated Net Benefit</span>
            <span className="text-2xl font-black text-white mt-0.5">
              ₱{dynamicTotalBenefit.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[10px] text-slate-400">
              (₱{dynamicSalvage.toFixed(2)} sales + ₱{dynamicEnergyPhp.toFixed(2)} power saved)
            </span>
          </div>
        </div>
      </div>

      {/* Incubation Lifecycle Viability Curve */}
      <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-6 shadow-lg space-y-4">
        <div>
          <h3 className="text-base font-bold text-slate-100">Embryonic Viability Curve Across 28 Days</h3>
          <p className="text-xs text-slate-400">Survival percentage vs cumulative culling across incubation milestones</p>
        </div>

        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={milestoneData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorViable" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#357a38" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#357a38" stopOpacity={0.05}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="day" stroke="#64748B" fontSize={11} tickLine={false} />
              <YAxis domain={[80, 100]} stroke="#64748B" fontSize={11} tickLine={false} unit="%" />
              <Tooltip
                contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', color: '#fff' }}
                formatter={(val: any) => [`${val}%`, 'Viable Embryos']}
              />
              <Area type="monotone" dataKey="viable" stroke="#357a38" strokeWidth={2.5} fillOpacity={1} fill="url(#colorViable)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Academic Takeaways for Capstone Defense */}
      <div className="bg-[#1E293B] border border-slate-800 rounded-xl p-6 shadow-lg space-y-3">
        <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
          <Award className="w-5 h-5 text-amber-400" />
          Foundation University Hatchery Insights
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 bg-slate-900/60 rounded-lg border border-slate-800 space-y-1">
            <h4 className="font-bold text-emerald-400">1. Day-10 Cull Maximizes Penoy Yield</h4>
            <p className="text-slate-400">
              Unfertilized eggs culled on Day 10 remain edible and sell at market price (₱14–₱16), preventing complete loss.
            </p>
          </div>
          <div className="p-3.5 bg-slate-900/60 rounded-lg border border-slate-800 space-y-1">
            <h4 className="font-bold text-amber-400">2. Power Savings via Space Recovery</h4>
            <p className="text-slate-400">
              Removing infertile eggs frees up incubator tray capacity and saves ~45 kWh of heating energy across 18 remaining days.
            </p>
          </div>
          <div className="p-3.5 bg-slate-900/60 rounded-lg border border-slate-800 space-y-1">
            <h4 className="font-bold text-blue-400">3. Prevention of Egg Corruption (Exploders)</h4>
            <p className="text-slate-400">
              Early culling of dead embryos prevents bacterial gas buildup, protecting adjacent healthy eggs from contamination.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
