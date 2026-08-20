import React, { useState, useEffect } from 'react';
import {
  Coins,
  TrendingUp,
  Zap,
  Award,
  Layers,
  Calculator,
  Info,
  CheckCircle,
  Sliders,
  DollarSign,
  PieChart as PieIcon,
  ShieldCheck
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

  // Dynamic Financial Simulator sliders
  const [customEggs, setCustomEggs] = useState(168);
  const [customPrice, setCustomPrice] = useState(14.00);
  const [electricityRate, setElectricityRate] = useState(12.50); // PHP per kWh

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

  // 28-day duck egg developmental viability curve
  const cohortSurvivalData = [
    { day: 'Day 0 (Set)', viablePct: 100, penoyRecovery: 0, deadDiscard: 0 },
    { day: 'Day 10 (1st Candle)', viablePct: 91.2, penoyRecovery: 8.8, deadDiscard: 0 },
    { day: 'Day 18 (2nd Candle)', viablePct: 88.5, penoyRecovery: 8.8, deadDiscard: 2.7 },
    { day: 'Day 25 (Pipping)', viablePct: 87.1, penoyRecovery: 8.8, deadDiscard: 4.1 },
    { day: 'Day 28 (Harvest)', viablePct: 86.8, penoyRecovery: 8.8, deadDiscard: 4.4 },
  ];

  // Breed Performance Comparison Matrix
  const breedMatrix = [
    { breed: 'Kayumanggi Duck', sampleSet: 500, fertility: 91.2, penoyYield: '8.8%', hatchability: 86.8, netRevenue: '₱6,980.00' },
    { breed: 'Itim (Native Duck)', sampleSet: 450, fertility: 87.5, penoyYield: '9.3%', hatchability: 82.4, netRevenue: '₱5,840.00' },
    { breed: 'Khaki Campbell', sampleSet: 350, fertility: 84.8, penoyYield: '10.2%', hatchability: 79.6, netRevenue: '₱4,320.00' },
  ];

  // Dynamic calculations
  const dynamicSales = customEggs * customPrice;
  const dynamicKwhSaved = customEggs * 18 * 0.015; // 0.015 kWh/egg/day across 18 days
  const dynamicPowerSavings = dynamicKwhSaved * electricityRate;
  const dynamicTotalBenefit = dynamicSales + dynamicPowerSavings;

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-obsidian-900 border border-obsidian-700/80 p-4 rounded-lg shadow-xl">
        <div>
          <h2 className="text-lg font-display font-black tracking-wide text-white uppercase flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            Hatchery Economics, Penoy Salvage & Embryonic Analytics
          </h2>
          <p className="text-xs font-mono text-slate-400">
            Day 10 unfertilized egg food market recovery • Incubator thermal energy savings • Breed benchmarking
          </p>
        </div>

        <div className="px-3 py-1.5 bg-[#800000]/20 border border-[#800000]/60 rounded text-amber-300 font-mono text-xs font-bold">
          FOUNDATION UNIVERSITY RESEARCH DEPT
        </div>
      </div>

      {/* Economic KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Penoy Salvaged"
          value={economic ? `${economic.penoy_culled_day_10}` : '168'}
          unit="eggs"
          subtitle="Culled on Day 10 candling"
          icon={Coins}
          accentColor="amber"
          trend={{ value: '100% Edible', isPositive: true, label: 'Unfertilized' }}
        />
        <StatCard
          title="Penoy Salvage Revenue"
          value={economic ? `₱${economic.salvage_revenue_php.toFixed(2)}` : '₱2,352.00'}
          subtitle={`@ ₱${economic ? economic.penoy_unit_price_php : 14.0}/egg market rate`}
          icon={TrendingUp}
          accentColor="green"
          trend={{ value: '₱0 Loss', isPositive: true }}
        />
        <StatCard
          title="Incubator Energy Saved"
          value={economic ? `${economic.incubator_energy_saved_kwh.toFixed(1)}` : '45.4'}
          unit="kWh"
          subtitle={`₱${economic ? economic.energy_savings_php.toFixed(2) : '567.50'} power tariff avoided`}
          icon={Zap}
          accentColor="cyan"
          baseline="18 Days Post-Cull"
        />
        <StatCard
          title="Net Economic Gain"
          value={economic ? `₱${economic.total_economic_benefit_php.toFixed(2)}` : '₱2,919.50'}
          subtitle="Direct Revenue + Energy Saved"
          icon={Award}
          accentColor="maroon"
          trend={{ value: '+18.4% ROI', isPositive: true }}
        />
      </div>

      {/* Interactive Day-10 Penoy Economic Simulator (Technical Terminal Style) */}
      <div className="panel-scada p-5 space-y-4 border-amber-500/40">
        <div className="flex items-center justify-between border-b border-obsidian-700 pb-3">
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-display font-bold uppercase tracking-wider text-slate-100">
              Interactive Day-10 Penoy Financial Simulator
            </h3>
          </div>
          <span className="text-[10px] font-mono bg-amber-950/60 border border-amber-600/50 text-amber-300 px-2 py-0.5 rounded font-bold">
            SCENARIO MODELER
          </span>
        </div>

        <p className="text-xs font-mono text-slate-300">
          Simulate revenue recovered from culling clear unfertilized eggs at Day 10 versus leaving them in incubator trays until Day 28:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1 font-mono text-xs">
          {/* Slider 1: Eggs Culled */}
          <div className="p-3 bg-obsidian-950 rounded border border-obsidian-800 space-y-2">
            <div className="flex justify-between">
              <label className="text-slate-400 font-bold">Day 10 Infertile Eggs Culled:</label>
              <span className="text-amber-300 font-black">{customEggs} eggs</span>
            </div>
            <input
              type="range"
              min="0"
              max="500"
              step="5"
              value={customEggs}
              onChange={(e) => setCustomEggs(Number(e.target.value))}
              className="w-full accent-amber-400 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500 block">From 0 to 500 tray capacity</span>
          </div>

          {/* Slider 2: Penoy Market Price */}
          <div className="p-3 bg-obsidian-950 rounded border border-obsidian-800 space-y-2">
            <div className="flex justify-between">
              <label className="text-slate-400 font-bold">Penoy Selling Price (PHP):</label>
              <span className="text-amber-300 font-black">₱{customPrice.toFixed(2)}/egg</span>
            </div>
            <input
              type="range"
              min="10"
              max="22"
              step="0.5"
              value={customPrice}
              onChange={(e) => setCustomPrice(Number(e.target.value))}
              className="w-full accent-amber-400 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500 block">Negros Oriental local market (₱12–₱18)</span>
          </div>

          {/* Calculated Output Box */}
          <div className="p-4 bg-[#800000]/25 rounded border border-[#800000]/60 flex flex-col justify-center text-center">
            <span className="text-[10px] font-bold text-amber-300 uppercase tracking-widest">
              Total Economic Benefit Recovered
            </span>
            <span className="text-2xl lg:text-3xl font-black text-white mt-1">
              ₱{dynamicTotalBenefit.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[10px] text-slate-300 mt-1">
              (₱{dynamicSales.toFixed(2)} sales + ₱{dynamicPowerSavings.toFixed(2)} power saved)
            </span>
          </div>
        </div>
      </div>

      {/* Split: Cohort Survival Curve + Breed Benchmarks Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 Cols: 28-Day Embryonic Cohort Survival Area Chart */}
        <div className="lg:col-span-7 panel-scada p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-obsidian-700/60 pb-2">
            <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-200">
              28-Day Embryonic Development & Viability Retention
            </h3>
            <span className="text-[10px] font-mono text-emerald-400 font-bold">86.8% HATCHABILITY</span>
          </div>

          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={cohortSurvivalData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="viableGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#16A34A" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#16A34A" stopOpacity={0.05}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" stroke="#64748B" fontSize={10} tickLine={false} />
                <YAxis domain={[75, 100]} stroke="#64748B" fontSize={10} tickLine={false} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#070A11', borderColor: '#1E293B', borderRadius: '6px', fontSize: '11px', fontFamily: 'JetBrains Mono', color: '#fff' }}
                  formatter={(val: any) => [`${val}%`, 'Viable Embryos']}
                />
                <Area type="monotone" dataKey="viablePct" stroke="#16A34A" strokeWidth={2.5} fillOpacity={1} fill="url(#viableGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="text-[10px] font-mono text-slate-400 text-center border-t border-obsidian-800 pt-2">
            Day 10 candling locks in unfertilized egg value; Day 18 transfer eliminates space heating waste.
          </div>
        </div>

        {/* Right 5 Cols: Comparative Breed Performance Ledger */}
        <div className="lg:col-span-5 panel-scada p-0 overflow-hidden">
          <div className="panel-scada-header">
            <span>Breed Performance Matrix</span>
            <span className="text-[10px] text-amber-400 font-mono">Benchmark</span>
          </div>

          <div className="p-3 space-y-3 font-mono text-xs">
            {breedMatrix.map((b) => (
              <div key={b.breed} className="p-3 bg-obsidian-950 rounded border border-obsidian-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-100">{b.breed}</span>
                  <span className="font-bold text-emerald-400">{b.fertility}% Fertility</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-[10px] text-slate-400 pt-1 border-t border-obsidian-850">
                  <div>Set: <strong className="text-slate-200">{b.sampleSet}</strong></div>
                  <div>Penoy: <strong className="text-amber-300">{b.penoyYield}</strong></div>
                  <div>Hatch: <strong className="text-slate-200">{b.hatchability}%</strong></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Academic Capstone Defense Takeaways */}
      <div className="panel-scada p-4 space-y-3">
        <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
          <Award className="w-4 h-4 text-amber-400" />
          Foundation University Hatchery Economics & Biological Defense Notes
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
          <div className="p-3 bg-obsidian-950 rounded border border-obsidian-800 space-y-1">
            <span className="text-emerald-400 font-bold block">1. 100% Edible Penoy Recovery</span>
            <p className="text-[11px] text-slate-400">
              Unfertilized eggs candled on Day 10 have clean yolks with zero embryonic decay, making them 100% food-safe and sold at ₱14–₱16/egg.
            </p>
          </div>
          <div className="p-3 bg-obsidian-950 rounded border border-obsidian-800 space-y-1">
            <span className="text-amber-400 font-bold block">2. Thermal Energy & Tray Turnover</span>
            <p className="text-[11px] text-slate-400">
              Removing infertile eggs frees up tray slots 18 days early, reducing incubator heating load by ~45 kWh per 500-egg batch.
            </p>
          </div>
          <div className="p-3 bg-obsidian-950 rounded border border-obsidian-800 space-y-1">
            <span className="text-cyan-400 font-bold block">3. Exploder & Bacteria Defense</span>
            <p className="text-[11px] text-slate-400">
              Early culling of dead embryos (Abnormal) prevents bacterial gas buildup and egg bursting, safeguarding adjacent viable eggs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
